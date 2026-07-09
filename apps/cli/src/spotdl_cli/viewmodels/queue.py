"""``QueueViewModel`` — WS-driven download queue (CONTRACT A/E).

The heart is the **pure** ``reduce(snapshot, frame)``: it folds a ``WsMessage`` into
an immutable ``QueueSnapshot`` idempotently (duplicate/out-of-order/unknown-job
frames are safe). ``stream`` owns ``client.progress()``, does the ``WsHello`` version
check, and reconnects with bounded exponential backoff; the worker never parses a
frame itself.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace
from uuid import UUID

from spotdl_cli.viewmodels.app_state import SessionSnapshot
from spotdl_cli.viewmodels.base import (
    ErrorDisplay,
    Loadable,
    as_connection_error,
    guard,
)
from spotdl_cli.viewmodels.mappers import batch_ref, job_row
from spotdl_cli.viewmodels.protocol import SpotdlClientProtocol
from spotdl_cli.viewmodels.types import BatchRef, JobRow, QueueSnapshot
from spotdl_cli.views import (
    DownloadSubmit,
    WsBatchFinished,
    WsHello,
    WsJobCancelled,
    WsJobFailed,
    WsJobFinished,
    WsJobQueued,
    WsJobStarted,
    WsMessage,
    WsProgress,
)

# Mirrors the server/client ``WS_PROTOCOL_VERSION`` (``client.py``); duplicated as a
# literal because the framework-free view-model layer must not import the client
# (CONTRACT I). ``stream`` rejects a ``WsHello`` whose version differs.
WS_PROTOCOL_VERSION = 1

_TERMINAL = frozenset({"completed", "skipped", "failed", "cancelled"})
_MAX_RECONNECT_ATTEMPTS = 5
_BACKOFF_BASE_SECONDS = 0.5
_BACKOFF_CAP_SECONDS = 8.0
_UNBATCHED = UUID(int=0)

_PROTOCOL_MISMATCH = ErrorDisplay(
    "the server speaks a newer download-progress protocol; upgrade spotdl",
    code=None,
    severity="error",
)

_EMPTY = QueueSnapshot(
    jobs=(), overall_percent=0, active=0, completed=0, failed=0, skipped=0, cancelled=0
)


class QueueViewModel:
    def __init__(self, client: SpotdlClientProtocol, session: SessionSnapshot) -> None:
        self._client = client
        self._session = session
        self._snapshot = _EMPTY

    async def load(self) -> Loadable[QueueSnapshot]:
        """Seed the queue from a ``list_downloads()`` page."""

        async def _run() -> QueueSnapshot:
            page = await self._client.list_downloads()
            snapshot = _recount(_EMPTY, tuple(job_row(job) for job in page.jobs))
            self._snapshot = snapshot
            return snapshot

        return await guard(_run())

    async def cancel(self, job_id: UUID) -> Loadable[JobRow]:
        async def _run() -> JobRow:
            return job_row(await self._client.cancel_download(job_id))

        return await guard(_run())

    def apply_job(self, snap: QueueSnapshot, row: JobRow) -> QueueSnapshot:
        """Fold a single ``JobRow`` (e.g. a ``cancel`` outcome) into ``snap``.

        Reuses the reduce path's ``_recount`` so a command result reconciles counts
        the same way a WS frame would — the screen never recomputes totals itself.
        """
        rows = list(snap.jobs)
        index = next((i for i, existing in enumerate(rows) if existing.job_id == row.job_id), None)
        if index is None:
            rows.append(row)
        else:
            rows[index] = row
        self._snapshot = _recount(snap, tuple(rows))
        return self._snapshot

    async def enqueue(self, query: str) -> Loadable[BatchRef]:
        if not self._session.can_download:
            return Loadable.failed(
                ErrorDisplay("downloads aren't available on this server", None, "error")
            )

        async def _run() -> BatchRef:
            return batch_ref(await self._client.submit_download(DownloadSubmit(query=query)))

        return await guard(_run())

    def reduce(self, snap: QueueSnapshot, msg: WsMessage) -> QueueSnapshot:
        """Fold one WS frame into ``snap`` — pure, idempotent, order-tolerant."""
        inner = msg.root
        if isinstance(inner, WsHello):
            return snap
        if isinstance(inner, WsBatchFinished):
            return replace(
                snap,
                completed=inner.completed,
                failed=inner.failed,
                skipped=inner.skipped,
                cancelled=inner.cancelled,
                overall_percent=100,
                active=0,
            )
        rows = list(snap.jobs)
        index = next((i for i, row in enumerate(rows) if row.job_id == inner.job_id), None)
        existing = rows[index] if index is not None else None
        new_row = _apply_frame(existing, inner)
        if new_row is None:
            return snap
        if index is None:
            rows.append(new_row)
        else:
            rows[index] = new_row
        return _recount(snap, tuple(rows))

    async def stream(self) -> AsyncIterator[Loadable[QueueSnapshot]]:
        """Yield a ``ready`` snapshot after each frame; reconnect with backoff.

        Ends on a normal socket close; a ``WsHello`` version mismatch yields one
        ``failed`` and stops; a transport failure reconnects up to
        ``_MAX_RECONNECT_ATTEMPTS`` (then yields one terminal ``failed``).
        """
        attempts = 0
        while True:
            try:
                async with self._client.progress() as frames:
                    attempts = 0
                    async for msg in frames:
                        if isinstance(msg.root, WsHello):
                            version = (
                                msg.root.protocol_version
                                if msg.root.protocol_version is not None
                                else WS_PROTOCOL_VERSION
                            )
                            if version != WS_PROTOCOL_VERSION:
                                yield Loadable.failed(_PROTOCOL_MISMATCH)
                                return
                            continue
                        self._snapshot = self.reduce(self._snapshot, msg)
                        yield Loadable.ready(self._snapshot)
                return
            except Exception as exc:  # noqa: BLE001 — narrowed to transport failures
                if _is_protocol_mismatch(exc):
                    # The real client consumes the hello and raises this instead of
                    # yielding it (the fake yields it and the in-stream check above
                    # catches it) — surface the same typed error for both shapes.
                    yield Loadable.failed(_PROTOCOL_MISMATCH)
                    return
                connection_error = as_connection_error(exc)
                if connection_error is None:
                    raise
                attempts += 1
                if attempts >= _MAX_RECONNECT_ATTEMPTS:
                    yield Loadable.failed(connection_error)
                    return
                await asyncio.sleep(_backoff(attempts))


def _is_protocol_mismatch(exc: BaseException) -> bool:
    """Recognise the client's ``UnsupportedProtocol`` structurally (CONTRACT I).

    The framework-free view-model layer must not import ``spotdl_cli.client``, so —
    exactly like ``as_connection_error`` recognises transport failures by module —
    the WS worker matches the raised handshake error by its module + class name.
    """
    cls = type(exc)
    return cls.__module__ == "spotdl_cli.client" and cls.__name__ == "UnsupportedProtocol"


def _backoff(attempt: int) -> float:
    return min(_BACKOFF_CAP_SECONDS, _BACKOFF_BASE_SECONDS * (2.0 ** (attempt - 1)))


def _recount(snap: QueueSnapshot, rows: tuple[JobRow, ...]) -> QueueSnapshot:
    active = sum(1 for row in rows if row.status not in _TERMINAL)
    completed = sum(1 for row in rows if row.status == "completed")
    failed = sum(1 for row in rows if row.status == "failed")
    skipped = sum(1 for row in rows if row.status == "skipped")
    cancelled = sum(1 for row in rows if row.status == "cancelled")
    overall = round(sum(row.percent for row in rows) / len(rows)) if rows else 0
    return replace(
        snap,
        jobs=rows,
        overall_percent=overall,
        active=active,
        completed=completed,
        failed=failed,
        skipped=skipped,
        cancelled=cancelled,
    )


def _batch_of(frame: object) -> UUID:
    batch_id = getattr(frame, "batch_id", None)
    return batch_id if isinstance(batch_id, UUID) else _UNBATCHED


def _apply_frame(existing: JobRow | None, frame: object) -> JobRow | None:
    """Return the updated row for a per-job frame, or ``None`` to ignore it."""
    if isinstance(frame, WsJobQueued):
        if existing is not None:
            return existing  # idempotent: queued is the first state
        return JobRow(
            job_id=frame.job_id,
            batch_id=_batch_of(frame),
            title=frame.track_name or "",
            phase="queued",
            percent=0,
            status="queued",
            error=None,
            output_path=None,
            skip_reason=None,
        )
    # Every other per-job frame updates an existing, non-terminal row.
    if existing is None or existing.status in _TERMINAL:
        return existing
    if isinstance(frame, WsJobStarted):
        return replace(existing, status="started", phase="start")
    if isinstance(frame, WsProgress):
        percent = frame.percent if frame.percent is not None else existing.percent
        return replace(existing, status="running", phase=frame.phase, percent=percent)
    if isinstance(frame, WsJobFinished):
        return replace(
            existing,
            status="skipped" if frame.skipped else "completed",
            percent=100,
            output_path=frame.output_path,
            skip_reason=frame.skip_reason,
        )
    if isinstance(frame, WsJobFailed):
        return replace(
            existing, status="failed", error=frame.error, phase=frame.step or existing.phase
        )
    if isinstance(frame, WsJobCancelled):
        return replace(existing, status="cancelled")
    return existing
