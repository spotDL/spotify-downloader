"""Task 6 — ``DownloadWorkerPool`` state machine, cancellation, drain, recovery.

Fully offline: an on-disk ``download_sessionmaker`` (independent connections per
collaborator), the ``FakeDownloadEngine`` seam, a recording broadcaster, and a
spy finalizer. No network / ffmpeg / real engine.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from spotdl_core.download import DownloadOutcome, OverwriteMode, ProgressPhase
from spotdl_core.model import MatchStatus, ProviderId
from spotdl_server.db.enums import BatchKind, DownloadStatus
from spotdl_server.db.models import Artist, DownloadBatch, DownloadJob, Match, Track, track_artists
from spotdl_server.downloads.worker import DownloadWorkerPool
from spotdl_server.settings import DeploymentMode, Settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.conftest import FakeDownloadEngine, SkipReason


# ------------------------------------------------------------ collaborators
class RecordingBroadcaster:
    def __init__(self) -> None:
        self.messages: list[Any] = []

    async def broadcast(self, message: Any) -> None:
        self.messages.append(message)

    def types(self) -> list[str]:
        return [m.type for m in self.messages]


class SpyFinalizer:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    async def finalize(self, batch_id: Any) -> Any:
        self.calls.append(batch_id)
        return SimpleNamespace(m3u_paths=[], save_file_path=None)


# ------------------------------------------------------------ seeding
async def _seed(
    maker: async_sessionmaker[AsyncSession],
    *,
    kind: BatchKind = BatchKind.SINGLE,
    status: DownloadStatus = DownloadStatus.QUEUED,
    with_match: bool = True,
    attempts: int = 0,
    total_jobs: int = 1,
    name: str | None = None,
    overwrite: str | None = None,
) -> tuple[Any, Any]:
    async with maker() as session:
        batch = DownloadBatch(kind=kind, name=name, total_jobs=total_jobs, overwrite=overwrite)
        session.add(batch)
        await session.flush()
        track = Track(name="Song", duration_ms=180_000, track_number=7)
        session.add(track)
        await session.flush()
        artist = Artist(name="A", normalized_name=f"a-{uuid4().hex[:8]}")
        session.add(artist)
        await session.flush()
        await session.execute(
            track_artists.insert().values(track_id=track.id, artist_id=artist.id, position=0)
        )
        match = None
        if with_match:
            match = Match(
                track_id=track.id,
                target_provider=ProviderId.YOUTUBE,
                target_id="yt",
                target_url="https://youtube.com/watch?v=x",
                score=0.9,
                matcher_version="v5",
                status=MatchStatus.AUTO,
            )
            session.add(match)
            await session.flush()
        job = DownloadJob(
            batch_id=batch.id,
            track_id=track.id,
            match_id=match.id if match is not None else None,
            status=status,
            list_position=1,
            attempts=attempts,
            output_format="mp3",
            bitrate="auto",
            output_template="{artists} - {title}.{output-ext}",
        )
        session.add(job)
        await session.flush()
        await session.commit()
        return batch.id, job.id


async def _add_job(maker: async_sessionmaker[AsyncSession], batch_id: Any, *, position: int) -> Any:
    async with maker() as session:
        track = Track(name=f"Song{position}", duration_ms=180_000)
        session.add(track)
        await session.flush()
        artist = Artist(name=f"A{position}", normalized_name=f"a{position}-{uuid4().hex[:8]}")
        session.add(artist)
        await session.flush()
        await session.execute(
            track_artists.insert().values(track_id=track.id, artist_id=artist.id, position=0)
        )
        match = Match(
            track_id=track.id,
            target_provider=ProviderId.YOUTUBE,
            target_id=f"yt{position}",
            target_url=f"https://youtube.com/watch?v={position}",
            score=0.9,
            matcher_version="v5",
            status=MatchStatus.AUTO,
        )
        session.add(match)
        await session.flush()
        job = DownloadJob(
            batch_id=batch_id,
            track_id=track.id,
            match_id=match.id,
            status=DownloadStatus.QUEUED,
            list_position=position,
            output_format="mp3",
            bitrate="auto",
            output_template="{artists} - {title}.{output-ext}",
        )
        session.add(job)
        await session.flush()
        await session.commit()
        return job.id


async def _get_job(maker: async_sessionmaker[AsyncSession], job_id: Any) -> DownloadJob:
    async with maker() as session:
        job = await session.get(DownloadJob, job_id)
        assert job is not None
        return job


async def _wait_status(
    maker: async_sessionmaker[AsyncSession],
    job_id: Any,
    statuses: set[DownloadStatus],
    *,
    timeout: float = 3.0,
) -> DownloadJob:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        job = await _get_job(maker, job_id)
        if job.status in statuses:
            return job
        await asyncio.sleep(0.01)
    raise AssertionError(f"job {job_id} never reached {statuses}")


async def _assert_no_running(maker: async_sessionmaker[AsyncSession], job_ids: list[Any]) -> None:
    for job_id in job_ids:
        job = await _get_job(maker, job_id)
        assert job.status is not DownloadStatus.RUNNING, f"job {job_id} left running"


async def _wait_until(predicate: Any, *, timeout: float = 3.0) -> None:
    """Poll ``predicate()`` (a 0-arg bool callable) until true or the timeout."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition never became true")


# ------------------------------------------------------------ pool fixture
@pytest.fixture
def make_pool(download_settings: Settings, clock: Any) -> Any:
    pools: list[DownloadWorkerPool] = []

    def _factory(
        maker: async_sessionmaker[AsyncSession],
        engine: Any,
        *,
        hub: Any | None = None,
        finalizer: Any | None = None,
        settings: Settings | None = None,
    ) -> tuple[DownloadWorkerPool, RecordingBroadcaster, SpyFinalizer]:
        broadcaster = hub or RecordingBroadcaster()
        spy = finalizer or SpyFinalizer()
        pool = DownloadWorkerPool(
            sessionmaker=maker,
            engine=engine,
            hub=broadcaster,
            settings=settings or download_settings,
            finalizer=spy,
            clock=clock,
        )
        pools.append(pool)
        return pool, broadcaster, spy

    _factory.pools = pools  # type: ignore[attr-defined]
    return _factory


@pytest.fixture(autouse=True)
async def _shutdown_pools(make_pool: Any) -> Any:
    yield
    for pool in getattr(make_pool, "pools", []):
        await pool.shutdown(drain_timeout_s=0.0)


# ------------------------------------------------------------ happy path
async def test_happy_path_downloaded(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    batch_id, job_id = await _seed(download_sessionmaker)
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, hub, _ = make_pool(download_sessionmaker, engine)

    await pool.start()
    job = await _wait_status(download_sessionmaker, job_id, {DownloadStatus.COMPLETED})

    assert job.output_path is not None
    from pathlib import Path

    assert Path(job.output_path).is_file()
    assert job.progress == 1.0
    assert job.skip_reason is None
    types = hub.types()
    assert "job_started" in types
    assert "progress" in types
    assert "job_finished" in types
    await _assert_no_running(download_sessionmaker, [job_id])


async def test_skip_maps_to_completed_with_reason(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    batch_id, job_id = await _seed(download_sessionmaker)

    async def script(engine: FakeDownloadEngine, request: Any, on_progress: Any) -> DownloadOutcome:
        engine.emit(on_progress, ProgressPhase.SKIPPED, 100)
        return DownloadOutcome.skipped(request.track, SkipReason.ALREADY_EXISTS)

    engine = FakeDownloadEngine(config=download_settings.download_config(), script=script)
    pool, hub, _ = make_pool(download_sessionmaker, engine)

    await pool.start()
    job = await _wait_status(download_sessionmaker, job_id, {DownloadStatus.COMPLETED})

    assert job.skip_reason == "already_exists"
    finished = [m for m in hub.messages if m.type == "job_finished"]
    assert finished and finished[-1].skipped is True


async def test_failure_isolation_other_jobs_still_run(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    # concurrency=1 makes ordering deterministic: job_fail (seeded first ->
    # enqueued first) runs and fails; job_ok must still run afterwards.
    settings = download_settings.model_copy(update={"download_concurrency": 1})
    batch_a, job_fail = await _seed(download_sessionmaker)
    batch_b, job_ok = await _seed(download_sessionmaker)

    async def script(engine: FakeDownloadEngine, request: Any, on_progress: Any) -> DownloadOutcome:
        # fail the first job the engine sees; every later job downloads normally
        if len(engine.requests) == 1:
            return DownloadOutcome.failed(request.track, step="convert", error="boom")
        engine.write_output(request)
        return DownloadOutcome.downloaded(request.track, engine.planned_path(request))

    engine = FakeDownloadEngine(config=settings.download_config(), script=script)
    pool, hub, _ = make_pool(download_sessionmaker, engine, settings=settings)

    await pool.start()
    failed = await _wait_status(download_sessionmaker, job_fail, {DownloadStatus.FAILED})
    ok = await _wait_status(download_sessionmaker, job_ok, {DownloadStatus.COMPLETED})

    assert failed.error_step == "convert"
    assert ok.status is DownloadStatus.COMPLETED
    assert "job_failed" in hub.types()


async def test_embed_failure_retries_with_metadata_overwrite(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    batch_id, job_id = await _seed(download_sessionmaker)

    async def script(engine: FakeDownloadEngine, request: Any, on_progress: Any) -> DownloadOutcome:
        if len(engine.requests) == 1:  # first attempt: embed fails
            return DownloadOutcome.failed(request.track, step="embed", error="tag error")
        engine.write_output(request)
        return DownloadOutcome.downloaded(request.track, engine.planned_path(request))

    engine = FakeDownloadEngine(config=download_settings.download_config(), script=script)
    pool, _, _ = make_pool(download_sessionmaker, engine)

    await pool.start()
    job = await _wait_status(download_sessionmaker, job_id, {DownloadStatus.COMPLETED})

    assert job.status is DownloadStatus.COMPLETED
    assert len(engine.requests) == 2
    assert engine.requests[0].overwrite is OverwriteMode.SKIP
    assert engine.requests[1].overwrite is OverwriteMode.METADATA


# ------------------------------------------------------------ cancellation
async def test_cancel_running_job(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    batch_id, job_id = await _seed(download_sessionmaker)
    gate = asyncio.Event()

    async def script(engine: FakeDownloadEngine, request: Any, on_progress: Any) -> DownloadOutcome:
        engine.emit(on_progress, ProgressPhase.FETCH, 10)
        path = engine.write_output(request)  # partial file present
        await gate.wait()
        return DownloadOutcome.downloaded(request.track, path)

    engine = FakeDownloadEngine(config=download_settings.download_config(), script=script)
    pool, hub, _ = make_pool(download_sessionmaker, engine)

    await pool.start()
    running = await _wait_status(download_sessionmaker, job_id, {DownloadStatus.RUNNING})
    partial = running.output_path  # not set yet; grab planned path from engine instead
    # The DB flips to RUNNING before the worker calls engine.download(); wait for
    # the call (and its partial file) to land rather than racing it (CI flake).
    await _wait_until(lambda: bool(engine.requests))
    planned = engine.planned_path(engine.requests[0])
    await _wait_until(planned.is_file)
    assert planned.is_file()

    assert await pool.request_cancel(job_id) is True
    job = await _wait_status(download_sessionmaker, job_id, {DownloadStatus.CANCELLED})

    assert job.status is DownloadStatus.CANCELLED
    assert not planned.exists()  # partial removed
    assert "job_cancelled" in hub.types()
    assert partial is None


async def test_cancel_during_active_progress_flush_reaches_terminal(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    # The engine streams progress continuously so the pump is actively flushing
    # (write+commit) when the cancel lands. The flush must finish before the pump's
    # session closes (else a concurrent-session-use race strands the job ``running``);
    # this pins that the job still reaches CANCELLED cleanly, no stuck state.
    settings = download_settings.model_copy(update={"progress_throttle_ms": 1})
    batch_id, job_id = await _seed(download_sessionmaker)

    async def script(engine: FakeDownloadEngine, request: Any, on_progress: Any) -> DownloadOutcome:
        percent = 0
        while True:
            percent = (percent + 5) % 100
            engine.emit(on_progress, ProgressPhase.FETCH, percent)
            await asyncio.sleep(0.001)

    engine = FakeDownloadEngine(config=settings.download_config(), script=script)
    pool, hub, _ = make_pool(download_sessionmaker, engine, settings=settings)

    await pool.start()
    await _wait_status(download_sessionmaker, job_id, {DownloadStatus.RUNNING})
    # Let a few throttled flushes land while progress is streaming.
    await _wait_until(lambda: any(m.type == "progress" for m in hub.messages))

    assert await pool.request_cancel(job_id) is True
    job = await _wait_status(download_sessionmaker, job_id, {DownloadStatus.CANCELLED})

    assert job.status is DownloadStatus.CANCELLED
    await _assert_no_running(download_sessionmaker, [job_id])


async def test_uninterruptible_drives_write_commit_through_cancel(
    download_sessionmaker: Any,
) -> None:
    # Pins the invariant behind the mid-claim-cancel fix. ``_run_job`` claims the job
    # (``UPDATE ... status='running'`` + commit) through ``_uninterruptible``; a user
    # DELETE / shutdown drain can cancel the task mid-claim. If the cancel is allowed
    # to interrupt the in-flight write+commit, aiosqlite's worker thread finishes the
    # statement after SQLAlchemy has invalidated the connection, orphaning the open
    # transaction — SQLite's write lock is never released and every later writer fails
    # "database is locked". ``_uninterruptible`` must instead drain the write+commit to
    # completion before the cancel propagates, leaving the row persisted and the DB
    # writable. (A naive ``await coro`` leaves the row un-written; a bare
    # ``asyncio.shield`` lets the commit race the awaiter's unwind.)
    _batch_id, job_id = await _seed(download_sessionmaker)
    started = asyncio.Event()
    release = asyncio.Event()

    async def write_running() -> None:
        started.set()
        await release.wait()  # park so the cancel lands while this is shielded, pre-write
        async with download_sessionmaker() as session:
            job = await session.get(DownloadJob, job_id)
            job.status = DownloadStatus.RUNNING
            await session.commit()

    async def runner() -> None:
        await DownloadWorkerPool._uninterruptible(write_running())

    task = asyncio.create_task(runner())
    await started.wait()
    task.cancel()  # cancel before the wrapped write has run
    await asyncio.sleep(0)  # let the cancel reach the shield
    release.set()  # now let the shielded write+commit proceed
    with pytest.raises(asyncio.CancelledError):
        await task

    # The shielded write ran to completion despite the cancel...
    job = await _get_job(download_sessionmaker, job_id)
    assert job.status is DownloadStatus.RUNNING
    # ...and left no orphaned transaction: a fresh writer commits without blocking.
    async with download_sessionmaker() as session:
        job = await session.get(DownloadJob, job_id)
        job.progress = 0.5
        await session.commit()


async def test_cancel_queued_job_never_calls_engine(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    batch_id, job_id = await _seed(download_sessionmaker)
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, hub, _ = make_pool(download_sessionmaker, engine)

    # No start(): the job is never claimed, so cancel takes the queued path.
    assert await pool.request_cancel(job_id) is True
    job = await _get_job(download_sessionmaker, job_id)

    assert job.status is DownloadStatus.CANCELLED
    assert engine.requests == []
    assert "job_cancelled" in hub.types()


async def test_cancel_unknown_or_terminal_returns_false(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, _, _ = make_pool(download_sessionmaker, engine)
    assert await pool.request_cancel(uuid4()) is False


# ------------------------------------------------------------ crash recovery
async def test_crash_recovery_requeues_and_completes(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    # A row left ``running`` by a crashed prior process.
    batch_id, job_id = await _seed(download_sessionmaker, status=DownloadStatus.RUNNING)
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, _, _ = make_pool(download_sessionmaker, engine)

    await pool.start()
    job = await _wait_status(download_sessionmaker, job_id, {DownloadStatus.COMPLETED})

    assert job.status is DownloadStatus.COMPLETED
    assert job.attempts == 1  # bumped by recover_orphaned
    await _assert_no_running(download_sessionmaker, [job_id])


async def test_recovered_job_forces_overwrite_not_file_skip(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    # Recovered (running -> queued, attempts=1) job whose planned file exists.
    batch_id, job_id = await _seed(download_sessionmaker, status=DownloadStatus.RUNNING)
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, _, _ = make_pool(download_sessionmaker, engine)

    # Pre-create the suspect output file the recovered job would target.
    lib = download_settings.effective_library_path()
    lib.mkdir(parents=True, exist_ok=True)
    (lib / "A - Song.mp3").write_bytes(b"suspect-untagged")

    await pool.start()
    job = await _wait_status(download_sessionmaker, job_id, {DownloadStatus.COMPLETED})

    assert engine.requests[-1].overwrite is OverwriteMode.FORCE
    assert job.skip_reason is None  # re-processed, not a skip


async def test_fresh_job_keeps_skip_overwrite(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    batch_id, job_id = await _seed(download_sessionmaker)  # attempts=0
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, _, _ = make_pool(download_sessionmaker, engine)

    await pool.start()
    await _wait_status(download_sessionmaker, job_id, {DownloadStatus.COMPLETED})

    assert engine.requests[0].overwrite is OverwriteMode.SKIP


async def test_first_attempt_honours_batch_overwrite(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    # A batch submitted with overwrite=force: the fresh (attempts==0) job's
    # request must carry FORCE, not the default SKIP (CONTRACT 1 / CONTRACT 4).
    batch_id, job_id = await _seed(download_sessionmaker, overwrite="force")
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, _, _ = make_pool(download_sessionmaker, engine)

    await pool.start()
    await _wait_status(download_sessionmaker, job_id, {DownloadStatus.COMPLETED})

    assert engine.requests[0].overwrite is OverwriteMode.FORCE


async def test_first_attempt_honours_batch_overwrite_metadata(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    batch_id, job_id = await _seed(download_sessionmaker, overwrite="metadata")
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, _, _ = make_pool(download_sessionmaker, engine)

    await pool.start()
    await _wait_status(download_sessionmaker, job_id, {DownloadStatus.COMPLETED})

    assert engine.requests[0].overwrite is OverwriteMode.METADATA


# ------------------------------------------------------------ no viable match
async def test_no_match_fails_fast_without_engine(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    batch_id, job_id = await _seed(download_sessionmaker, with_match=False)
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, hub, _ = make_pool(download_sessionmaker, engine)

    await pool.start()
    job = await _wait_status(download_sessionmaker, job_id, {DownloadStatus.FAILED})

    assert job.error_step == "fetch"
    assert engine.requests == []
    assert "job_failed" in hub.types()


# ------------------------------------------------------------ temp sweep
async def test_temp_sweep_removes_stray_files(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    temp = download_settings.effective_temp_dir()
    temp.mkdir(parents=True, exist_ok=True)
    stray = temp / "orphan.part"
    stray.write_bytes(b"partial")
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, _, _ = make_pool(download_sessionmaker, engine)

    await pool.start()

    assert not stray.exists()


async def test_temp_sweep_never_raises_on_unlink_error(
    download_sessionmaker: Any,
    download_settings: Settings,
    make_pool: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temp = download_settings.effective_temp_dir()
    temp.mkdir(parents=True, exist_ok=True)
    (temp / "orphan.part").write_bytes(b"partial")

    from pathlib import Path

    def _boom(self: Path, *a: Any, **k: Any) -> None:
        raise OSError("read-only")

    monkeypatch.setattr(Path, "unlink", _boom)
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, _, _ = make_pool(download_sessionmaker, engine)

    await pool.start()  # must not raise


# ------------------------------------------------------------ drain
async def test_graceful_drain_requeues_slow_job(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    batch_id, job_id = await _seed(download_sessionmaker)

    async def slow(engine: FakeDownloadEngine, request: Any, on_progress: Any) -> DownloadOutcome:
        await asyncio.sleep(5.0)
        return DownloadOutcome.downloaded(request.track, engine.write_output(request))

    engine = FakeDownloadEngine(config=download_settings.download_config(), script=slow)
    pool, _, _ = make_pool(download_sessionmaker, engine)

    await pool.start()
    await _wait_status(download_sessionmaker, job_id, {DownloadStatus.RUNNING})
    await pool.shutdown(drain_timeout_s=0.01)

    job = await _get_job(download_sessionmaker, job_id)
    assert job.status is DownloadStatus.QUEUED
    assert job.started_at is None
    assert job.attempts == 1


async def test_graceful_drain_does_not_leak_queued_job(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    # concurrency=1: job1 runs (a straggler cancelled at the drain timeout) while
    # job2 waits in the queue. The worker must NOT pull+claim job2 during the
    # drain (it would run detached past shutdown, stranded ``running`` while the
    # engine is torn down). Both jobs must be non-running after shutdown, and the
    # engine must only ever have seen job1's request.
    settings = download_settings.model_copy(update={"download_concurrency": 1})
    batch_id, job1 = await _seed(download_sessionmaker, total_jobs=2, name="Mix")
    job2 = await _add_job(download_sessionmaker, batch_id, position=2)

    async def slow(engine: FakeDownloadEngine, request: Any, on_progress: Any) -> DownloadOutcome:
        await asyncio.sleep(5.0)
        return DownloadOutcome.downloaded(request.track, engine.write_output(request))

    engine = FakeDownloadEngine(config=settings.download_config(), script=slow)
    pool, _, _ = make_pool(download_sessionmaker, engine, settings=settings)

    await pool.start()
    await _wait_status(download_sessionmaker, job1, {DownloadStatus.RUNNING})
    await pool.shutdown(drain_timeout_s=0.01)

    j1 = await _get_job(download_sessionmaker, job1)
    j2 = await _get_job(download_sessionmaker, job2)
    assert j1.status is DownloadStatus.QUEUED  # straggler re-queued
    assert j2.status is DownloadStatus.QUEUED  # never claimed
    await _assert_no_running(download_sessionmaker, [job1, job2])
    assert len(engine.requests) == 1  # job2 never reached the engine


async def test_fast_job_completes_within_drain_window(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    batch_id, job_id = await _seed(download_sessionmaker)
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, _, _ = make_pool(download_sessionmaker, engine)

    await pool.start()
    await _wait_status(download_sessionmaker, job_id, {DownloadStatus.COMPLETED})
    await pool.shutdown(drain_timeout_s=1.0)

    job = await _get_job(download_sessionmaker, job_id)
    assert job.status is DownloadStatus.COMPLETED


# ------------------------------------------------------------ no double-run
async def test_no_double_run_of_one_id(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    settings = download_settings.model_copy(update={"download_concurrency": 2})
    batch_id, job_id = await _seed(download_sessionmaker)
    gate = asyncio.Event()

    async def script(engine: FakeDownloadEngine, request: Any, on_progress: Any) -> DownloadOutcome:
        await gate.wait()
        return DownloadOutcome.downloaded(request.track, engine.write_output(request))

    engine = FakeDownloadEngine(config=settings.download_config(), script=script)
    pool, _, _ = make_pool(download_sessionmaker, engine, settings=settings)

    await pool.start()
    # Defensive double-enqueue of the same id (start() already enqueued it once).
    await pool.enqueue([job_id])
    await _wait_status(download_sessionmaker, job_id, {DownloadStatus.RUNNING})
    gate.set()
    await _wait_status(download_sessionmaker, job_id, {DownloadStatus.COMPLETED})

    assert len(engine.requests) == 1  # claimed + run exactly once


# ------------------------------------------------------------ finalize
async def test_batch_finalized_exactly_once(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    batch_id, job1 = await _seed(download_sessionmaker, total_jobs=2, name="Mix")
    job2 = await _add_job(download_sessionmaker, batch_id, position=2)
    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, hub, spy = make_pool(download_sessionmaker, engine)

    await pool.start()
    await _wait_status(download_sessionmaker, job1, {DownloadStatus.COMPLETED})
    await _wait_status(download_sessionmaker, job2, {DownloadStatus.COMPLETED})
    # The finalize runs in the last job's finally (guaranteed once by the lock).
    # Wait for the ``batch_finished`` broadcast itself, not merely the finalizer
    # call: the finalizer records ``spy.calls`` and only *then* reads WS counts and
    # broadcasts, so waiting on ``spy.calls`` races the broadcast under slow
    # scheduling (the assertions below are on ``hub.messages``).
    await _wait_until(lambda: any(m.type == "batch_finished" for m in hub.messages))

    assert spy.calls == [batch_id]
    finished = [m for m in hub.messages if m.type == "batch_finished"]
    assert len(finished) == 1
    assert finished[0].completed == 2


async def test_start_finalizes_presettled_batch(
    download_sessionmaker: Any, download_settings: Settings, make_pool: Any
) -> None:
    # A batch whose only job already completed but was never finalized (crash
    # between the terminal write and finalize).
    async with download_sessionmaker() as session:
        batch = DownloadBatch(kind=BatchKind.SINGLE, total_jobs=1)
        session.add(batch)
        await session.flush()
        job = DownloadJob(
            batch_id=batch.id,
            status=DownloadStatus.COMPLETED,
            list_position=1,
            output_format="mp3",
        )
        session.add(job)
        await session.flush()
        await session.commit()
        batch_id = batch.id

    engine = FakeDownloadEngine(config=download_settings.download_config())
    pool, _, spy = make_pool(download_sessionmaker, engine)
    await pool.start()
    await _wait_until(lambda: bool(spy.calls))

    assert spy.calls == [batch_id]


# ------------------------------------------------------------ settings knobs
async def test_request_carries_settings_sourced_fields(
    download_sessionmaker: Any, tmp_path: Any, make_pool: Any
) -> None:
    from spotdl_core.download import RestrictMode

    settings = Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=tmp_path,
        library_path=tmp_path / "music",
        download_temp_dir=tmp_path / "temp",
        download_restrict=RestrictMode.ASCII,
        download_max_filename_length=50,
        download_id3_separator="; ",
        download_detect_formats=("m4a",),
        download_skip_explicit=True,
        download_respect_skip_file=True,
        download_create_skip_file=True,
        download_retain_track_cover=True,
        download_scan_existing=True,
        download_playlist_numbering=True,
    )
    # A pre-existing library audio file so the scan populates known_paths.
    lib = settings.effective_library_path()
    lib.mkdir(parents=True, exist_ok=True)
    existing = lib / "existing.mp3"
    existing.write_bytes(b"x")

    batch_id, job_id = await _seed(
        download_sessionmaker, kind=BatchKind.PLAYLIST, name="Roadtrip", total_jobs=1
    )
    engine = FakeDownloadEngine(config=settings.download_config())
    pool, _, _ = make_pool(download_sessionmaker, engine, settings=settings)

    await pool.start()
    await _wait_status(download_sessionmaker, job_id, {DownloadStatus.COMPLETED})

    request = engine.requests[0]
    from spotdl_core.download import OutputFormat

    assert request.restrict is RestrictMode.ASCII
    assert request.max_filename_length == 50
    assert request.id3_separator == "; "
    assert request.detect_formats == (OutputFormat.M4A,)
    assert request.skip_explicit is True
    assert request.respect_skip_file is True
    assert request.create_skip_file is True
    assert request.retain_track_cover is True
    assert existing in request.known_paths
    # playlist_numbering parity: track_number follows list_position, album titled
    assert request.track.track_number == 1
    assert request.track.album is not None
    assert request.track.album.name == "Roadtrip"
