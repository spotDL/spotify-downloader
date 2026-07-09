"""``QueueViewModel`` — the pure ``reduce`` + the WS ``stream`` + ``cancel``."""

from __future__ import annotations

from uuid import uuid4

from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.queue import QueueViewModel
from spotdl_cli.viewmodels.types import JobRow, QueueSnapshot

from .fakes import (
    FakeSpotdlClient,
    make_download_page,
    make_job,
    make_session,
    ws_batch_finished,
    ws_cancelled,
    ws_failed,
    ws_finished,
    ws_hello,
    ws_progress,
    ws_queued,
    ws_started,
)

_EMPTY = QueueSnapshot(
    jobs=(), overall_percent=0, active=0, completed=0, failed=0, skipped=0, cancelled=0
)


def _vm() -> QueueViewModel:
    return QueueViewModel(FakeSpotdlClient(), make_session())


def _fold(vm: QueueViewModel, *frames: object) -> QueueSnapshot:
    snap = _EMPTY
    for frame in frames:
        snap = vm.reduce(snap, frame)  # type: ignore[arg-type]
    return snap


def test_happy_path_queued_to_finished() -> None:
    vm = _vm()
    job, batch = uuid4(), uuid4()
    snap = _fold(
        vm,
        ws_queued(job, batch, track_name="Song"),
        ws_started(job, batch),
        ws_progress(job, batch, percent=40),
        ws_finished(job, batch, output_path="/music/song.mp3"),
    )
    (row,) = snap.jobs
    assert row.status == "completed"
    assert row.percent == 100
    assert row.output_path == "/music/song.mp3"
    assert snap.completed == 1
    assert snap.active == 0


def test_failed_frame_counts_as_failed() -> None:
    vm = _vm()
    job, batch = uuid4(), uuid4()
    snap = _fold(
        vm, ws_queued(job, batch), ws_started(job, batch), ws_failed(job, batch, error="net")
    )
    (row,) = snap.jobs
    assert row.status == "failed"
    assert row.error == "net"
    assert snap.failed == 1


def test_cancelled_frame() -> None:
    vm = _vm()
    job, batch = uuid4(), uuid4()
    snap = _fold(vm, ws_queued(job, batch), ws_cancelled(job, batch))
    (row,) = snap.jobs
    assert row.status == "cancelled"
    assert snap.cancelled == 1


def test_skipped_finished() -> None:
    vm = _vm()
    job, batch = uuid4(), uuid4()
    snap = _fold(
        vm,
        ws_queued(job, batch),
        ws_finished(job, batch, skipped=True, skip_reason="already_exists"),
    )
    (row,) = snap.jobs
    assert row.status == "skipped"
    assert row.skip_reason == "already_exists"
    assert snap.skipped == 1


def test_batch_finished_aggregates() -> None:
    vm = _vm()
    batch = uuid4()
    snap = vm.reduce(
        _EMPTY, ws_batch_finished(batch, completed=3, failed=1, skipped=2, cancelled=1)
    )
    assert (snap.completed, snap.failed, snap.skipped, snap.cancelled) == (3, 1, 2, 1)
    assert snap.overall_percent == 100
    assert snap.active == 0


def test_duplicate_frames_are_idempotent() -> None:
    vm = _vm()
    job, batch = uuid4(), uuid4()
    once = _fold(
        vm, ws_queued(job, batch), ws_started(job, batch), ws_progress(job, batch, percent=40)
    )
    twice = _fold(
        vm,
        ws_queued(job, batch),
        ws_queued(job, batch),
        ws_started(job, batch),
        ws_progress(job, batch, percent=40),
        ws_progress(job, batch, percent=40),
    )
    assert once == twice


def test_out_of_order_progress_after_finished_ignored() -> None:
    vm = _vm()
    job, batch = uuid4(), uuid4()
    snap = _fold(
        vm,
        ws_queued(job, batch),
        ws_finished(job, batch, output_path="/x.mp3"),
        ws_progress(job, batch, percent=10),  # late frame, must not regress
    )
    (row,) = snap.jobs
    assert row.status == "completed"
    assert row.percent == 100


def test_unknown_job_progress_ignored() -> None:
    vm = _vm()
    snap = vm.reduce(_EMPTY, ws_progress(uuid4(), uuid4(), percent=50))
    assert snap.jobs == ()
    assert snap == _EMPTY


def test_hello_frame_is_ignored_by_reduce() -> None:
    vm = _vm()
    assert vm.reduce(_EMPTY, ws_hello()) == _EMPTY


async def test_load_seeds_from_list_downloads() -> None:
    client = FakeSpotdlClient()
    job_id, batch_id = uuid4(), uuid4()
    client.download_page = make_download_page(
        jobs=[make_job(id=job_id, status="queued", batch_id=batch_id)]
    )
    result = await QueueViewModel(client, make_session()).load()
    assert result.state is LoadState.READY
    assert result.data is not None
    (row,) = result.data.jobs
    assert isinstance(row, JobRow)
    assert row.job_id == job_id


async def test_stream_yields_snapshots_then_ends() -> None:
    client = FakeSpotdlClient()
    vm = QueueViewModel(client, make_session())
    job, batch = uuid4(), uuid4()
    client.push_ws(ws_hello())
    client.push_ws(ws_queued(job, batch))
    client.push_ws(ws_progress(job, batch, percent=60))
    client.close_ws()

    snapshots = [update async for update in vm.stream()]
    assert all(u.state is LoadState.READY for u in snapshots)
    assert snapshots[-1].data is not None
    (row,) = snapshots[-1].data.jobs
    assert row.percent == 60


async def test_stream_protocol_mismatch_yields_one_failure() -> None:
    client = FakeSpotdlClient()
    vm = QueueViewModel(client, make_session())
    client.push_ws(ws_hello(protocol_version=99))
    client.push_ws(ws_queued(uuid4(), uuid4()))  # should never be processed
    client.close_ws()

    updates = [u async for u in vm.stream()]
    assert len(updates) == 1
    assert updates[0].state is LoadState.ERROR
    assert updates[0].error is not None


async def test_cancel_calls_client() -> None:
    client = FakeSpotdlClient()
    job_id, batch_id = uuid4(), uuid4()
    client.jobs[str(job_id)] = make_job(id=job_id, status="cancelled", batch_id=batch_id)
    result = await QueueViewModel(client, make_session()).cancel(job_id)
    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.status == "cancelled"
    assert client.calls[-1] == ("cancel_download", (job_id,), {})
