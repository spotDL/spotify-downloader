"""Task 3 — ``DownloadBatchRepository`` (create/get/aggregate/finalize)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from spotdl_server.db.enums import BatchKind, DownloadStatus
from spotdl_server.repositories.batches import DownloadBatchRepository
from spotdl_server.repositories.downloads import DownloadJobRepository
from sqlalchemy.ext.asyncio import AsyncSession

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


async def _mk_batch(session: AsyncSession, **over: object) -> object:
    repo = DownloadBatchRepository(session)
    kwargs: dict[str, object] = dict(
        kind=BatchKind.PLAYLIST,
        source="https://open.spotify.com/playlist/x",
        name="My Playlist",
        output_format="mp3",
        bitrate="auto",
        output_template="t",
        overwrite=None,
        generate_m3u=True,
        m3u_template="{list}",
        generate_save_file=True,
        save_file_path="/m/x.spotdl",
        update_archive=False,
        embed_lyrics=True,
        generate_lrc=False,
        sponsor_block=False,
        total_jobs=3,
        requested_by=None,
    )
    kwargs.update(over)
    return await repo.create(**kwargs)  # type: ignore[arg-type]


async def _mk_job(jobs: DownloadJobRepository, batch_id: object, pos: int) -> object:
    return await jobs.create(
        batch_id=batch_id,
        track_id=None,
        match_id=None,
        output_format="mp3",
        bitrate="auto",
        output_template="{title}",
        list_position=pos,
        requested_by=None,
    )


async def test_create_and_get(session: AsyncSession) -> None:
    repo = DownloadBatchRepository(session)
    batch = await _mk_batch(session)
    fetched = await repo.get(batch.id)  # type: ignore[attr-defined]
    assert fetched is not None
    assert fetched.kind is BatchKind.PLAYLIST
    assert fetched.name == "My Playlist"
    assert fetched.total_jobs == 3
    assert fetched.finalized_at is None


async def test_get_unknown_returns_none(session: AsyncSession) -> None:
    repo = DownloadBatchRepository(session)
    assert await repo.get(uuid4()) is None


async def test_jobs_ordered_by_list_position(session: AsyncSession) -> None:
    repo = DownloadBatchRepository(session)
    jobs = DownloadJobRepository(session)
    batch = await _mk_batch(session)
    await _mk_job(jobs, batch.id, 2)  # type: ignore[attr-defined]
    await _mk_job(jobs, batch.id, 1)  # type: ignore[attr-defined]
    await _mk_job(jobs, batch.id, 3)  # type: ignore[attr-defined]
    listed = await repo.jobs(batch.id)  # type: ignore[attr-defined]
    assert [j.list_position for j in listed] == [1, 2, 3]


async def test_counts_and_pending_across_mixed_statuses(session: AsyncSession) -> None:
    repo = DownloadBatchRepository(session)
    jobs = DownloadJobRepository(session)
    batch = await _mk_batch(session)
    j1 = await _mk_job(jobs, batch.id, 1)  # type: ignore[attr-defined]
    j2 = await _mk_job(jobs, batch.id, 2)  # type: ignore[attr-defined]
    j3 = await _mk_job(jobs, batch.id, 3)  # type: ignore[attr-defined]
    j4 = await _mk_job(jobs, batch.id, 4)  # type: ignore[attr-defined]
    # j1 completed, j2 failed, j3 running, j4 queued
    await jobs.claim(j1.id, now=_NOW)  # type: ignore[attr-defined]
    await jobs.mark_completed(j1.id, output_path="/x", skip_reason=None, now=_NOW)  # type: ignore[attr-defined]
    await jobs.claim(j2.id, now=_NOW)  # type: ignore[attr-defined]
    await jobs.mark_failed(j2.id, error_step="fetch", error_message="e", now=_NOW)  # type: ignore[attr-defined]
    await jobs.claim(j3.id, now=_NOW)  # type: ignore[attr-defined]
    _ = j4

    counts = await repo.counts(batch.id)  # type: ignore[attr-defined]
    assert counts[DownloadStatus.COMPLETED.value] == 1
    assert counts[DownloadStatus.FAILED.value] == 1
    assert counts[DownloadStatus.RUNNING.value] == 1
    assert counts[DownloadStatus.QUEUED.value] == 1
    assert counts[DownloadStatus.CANCELLED.value] == 0

    assert await repo.pending_count(batch.id) == 2  # type: ignore[attr-defined]


async def test_mark_finalized_returns_true_exactly_once(session: AsyncSession) -> None:
    repo = DownloadBatchRepository(session)
    batch = await _mk_batch(session)
    assert await repo.mark_finalized(batch.id, now=_NOW) is True  # type: ignore[attr-defined]
    assert await repo.mark_finalized(batch.id, now=_NOW) is False  # type: ignore[attr-defined]
    fetched = await repo.get(batch.id)  # type: ignore[attr-defined]
    assert fetched is not None
    assert fetched.finalized_at == _NOW
