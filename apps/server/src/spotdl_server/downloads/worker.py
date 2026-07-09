"""``DownloadWorkerPool`` — the in-process asyncio download engine driver.

Owns the queue's runtime side (CONTRACT 1 state machine + CONTRACT 2 pool): claim
→ run the Plan 4 :class:`~spotdl_core.download.DownloadEngine` → terminal
transition, with a throttled progress pump (CONTRACT 5), cooperative
cancellation, graceful-shutdown draining, and boot-time crash recovery. It owns
**everything around** the engine; the engine itself is consumed unchanged and
injected at construction (a ``FakeDownloadEngine`` in the offline suite).

**Single-process ownership** is the safety model: exactly one process owns the
queue, so claiming is a conditional ``UPDATE ... WHERE status='queued'`` guarded
by one ``asyncio.Lock`` (no cross-process ``SELECT ... FOR UPDATE SKIP LOCKED`` —
a documented non-goal). Crash recovery is therefore unconditional on
``status='running'`` at boot (any such row is orphaned by a crashed prior run).

**Layering seams (why this ``downloads/`` module imports no ``api/`` glue):**
the pool broadcasts through a structural :class:`Broadcaster` Protocol that the
concrete ``api.progress_hub.ProgressHub`` satisfies, and finalizes through a
structural :class:`Finalizer` Protocol that ``services.batch.BatchFinalizer``
satisfies — so neither the concrete hub (which imports ``fastapi``) nor the
finalizer is imported here. The WS *message* models are plain Pydantic value
types (no ``fastapi``), imported from ``api.schemas`` to construct the frames.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from spotdl_core.download import (
    DownloadOutcome,
    DownloadRequest,
    OutcomeStatus,
    OutputFormat,
    OverwriteMode,
    ProgressEvent,
    ProgressPhase,
)
from spotdl_core.download.paths import build_output_path, load_archive
from spotdl_core.model import AlbumRef, AudioCandidate, Track
from sqlalchemy.exc import OperationalError

from spotdl_server.api.schemas import (
    WsBatchFinished,
    WsJobCancelled,
    WsJobFailed,
    WsJobFinished,
    WsJobStarted,
    WsMessage,
    WsProgress,
)
from spotdl_server.db.enums import BatchKind, DownloadStatus
from spotdl_server.downloads.progress import ProgressThrottle, overall_progress
from spotdl_server.repositories.batches import DownloadBatchRepository
from spotdl_server.repositories.downloads import DownloadJobRepository
from spotdl_server.repositories.entities import TrackRepository
from spotdl_server.repositories.matches import MatchRepository

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from spotdl_server.auth.clock import Clock
    from spotdl_server.db.models import DownloadBatch, DownloadJob, Match
    from spotdl_server.db.models import Track as TrackModel
    from spotdl_server.settings import Settings

logger = logging.getLogger("spotdl_server.downloads.worker")

_ARCHIVE_FILENAME = ".spotdl-archive.txt"
_TERMINAL_PHASES = frozenset({ProgressPhase.DONE, ProgressPhase.SKIPPED, ProgressPhase.ERROR})
_AUDIO_SUFFIXES = frozenset(f".{fmt.value}" for fmt in OutputFormat)


class Engine(Protocol):
    """The single method the pool needs from the download engine (structural seam).

    Satisfied structurally by the Plan 4 ``DownloadEngine`` in production and by
    the offline ``FakeDownloadEngine`` in tests — the pool never imports either.
    """

    async def download(
        self, request: DownloadRequest, on_progress: object | None = None
    ) -> DownloadOutcome: ...


class Broadcaster(Protocol):
    """The one method the pool needs from the WS hub (structural seam)."""

    async def broadcast(self, message: WsMessage) -> None: ...


class _FinalizeResult(Protocol):
    """The finalizer output fields the pool reads to build ``batch_finished``."""

    m3u_paths: list[Path]
    save_file_path: Path | None


class Finalizer(Protocol):
    """The one method the pool needs from the batch finalizer (structural seam)."""

    async def finalize(self, batch_id: UUID) -> _FinalizeResult: ...


class _ProgressHolder:
    """A GIL-safe latch: the engine's ``on_progress`` (running in its worker
    thread) writes the latest event; the pump coroutine reads it."""

    __slots__ = ("latest",)

    def __init__(self) -> None:
        self.latest: ProgressEvent | None = None

    def set(self, event: ProgressEvent) -> None:
        self.latest = event


class DownloadWorkerPool:
    """Run queued download jobs concurrently through the engine (CONTRACT 2)."""

    def __init__(
        self,
        *,
        sessionmaker: async_sessionmaker[AsyncSession],
        engine: Engine,  # DownloadEngine (prod) / FakeDownloadEngine (tests)
        hub: Broadcaster,
        settings: Settings,
        finalizer: Finalizer,
        clock: Clock,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._engine = engine
        self._hub = hub
        self._settings = settings
        self._finalizer = finalizer
        self._clock = clock

        self._queue: asyncio.Queue[UUID] = asyncio.Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._running: dict[UUID, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()  # claim + finalize check-and-set
        self._shutting_down = False
        self._closed = False
        self._known_paths: tuple[Path, ...] = ()
        # Pump wakes far more often than it flushes; the throttle (CONTRACT 5)
        # gates the actual row-write + broadcast cadence to progress_throttle_ms.
        self._pump_tick_s = min(0.05, max(0.005, settings.progress_throttle_ms / 1000.0))

    def _now(self) -> datetime:
        return self._clock.now()

    # ------------------------------------------------------------ lifecycle
    async def start(self) -> None:
        """Recover orphans, sweep temp, re-enqueue queued ids, spawn workers."""
        # 1. crash recovery (running -> queued, attempts+=1) + temp sweep.
        async with self._sessionmaker() as session:
            await DownloadJobRepository(session).recover_orphaned(now=self._now())
            await session.commit()
        self._sweep_temp_dir()
        if self._settings.download_scan_existing:
            self._known_paths = self._scan_library()

        # 2. re-enqueue every queued id (recovered + pre-existing), FIFO.
        async with self._sessionmaker() as session:
            queued_ids = await DownloadJobRepository(session).ids_by_status(DownloadStatus.QUEUED)
        for job_id in queued_ids:
            self._queue.put_nowait(job_id)

        # 3. spawn the worker tasks.
        for _ in range(max(1, self._settings.download_concurrency)):
            self._workers.append(asyncio.create_task(self._worker_loop()))

        # 4. finalize any batch already fully-terminal but never finalized (a
        #    crash between the last job's terminal write and its finalize).
        await self._finalize_settled_batches()

    async def enqueue(self, job_ids: Sequence[UUID]) -> None:
        """Push freshly-committed job ids onto the queue so idle workers wake."""
        for job_id in job_ids:
            self._queue.put_nowait(job_id)

    async def request_cancel(self, job_id: UUID) -> bool:
        """Cancel a running task, or conditionally cancel a still-queued job."""
        task = self._running.get(job_id)
        if task is not None:
            task.cancel()
            return True
        async with self._sessionmaker() as session:
            cancelled = await DownloadJobRepository(session).cancel_if_queued(
                job_id, now=self._now()
            )
            await session.commit()
        if cancelled:
            batch_id = await self._batch_id_of(job_id)
            await self._hub.broadcast(WsJobCancelled(job_id=job_id, batch_id=batch_id))
            if batch_id is not None:
                await self._maybe_finalize(batch_id)
        return cancelled

    async def shutdown(self, *, drain_timeout_s: float | None = None) -> None:
        """Drain in-flight jobs up to the timeout, then re-queue the stragglers."""
        if self._closed:
            return
        self._shutting_down = True
        timeout = (
            drain_timeout_s
            if drain_timeout_s is not None
            else self._settings.download_drain_timeout_s
        )

        inflight = list(self._running.values())
        if inflight:
            await asyncio.wait(inflight, timeout=timeout)
        # Cancel any job still running past the window: its handler re-queues it
        # (running -> queued) because _shutting_down is set.
        stragglers = list(self._running.values())
        for task in stragglers:
            task.cancel()
        if stragglers:
            await asyncio.wait(stragglers)

        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        # Belt-and-suspenders: a worker may have claimed a fresh job between the
        # straggler snapshot above and its own cancellation (cancelling the worker
        # task only unwinds its ``asyncio.wait`` waiter, never the spawned
        # ``_run_job`` child). Cancel any such leaked job so none runs detached past
        # shutdown — otherwise the lifespan disposes the DB engine underneath it and
        # the row is left ``running`` until the next boot's recover_orphaned.
        leaked = list(self._running.values())
        for task in leaked:
            task.cancel()
        if leaked:
            await asyncio.gather(*leaked, return_exceptions=True)
        self._closed = True

    # ------------------------------------------------------------ worker loop
    async def _worker_loop(self) -> None:
        while True:
            try:
                job_id = await self._queue.get()
            except asyncio.CancelledError:
                return
            # Stop pulling once a drain has begun: a job popped here would be a
            # *fresh* claim the shutdown snapshot has already passed, so it would
            # run detached past shutdown. Leave it ``queued`` for the next boot.
            if self._shutting_down:
                self._queue.task_done()
                return
            task = asyncio.create_task(self._run_job(job_id))
            self._running[job_id] = task
            # ``wait`` never re-raises the job's cancellation/errors into the
            # loop, so one cancelled or failing job never kills the worker.
            await asyncio.wait({task})
            self._queue.task_done()

    async def _run_job(self, job_id: UUID) -> None:
        batch_id: UUID | None = None
        request: DownloadRequest | None = None
        try:
            async with self._sessionmaker() as session:
                async with self._lock:
                    job = await DownloadJobRepository(session).claim(job_id, now=self._now())
                    await session.commit()
                if job is None:  # cancelled / already claimed / gone
                    return
                batch_id = job.batch_id
                await self._hub.broadcast(WsJobStarted(job_id=job_id, batch_id=batch_id))

                request = await self._build_request(session, job)
                if request is None:  # no viable match -> fail fast, never call the engine
                    await self._mark_failed(
                        session, job_id, batch_id, step="fetch", error="no viable match"
                    )
                    return

                outcome = await self._run_engine(job_id, batch_id, request)
                await self._finish(session, job_id, batch_id, outcome)
        except asyncio.CancelledError:
            await self._on_cancelled(job_id, batch_id, request)
            if self._shutting_down:
                raise  # let the worker task exit
        finally:
            self._running.pop(job_id, None)
            if batch_id is not None and not self._shutting_down:
                await self._maybe_finalize(batch_id)

    async def _run_engine(
        self, job_id: UUID, batch_id: UUID | None, request: DownloadRequest
    ) -> DownloadOutcome:
        """Run the engine under a progress pump; retry an embed failure once."""
        holder = _ProgressHolder()
        pump = asyncio.create_task(self._pump(job_id, batch_id, holder))
        try:
            outcome = await self._engine.download(request, on_progress=holder.set)
            if outcome.status is OutcomeStatus.FAILED and outcome.failed_step == "embed":
                # Handoff: an embed failure leaves a converted-but-untagged file at
                # output_path; a plain re-run with SKIP would skip it forever, so
                # re-embed over it with overwrite=METADATA (no re-fetch/re-convert).
                retry = request.model_copy(update={"overwrite": OverwriteMode.METADATA})
                outcome = await self._engine.download(retry, on_progress=holder.set)
            return outcome
        finally:
            await self._stop_pump(pump)

    # ------------------------------------------------------------ progress pump
    async def _pump(self, job_id: UUID, batch_id: UUID | None, holder: _ProgressHolder) -> None:
        """Persist + broadcast throttled whole-job progress until cancelled."""
        throttle = ProgressThrottle(min_interval_ms=self._settings.progress_throttle_ms)
        loop = asyncio.get_running_loop()
        async with self._sessionmaker() as session:
            repo = DownloadJobRepository(session)
            while True:
                await asyncio.sleep(self._pump_tick_s)
                event = holder.latest
                if event is None:
                    continue
                overall = overall_progress(event.phase, event.percent)
                is_terminal = event.phase in _TERMINAL_PHASES
                if throttle.should_flush(
                    now=loop.time(), phase=event.phase, overall=overall, is_terminal=is_terminal
                ):
                    # Shield the write+commit: ``_stop_pump`` cancels this task on every
                    # job teardown (completion *and* cancellation), and a cancel landing
                    # mid-commit aborts the transaction with the connection still holding
                    # the SQLite write lock — the job's terminal write (``_finish`` /
                    # ``_on_cancelled``) then fails with "database is locked". A bare
                    # ``await asyncio.shield(coro)`` does *not* keep the flush from racing:
                    # on cancel the awaiter unwinds immediately while the flush runs
                    # detached on ``session``, which this ``async with`` is now closing —
                    # a concurrent-session-use race. So hold a reference and, on cancel,
                    # await the in-flight flush to completion *before* re-raising, so the
                    # write+commit finishes (releasing the lock) before the session closes.
                    flush = asyncio.ensure_future(
                        self._flush_progress(session, repo, job_id, overall)
                    )
                    try:
                        await asyncio.shield(flush)
                    except asyncio.CancelledError:
                        with contextlib.suppress(Exception):
                            await flush
                        raise
                    await self._hub.broadcast(
                        WsProgress(
                            job_id=job_id,
                            batch_id=batch_id,
                            phase=event.phase.value,
                            percent=event.percent,
                            overall=overall,
                        )
                    )

    async def _flush_progress(
        self, session: AsyncSession, repo: DownloadJobRepository, job_id: UUID, overall: float
    ) -> None:
        await repo.update_progress(job_id, progress=overall)
        await session.commit()

    @staticmethod
    async def _stop_pump(pump: asyncio.Task[None]) -> None:
        pump.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pump

    # ------------------------------------------------------------ transitions
    async def _finish(
        self,
        session: AsyncSession,
        job_id: UUID,
        batch_id: UUID | None,
        outcome: DownloadOutcome,
    ) -> None:
        """Map an engine outcome onto the job's terminal state + final WS frames.

        Unlike ``_on_cancelled`` (fresh session + ``_commit_with_locked_retry``),
        these terminal commits reuse the ``_run_job`` session and are NOT
        lock-retried: by the time ``_finish`` runs the job's progress pump has
        been stopped and its shielded flush awaited, so this session has no
        competing in-flight writer; remaining cross-job writers ride WAL (prod)
        where ``busy_timeout`` suffices. Only the cancel path races its own
        teardown, which is why only it needs the fresh-session retry.
        """
        repo = DownloadJobRepository(session)
        if outcome.status is OutcomeStatus.DOWNLOADED:
            output_path = str(outcome.path) if outcome.path is not None else None
            await repo.mark_completed(
                job_id, output_path=output_path, skip_reason=None, now=self._now()
            )
            await session.commit()
            await self._broadcast_final_progress(job_id, batch_id, ProgressPhase.DONE)
            await self._hub.broadcast(
                WsJobFinished(
                    job_id=job_id,
                    batch_id=batch_id,
                    status="completed",
                    skipped=False,
                    skip_reason=None,
                    output_path=output_path,
                )
            )
        elif outcome.status is OutcomeStatus.SKIPPED:
            reason = outcome.skip_reason.value if outcome.skip_reason is not None else None
            output_path = str(outcome.path) if outcome.path is not None else None
            await repo.mark_completed(
                job_id, output_path=output_path, skip_reason=reason, now=self._now()
            )
            await session.commit()
            await self._broadcast_final_progress(job_id, batch_id, ProgressPhase.SKIPPED)
            await self._hub.broadcast(
                WsJobFinished(
                    job_id=job_id,
                    batch_id=batch_id,
                    status="completed",
                    skipped=True,
                    skip_reason=reason,
                    output_path=output_path,
                )
            )
        else:  # FAILED
            await self._mark_failed(
                session,
                job_id,
                batch_id,
                step=outcome.failed_step or "unknown",
                error=outcome.error,
            )

    async def _mark_failed(
        self,
        session: AsyncSession,
        job_id: UUID,
        batch_id: UUID | None,
        *,
        step: str,
        error: str | None,
    ) -> None:
        await DownloadJobRepository(session).mark_failed(
            job_id, error_step=step, error_message=error, now=self._now()
        )
        await session.commit()
        await self._hub.broadcast(
            WsJobFailed(job_id=job_id, batch_id=batch_id, step=step, error=error)
        )

    async def _broadcast_final_progress(
        self, job_id: UUID, batch_id: UUID | None, phase: ProgressPhase
    ) -> None:
        await self._hub.broadcast(
            WsProgress(
                job_id=job_id, batch_id=batch_id, phase=phase.value, percent=100, overall=1.0
            )
        )

    async def _on_cancelled(
        self, job_id: UUID, batch_id: UUID | None, request: DownloadRequest | None
    ) -> None:
        """Handle a cancelled in-flight job: drain re-queue vs user cancel.

        Uses a *fresh* session — the ``_run_job`` session has already unwound.
        """
        if self._shutting_down:
            # Graceful shutdown: put the job back so the next boot resumes it.
            await self._commit_with_locked_retry(
                lambda session: DownloadJobRepository(session).requeue(job_id, now=self._now())
            )
            return
        await self._commit_with_locked_retry(
            lambda session: DownloadJobRepository(session).mark_cancelled(job_id, now=self._now())
        )
        self._delete_partial(request)
        await self._hub.broadcast(WsJobCancelled(job_id=job_id, batch_id=batch_id))

    async def _commit_with_locked_retry(
        self,
        work: Callable[[AsyncSession], Awaitable[object]],
        *,
        attempts: int = 6,
        base_delay_s: float = 0.03,
    ) -> None:
        """Run ``work`` + commit on a fresh session, retrying "database is locked".

        The terminal cancel write races the just-cancelled job's own connection
        teardown (its read snapshot) and any concurrent writer, so under SQLite it
        can hit ``SQLITE_BUSY``/``SQLITE_BUSY_SNAPSHOT`` — which ``busy_timeout`` does
        not cover for a read→write upgrade. Rolling back and re-running on a fresh
        snapshot clears it; without this the cancel is silently lost and the job is
        stranded non-terminal. Non-lock errors and the last attempt propagate.
        """
        for attempt in range(attempts):
            try:
                async with self._sessionmaker() as session:
                    await work(session)
                    await session.commit()
                return
            except OperationalError as exc:
                if "locked" not in str(exc).lower() or attempt == attempts - 1:
                    raise
                await asyncio.sleep(base_delay_s * (attempt + 1))

    # ------------------------------------------------------------ finalize
    async def _maybe_finalize(self, batch_id: UUID) -> None:
        """Finalize the batch exactly once when its last job reaches terminal."""
        async with self._lock, self._sessionmaker() as session:
            repo = DownloadBatchRepository(session)
            if await repo.pending_count(batch_id) != 0:
                return
            claimed = await repo.mark_finalized(batch_id, now=self._now())
            await session.commit()
        if not claimed:
            return
        result = await self._finalizer.finalize(batch_id)
        counts = await self._ws_counts(batch_id)
        await self._hub.broadcast(
            WsBatchFinished(
                batch_id=batch_id,
                completed=counts["completed"],
                failed=counts["failed"],
                skipped=counts["skipped"],
                cancelled=counts["cancelled"],
                m3u_paths=[str(path) for path in result.m3u_paths],
                save_file_path=(
                    str(result.save_file_path) if result.save_file_path is not None else None
                ),
            )
        )

    async def _finalize_settled_batches(self) -> None:
        async with self._sessionmaker() as session:
            batch_ids = await DownloadBatchRepository(session).finalizable_ids()
        for batch_id in batch_ids:
            await self._maybe_finalize(batch_id)

    async def _ws_counts(self, batch_id: UUID) -> dict[str, int]:
        """WS-shaped tally: completed (real) / skipped / failed / cancelled."""
        async with self._sessionmaker() as session:
            jobs = await DownloadBatchRepository(session).jobs(batch_id)
        counts = {"completed": 0, "skipped": 0, "failed": 0, "cancelled": 0}
        for job in jobs:
            if job.status is DownloadStatus.COMPLETED:
                counts["skipped" if job.skip_reason else "completed"] += 1
            elif job.status is DownloadStatus.FAILED:
                counts["failed"] += 1
            elif job.status is DownloadStatus.CANCELLED:
                counts["cancelled"] += 1
        return counts

    # ------------------------------------------------------------ request build
    async def _build_request(
        self, session: AsyncSession, job: DownloadJob
    ) -> DownloadRequest | None:
        """Assemble a Plan 4 :class:`DownloadRequest` from the job/batch/track/match.

        Returns ``None`` when the job carries no viable match (``match_id`` NULL)
        so the caller fails it at the fetch step without ever calling the engine.
        """
        if job.match_id is None or job.track_id is None:
            return None
        batch = (
            await DownloadBatchRepository(session).get(job.batch_id)
            if job.batch_id is not None
            else None
        )
        track_model = await TrackRepository(session).get(job.track_id)
        match_model = await MatchRepository(session).get(job.match_id)
        if track_model is None or match_model is None:
            return None

        core_track = self._core_track(track_model, job, batch)
        candidate = self._candidate(match_model, core_track)

        output_format = OutputFormat(
            job.output_format
            or (batch.output_format if batch is not None else None)
            or self._settings.default_output_format.value
        )
        bitrate = (
            job.bitrate
            or (batch.bitrate if batch is not None else None)
            or self._settings.default_bitrate
        )
        output_template = (
            job.output_template
            or (batch.output_template if batch is not None else None)
            or self._settings.default_output_template
        )

        # Recovery integrity (CONTRACT 1): a re-run job (attempts>0) may sit on a
        # converted-but-untagged file, so FORCE a full re-fetch/convert/embed
        # rather than trusting file existence. First attempts honour the batch's
        # overwrite mode (the client's ``overwrite=`` on submit; NULL ⇒ SKIP).
        if job.attempts > 0:
            overwrite = OverwriteMode.FORCE
        elif batch is not None and batch.overwrite is not None:
            overwrite = OverwriteMode(batch.overwrite)
        else:
            overwrite = OverwriteMode.SKIP

        archive: frozenset[str] = frozenset()
        if batch is not None and batch.update_archive:
            archive = load_archive(self._archive_path())

        detect_formats = tuple(
            OutputFormat(value) for value in self._settings.download_detect_formats
        )

        return DownloadRequest(
            track=core_track,
            candidate=candidate,
            output_template=output_template,
            output_format=output_format,
            bitrate=bitrate,
            overwrite=overwrite,
            restrict=self._settings.download_restrict,
            max_filename_length=self._settings.download_max_filename_length,
            id3_separator=self._settings.download_id3_separator,
            detect_formats=detect_formats,
            skip_explicit=self._settings.download_skip_explicit,
            respect_skip_file=self._settings.download_respect_skip_file,
            create_skip_file=self._settings.download_create_skip_file,
            retain_track_cover=self._settings.download_retain_track_cover,
            embed_lyrics=batch.embed_lyrics if batch is not None else True,
            generate_lrc=batch.generate_lrc if batch is not None else False,
            sponsor_block=batch.sponsor_block if batch is not None else False,
            archive=archive,
            known_paths=self._known_paths,
            list_name=batch.name if batch is not None else None,
            list_position=job.list_position,
            list_length=batch.total_jobs if batch is not None else None,
        )

    def _core_track(
        self, track: TrackModel, job: DownloadJob, batch: DownloadBatch | None
    ) -> Track:
        """Build a core :class:`Track` from the canonical row (+ playlist parity)."""
        album = track.album
        album_ref: AlbumRef | None = None
        if album is not None:
            album_ref = AlbumRef(
                name=album.name,
                album_artist=album.album_artist,
                year=album.year,
                track_count=album.track_count,
                cover_url=album.cover_url,
            )

        track_number = track.track_number
        # v4 playlist_numbering parity: renumber tracks by list position and title
        # the album after the playlist so file/tag numbering follows the playlist.
        if (
            self._settings.download_playlist_numbering
            and batch is not None
            and batch.kind is BatchKind.PLAYLIST
        ):
            track_number = job.list_position
            if batch.name:
                base = album_ref
                album_ref = AlbumRef(
                    name=batch.name,
                    album_artist=base.album_artist if base is not None else None,
                    year=base.year if base is not None else None,
                    track_count=base.track_count if base is not None else None,
                    cover_url=base.cover_url if base is not None else None,
                )

        artists = tuple(artist.name for artist in track.artists) or (track.name,)
        # retain_track_cover gating (handoff): only populate a track-level cover
        # when retained; the canonical row carries none, so this stays None in v1
        # and playback falls back to the album cover.
        cover_url = None
        return Track(
            name=track.name,
            artists=artists,
            duration_ms=track.duration_ms,
            album=album_ref,
            isrc=track.isrc,
            explicit=track.explicit,
            track_number=track_number,
            disc_number=track.disc_number,
            genres=tuple(track.genres),
            year=track.year,
            popularity=track.popularity,
            cover_url=cover_url if self._settings.download_retain_track_cover else None,
        )

    @staticmethod
    def _candidate(match: Match, core_track: Track) -> AudioCandidate:
        return AudioCandidate(
            provider=match.target_provider,
            provider_id=match.target_id,
            url=match.target_url,
            name=match.candidate_name or core_track.name,
            artists=tuple(match.candidate_artists or ()),
            duration_ms=match.candidate_duration_ms,
        )

    # ------------------------------------------------------------ filesystem
    def _archive_path(self) -> Path:
        return self._settings.effective_library_path() / _ARCHIVE_FILENAME

    def _sweep_temp_dir(self) -> None:
        """Best-effort clear of crash-orphaned partial fetches in the temp dir."""
        temp_dir = self._settings.effective_temp_dir()
        if not temp_dir.exists():
            return
        for entry in temp_dir.iterdir():
            if entry.is_file():
                with contextlib.suppress(OSError):
                    entry.unlink()

    def _scan_library(self) -> tuple[Path, ...]:
        """One-shot scan of the library root for existing audio files (v4 parity)."""
        root = self._settings.effective_library_path()
        if not root.exists():
            return ()
        return tuple(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in _AUDIO_SUFFIXES
        )

    def _delete_partial(self, request: DownloadRequest | None) -> None:
        """Best-effort removal of a cancelled job's partial output file."""
        if request is None:
            return
        try:
            path = self._planned_output_path(request)
        except Exception:  # noqa: BLE001 - a rendering error just means nothing to clean
            return
        if path is not None and path.exists():
            with contextlib.suppress(OSError):
                path.unlink()

    def _planned_output_path(self, request: DownloadRequest) -> Path | None:
        return build_output_path(request, self._settings.download_config())

    # ------------------------------------------------------------ small reads
    async def _batch_id_of(self, job_id: UUID) -> UUID | None:
        async with self._sessionmaker() as session:
            job = await DownloadJobRepository(session).get(job_id)
            return job.batch_id if job is not None else None
