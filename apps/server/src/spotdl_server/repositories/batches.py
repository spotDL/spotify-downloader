"""Download-batch repository: the sole holder of ``download_batches`` query code.

A batch groups the N jobs produced by one ``POST /downloads`` and holds the
batch-level post-processing config the finalizer needs (CONTRACT 4/7). Takes/
returns ORM models or plain values, never Pydantic/HTTP types, and never commits —
except :meth:`mark_finalized`, the idempotent finalization race guard the caller
commits immediately.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from spotdl_server.db.enums import BatchKind, DownloadStatus
from spotdl_server.db.models import DownloadBatch, DownloadJob


class DownloadBatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        kind: BatchKind,
        source: str | None,
        name: str | None,
        output_format: str | None,
        bitrate: str | None,
        output_template: str | None,
        generate_m3u: bool,
        m3u_template: str | None,
        generate_save_file: bool,
        save_file_path: str | None,
        update_archive: bool,
        embed_lyrics: bool,
        generate_lrc: bool,
        sponsor_block: bool,
        total_jobs: int,
        requested_by: UUID | None,
    ) -> DownloadBatch:
        """Insert a batch row (``finalized_at=NULL``) and return it (with its id)."""
        batch = DownloadBatch(
            kind=kind,
            source=source,
            name=name,
            output_format=output_format,
            bitrate=bitrate,
            output_template=output_template,
            generate_m3u=generate_m3u,
            m3u_template=m3u_template,
            generate_save_file=generate_save_file,
            save_file_path=save_file_path,
            update_archive=update_archive,
            embed_lyrics=embed_lyrics,
            generate_lrc=generate_lrc,
            sponsor_block=sponsor_block,
            total_jobs=total_jobs,
            requested_by=requested_by,
        )
        self.session.add(batch)
        await self.session.flush()
        return batch

    async def get(self, batch_id: UUID) -> DownloadBatch | None:
        return await self.session.get(DownloadBatch, batch_id)

    async def jobs(self, batch_id: UUID) -> list[DownloadJob]:
        """Every job in the batch, ordered by ``list_position`` (then ``created_at``)."""
        result = await self.session.execute(
            select(DownloadJob)
            .where(DownloadJob.batch_id == batch_id)
            .order_by(
                DownloadJob.list_position.asc().nulls_last(),
                DownloadJob.created_at.asc(),
            )
        )
        return list(result.scalars().all())

    async def counts(self, batch_id: UUID) -> dict[str, int]:
        """A per-status tally for the batch (every status present, zero-filled)."""
        result = await self.session.execute(
            select(DownloadJob.status, func.count())
            .where(DownloadJob.batch_id == batch_id)
            .group_by(DownloadJob.status)
        )
        tally = {status.value: 0 for status in DownloadStatus}
        for status, count in result.all():
            tally[status.value] = int(count)
        return tally

    async def pending_count(self, batch_id: UUID) -> int:
        """The number of not-yet-terminal jobs (``queued`` + ``running``)."""
        total = await self.session.scalar(
            select(func.count())
            .select_from(DownloadJob)
            .where(
                DownloadJob.batch_id == batch_id,
                DownloadJob.status.in_((DownloadStatus.QUEUED, DownloadStatus.RUNNING)),
            )
        )
        return int(total or 0)

    async def finalizable_ids(self) -> list[UUID]:
        """Ids of batches whose jobs are all terminal but were never finalized.

        A batch qualifies when ``finalized_at IS NULL``, it has at least one job
        (``total_jobs > 0``), and no job is still ``queued``/``running``. The pool
        finalizes these at boot to recover from a crash between the last job's
        terminal write and its finalize (idempotency still guarded by
        :meth:`mark_finalized`).
        """
        pending = (
            select(DownloadJob.batch_id)
            .where(
                DownloadJob.status.in_((DownloadStatus.QUEUED, DownloadStatus.RUNNING)),
                DownloadJob.batch_id.is_not(None),
            )
            .distinct()
        )
        result = await self.session.execute(
            select(DownloadBatch.id).where(
                DownloadBatch.finalized_at.is_(None),
                DownloadBatch.total_jobs > 0,
                DownloadBatch.id.not_in(pending),
            )
        )
        return list(result.scalars().all())

    async def mark_finalized(self, batch_id: UUID, *, now: datetime) -> bool:
        """Stamp ``finalized_at`` exactly once (idempotent finalization race guard).

        Conditional ``UPDATE ... SET finalized_at=now WHERE id=:id AND
        finalized_at IS NULL``; returns ``True`` on the transitioning call and
        ``False`` on every later one — so a concurrent last-two-jobs race finalizes
        exactly once. The caller commits immediately.
        """
        result = await self.session.execute(
            update(DownloadBatch)
            .where(DownloadBatch.id == batch_id, DownloadBatch.finalized_at.is_(None))
            .values(finalized_at=now)
            .execution_options(synchronize_session=False)
        )
        if cast("CursorResult[Any]", result).rowcount == 0:
            return False
        batch = await self.session.get(DownloadBatch, batch_id)
        if batch is not None:
            # Reflect the committed stamp on the identity-mapped row without a
            # naive-datetime reload (SQLite drops the tz on DateTime(timezone=True)).
            set_committed_value(batch, "finalized_at", now)
        return True
