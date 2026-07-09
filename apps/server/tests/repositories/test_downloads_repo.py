"""Task 3 — ``DownloadJobRepository`` (claim/list/filter/update/recover).

Offline, in-memory SQLite. The repository never commits (the caller owns the unit
of work); the atomic status transitions (claim/cancel/recover) are the ones the
caller commits immediately — here we just flush and read back in the same session.
"""

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
        kind=BatchKind.SINGLE,
        source="q",
        name=None,
        output_format="mp3",
        bitrate="auto",
        output_template="t",
        overwrite=None,
        generate_m3u=False,
        m3u_template=None,
        generate_save_file=False,
        save_file_path=None,
        update_archive=False,
        embed_lyrics=True,
        generate_lrc=False,
        sponsor_block=False,
        total_jobs=0,
        requested_by=None,
    )
    kwargs.update(over)
    return await repo.create(**kwargs)  # type: ignore[arg-type]


async def _mk_job(
    repo: DownloadJobRepository, *, batch_id: object = None, list_position: int | None = None
) -> object:
    return await repo.create(
        batch_id=batch_id,
        track_id=None,
        match_id=None,
        output_format="mp3",
        bitrate="auto",
        output_template="{title}",
        list_position=list_position,
        requested_by=None,
    )


async def test_create_defaults_queued(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    job = await _mk_job(repo)
    assert job.status is DownloadStatus.QUEUED  # type: ignore[attr-defined]
    assert job.progress == 0.0  # type: ignore[attr-defined]
    assert job.attempts == 0  # type: ignore[attr-defined]
    assert job.started_at is None  # type: ignore[attr-defined]


async def test_get_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    assert await repo.get(uuid4()) is None


async def test_list_pagination_total_independent_of_limit(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    for _ in range(5):
        await _mk_job(repo)
    page, total = await repo.list(limit=2, offset=0)
    assert total == 5
    assert len(page) == 2


async def test_list_newest_first(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    first = await _mk_job(repo)
    second = await _mk_job(repo)
    page, _ = await repo.list()
    assert page[0].id == second.id  # type: ignore[attr-defined]
    assert page[1].id == first.id  # type: ignore[attr-defined]


async def test_list_filter_by_status_and_batch(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    batch_a = await _mk_batch(session)
    batch_b = await _mk_batch(session)
    ja = await _mk_job(repo, batch_id=batch_a.id)  # type: ignore[attr-defined]
    await _mk_job(repo, batch_id=batch_b.id)  # type: ignore[attr-defined]
    # transition ja to running so a status filter distinguishes it.
    await repo.claim(ja.id, now=_NOW)  # type: ignore[attr-defined]

    running, running_total = await repo.list(status=DownloadStatus.RUNNING)
    assert running_total == 1
    assert running[0].id == ja.id  # type: ignore[attr-defined]

    in_b, total_b = await repo.list(batch_id=batch_b.id)  # type: ignore[attr-defined]
    assert total_b == 1
    assert in_b[0].batch_id == batch_b.id  # type: ignore[attr-defined]


async def test_claim_transitions_once(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    job = await _mk_job(repo)
    claimed = await repo.claim(job.id, now=_NOW)  # type: ignore[attr-defined]
    assert claimed is not None
    assert claimed.status is DownloadStatus.RUNNING
    assert claimed.started_at == _NOW
    # second claim finds no queued row.
    again = await repo.claim(job.id, now=_NOW)  # type: ignore[attr-defined]
    assert again is None


async def test_claim_none_when_cancelled_first(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    job = await _mk_job(repo)
    assert await repo.cancel_if_queued(job.id, now=_NOW) is True  # type: ignore[attr-defined]
    assert await repo.claim(job.id, now=_NOW) is None  # type: ignore[attr-defined]


async def test_cancel_if_queued_false_on_running(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    job = await _mk_job(repo)
    await repo.claim(job.id, now=_NOW)  # type: ignore[attr-defined]
    assert await repo.cancel_if_queued(job.id, now=_NOW) is False  # type: ignore[attr-defined]


async def test_recover_orphaned_flips_only_running(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    running_job = await _mk_job(repo)
    queued_job = await _mk_job(repo)
    await repo.claim(running_job.id, now=_NOW)  # type: ignore[attr-defined]

    recovered = await repo.recover_orphaned(now=_NOW)
    assert recovered == [running_job.id]  # type: ignore[attr-defined]

    refetched = await repo.get(running_job.id)  # type: ignore[attr-defined]
    assert refetched is not None
    assert refetched.status is DownloadStatus.QUEUED
    assert refetched.started_at is None
    assert refetched.progress == 0.0
    assert refetched.attempts == 1
    still_queued = await repo.get(queued_job.id)  # type: ignore[attr-defined]
    assert still_queued is not None
    assert still_queued.attempts == 0


async def test_requeue_increments_attempts(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    job = await _mk_job(repo)
    await repo.claim(job.id, now=_NOW)  # type: ignore[attr-defined]
    await repo.requeue(job.id, now=_NOW)  # type: ignore[attr-defined]
    refetched = await repo.get(job.id)  # type: ignore[attr-defined]
    assert refetched is not None
    assert refetched.status is DownloadStatus.QUEUED
    assert refetched.started_at is None
    assert refetched.progress == 0.0
    assert refetched.attempts == 1


async def test_mark_completed_download(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    job = await _mk_job(repo)
    await repo.claim(job.id, now=_NOW)  # type: ignore[attr-defined]
    await repo.mark_completed(job.id, output_path="/m/x.mp3", skip_reason=None, now=_NOW)  # type: ignore[attr-defined]
    refetched = await repo.get(job.id)  # type: ignore[attr-defined]
    assert refetched is not None
    assert refetched.status is DownloadStatus.COMPLETED
    assert refetched.output_path == "/m/x.mp3"
    assert refetched.skip_reason is None
    assert refetched.progress == 1.0
    assert refetched.finished_at == _NOW


async def test_mark_completed_skip_sets_reason(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    job = await _mk_job(repo)
    await repo.claim(job.id, now=_NOW)  # type: ignore[attr-defined]
    await repo.mark_completed(job.id, output_path=None, skip_reason="already_exists", now=_NOW)  # type: ignore[attr-defined]
    refetched = await repo.get(job.id)  # type: ignore[attr-defined]
    assert refetched is not None
    assert refetched.status is DownloadStatus.COMPLETED
    assert refetched.skip_reason == "already_exists"


async def test_mark_failed_truncates_error_message(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    job = await _mk_job(repo)
    await repo.claim(job.id, now=_NOW)  # type: ignore[attr-defined]
    huge = "x" * 20_000
    await repo.mark_failed(job.id, error_step="convert", error_message=huge, now=_NOW)  # type: ignore[attr-defined]
    refetched = await repo.get(job.id)  # type: ignore[attr-defined]
    assert refetched is not None
    assert refetched.status is DownloadStatus.FAILED
    assert refetched.error_step == "convert"
    assert refetched.error_message is not None
    assert len(refetched.error_message) < len(huge)
    assert refetched.finished_at == _NOW


async def test_mark_cancelled(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    job = await _mk_job(repo)
    await repo.claim(job.id, now=_NOW)  # type: ignore[attr-defined]
    await repo.mark_cancelled(job.id, now=_NOW)  # type: ignore[attr-defined]
    refetched = await repo.get(job.id)  # type: ignore[attr-defined]
    assert refetched is not None
    assert refetched.status is DownloadStatus.CANCELLED
    assert refetched.finished_at == _NOW


async def test_update_progress(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    job = await _mk_job(repo)
    await repo.claim(job.id, now=_NOW)  # type: ignore[attr-defined]
    await repo.update_progress(job.id, progress=0.42)  # type: ignore[attr-defined]
    refetched = await repo.get(job.id)  # type: ignore[attr-defined]
    assert refetched is not None
    assert refetched.progress == 0.42


async def test_ids_by_status(session: AsyncSession) -> None:
    repo = DownloadJobRepository(session)
    a = await _mk_job(repo)
    b = await _mk_job(repo)
    await repo.claim(b.id, now=_NOW)  # type: ignore[attr-defined]
    queued = await repo.ids_by_status(DownloadStatus.QUEUED)
    assert queued == [a.id]  # type: ignore[attr-defined]
