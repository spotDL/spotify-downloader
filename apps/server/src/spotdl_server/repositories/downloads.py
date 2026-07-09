"""Download-job repository: the sole holder of ``download_jobs`` query code (§6.1).

Drives the Plan 7 queue's row lifecycle (CONTRACT 1). Every method takes/returns
ORM models or plain values — never Pydantic/HTTP types — and **never commits**:
the caller owns the unit of work. The exception in spirit are the atomic status
transitions (``claim`` / ``cancel_if_queued`` / ``recover_orphaned``): the caller
commits them immediately, but the flush/commit itself still lives with the caller
(the worker pool), so this class only ever ``flush``es.

**Claim safety** rides on the single-process ownership invariant (CONTRACT 2): the
conditional ``UPDATE ... WHERE status='queued'`` transitions a row at most once, so
two workers holding the pool's ``asyncio.Lock`` never double-run a job. A
multi-process design would instead use ``SELECT ... FOR UPDATE SKIP LOCKED`` — a
documented non-goal for v1.
"""

from __future__ import annotations

import builtins
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from spotdl_server.db.enums import DownloadStatus
from spotdl_server.db.models import DownloadJob

# ``error_message`` is a ``Text`` column (effectively unbounded); a runaway
# traceback from the engine is truncated to keep rows bounded and log-friendly.
_MAX_ERROR_MESSAGE = 4000
# ``error_step`` is ``String(32)``.
_MAX_ERROR_STEP = 32


class DownloadJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        batch_id: UUID | None,
        track_id: UUID | None,
        match_id: UUID | None,
        output_format: str | None,
        bitrate: str | None,
        output_template: str | None,
        list_position: int | None,
        requested_by: UUID | None,
    ) -> DownloadJob:
        """Insert a fresh ``queued`` job (``progress=0``, ``attempts=0``)."""
        job = DownloadJob(
            batch_id=batch_id,
            track_id=track_id,
            match_id=match_id,
            status=DownloadStatus.QUEUED,
            list_position=list_position,
            output_format=output_format,
            bitrate=bitrate,
            output_template=output_template,
            progress=0.0,
            attempts=0,
            requested_by=requested_by,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get(self, job_id: UUID) -> DownloadJob | None:
        return await self.session.get(DownloadJob, job_id)

    async def list(
        self,
        *,
        status: DownloadStatus | None = None,
        batch_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DownloadJob], int]:
        """A newest-first page of jobs + the total match count (before paging).

        The total is independent of ``limit``/``offset`` so a client can render
        pagination controls. Optional ``status`` / ``batch_id`` filters compose.
        """
        filters = []
        if status is not None:
            filters.append(DownloadJob.status == status)
        if batch_id is not None:
            filters.append(DownloadJob.batch_id == batch_id)

        total = await self.session.scalar(
            select(func.count()).select_from(DownloadJob).where(*filters)
        )
        result = await self.session.execute(
            select(DownloadJob)
            .where(*filters)
            .order_by(DownloadJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    async def claim(self, job_id: UUID, *, now: datetime) -> DownloadJob | None:
        """Atomically transition ``queued → running`` (returns the row iff it moved).

        A conditional ``UPDATE ... SET status='running', started_at=now, progress=0
        WHERE id=:id AND status='queued'``. Returns ``None`` when the row was no
        longer queued (cancelled meanwhile / already claimed / gone) — the
        no-double-run guard. The caller holds the pool lock and commits.
        """
        result = await self.session.execute(
            update(DownloadJob)
            .where(DownloadJob.id == job_id, DownloadJob.status == DownloadStatus.QUEUED)
            .values(status=DownloadStatus.RUNNING, started_at=now, progress=0.0)
            .execution_options(synchronize_session=False)
        )
        if cast("CursorResult[Any]", result).rowcount == 0:
            return None
        job = await self.session.get(DownloadJob, job_id)
        if job is not None:
            # The DB row is already transitioned by the bulk UPDATE; reflect it on
            # the identity-mapped instance as committed state (tz-aware ``now``
            # preserved; SQLite would otherwise reload a naive datetime) without a
            # redundant second write.
            set_committed_value(job, "status", DownloadStatus.RUNNING)
            set_committed_value(job, "started_at", now)
            set_committed_value(job, "progress", 0.0)
        return job

    async def mark_completed(
        self, job_id: UUID, *, output_path: str | None, skip_reason: str | None, now: datetime
    ) -> None:
        """``running → completed``: a real download (``skip_reason=None``) or a skip."""
        job = await self.session.get(DownloadJob, job_id)
        if job is None:
            return
        job.status = DownloadStatus.COMPLETED
        job.output_path = output_path
        job.skip_reason = skip_reason
        job.progress = 1.0
        job.finished_at = now
        await self.session.flush()

    async def mark_failed(
        self, job_id: UUID, *, error_step: str | None, error_message: str | None, now: datetime
    ) -> None:
        """``running → failed``: stamp the failed step + (truncated) error message."""
        job = await self.session.get(DownloadJob, job_id)
        if job is None:
            return
        job.status = DownloadStatus.FAILED
        job.error_step = error_step[:_MAX_ERROR_STEP] if error_step is not None else None
        job.error_message = (
            error_message[:_MAX_ERROR_MESSAGE] if error_message is not None else None
        )
        job.finished_at = now
        await self.session.flush()

    async def mark_cancelled(self, job_id: UUID, *, now: datetime) -> None:
        """``running → cancelled`` (user cancel of an in-flight job)."""
        job = await self.session.get(DownloadJob, job_id)
        if job is None:
            return
        job.status = DownloadStatus.CANCELLED
        job.finished_at = now
        await self.session.flush()

    async def requeue(self, job_id: UUID, *, now: datetime) -> None:
        """``running → queued`` on graceful-shutdown drain: reset + bump ``attempts``.

        ``attempts > 0`` makes the worker force ``overwrite=FORCE`` on the re-run
        (recovery-integrity rule, CONTRACT 1) so a suspect partial file is redone.
        """
        job = await self.session.get(DownloadJob, job_id)
        if job is None:
            return
        job.status = DownloadStatus.QUEUED
        job.started_at = None
        job.progress = 0.0
        job.attempts = job.attempts + 1
        await self.session.flush()

    async def cancel_if_queued(self, job_id: UUID, *, now: datetime) -> bool:
        """Atomically cancel a not-yet-claimed job (``queued → cancelled``).

        Conditional ``UPDATE ... WHERE status='queued'``; returns ``True`` iff the
        row transitioned (``False`` when already running/terminal/gone). The caller
        commits immediately.
        """
        result = await self.session.execute(
            update(DownloadJob)
            .where(DownloadJob.id == job_id, DownloadJob.status == DownloadStatus.QUEUED)
            .values(status=DownloadStatus.CANCELLED, finished_at=now)
            .execution_options(synchronize_session=False)
        )
        if cast("CursorResult[Any]", result).rowcount == 0:
            return False
        job = await self.session.get(DownloadJob, job_id)
        if job is not None:
            set_committed_value(job, "status", DownloadStatus.CANCELLED)
            set_committed_value(job, "finished_at", now)
        return True

    async def update_progress(self, job_id: UUID, *, progress: float) -> None:
        """Persist the whole-job ``progress`` (0..1); throttled by the pump (CONTRACT 5)."""
        job = await self.session.get(DownloadJob, job_id)
        if job is None:
            return
        job.progress = progress
        await self.session.flush()

    async def recover_orphaned(self, *, now: datetime) -> builtins.list[UUID]:
        """Return every ``running`` row to ``queued`` at boot (crash recovery).

        A single conditional ``UPDATE ... WHERE status='running'`` (reset
        ``started_at``/``progress``, bump ``attempts``). Justified by single-process
        ownership: before the pool starts, any ``running`` row is orphaned by a
        crashed prior process. Returns the recovered ids so the pool re-enqueues them.
        """
        ids = list(
            (
                await self.session.execute(
                    select(DownloadJob.id).where(DownloadJob.status == DownloadStatus.RUNNING)
                )
            )
            .scalars()
            .all()
        )
        if ids:
            await self.session.execute(
                update(DownloadJob)
                .where(DownloadJob.status == DownloadStatus.RUNNING)
                .values(
                    status=DownloadStatus.QUEUED,
                    started_at=None,
                    progress=0.0,
                    attempts=DownloadJob.attempts + 1,
                )
                .execution_options(synchronize_session=False)
            )
            # Re-sync any identity-mapped recovered rows to the DB so a caller
            # reading them in this session sees the transition (async refresh —
            # ``expire_all`` would force a sync lazy-load outside the greenlet).
            for job_id in ids:
                obj = await self.session.get(DownloadJob, job_id)
                if obj is not None:
                    await self.session.refresh(obj)
        return ids

    async def ids_by_status(self, status: DownloadStatus) -> builtins.list[UUID]:
        """Every job id in ``status``, oldest-first (FIFO re-enqueue on ``start()``)."""
        result = await self.session.execute(
            select(DownloadJob.id)
            .where(DownloadJob.status == status)
            .order_by(DownloadJob.created_at.asc())
        )
        return list(result.scalars().all())
