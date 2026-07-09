"""Pilot tests for the live ``QueueScreen`` + ``QueueTable`` (Plan 9 Task 8).

Everything runs headless through ``App.run_test()`` over :class:`FakeSpotdlClient`'s
controllable WS source (``push_ws``/``close_ws``). The screen's contract (CONTRACT E):
one worker owns the WS path; frames fold into the reactive snapshot; the table and
counts line update; a failed job is counted (batch not aborted); ``x`` cancels the
focused job; a protocol-version mismatch toasts and stops the worker; and unmounting
cancels the worker. A separate pair of tests pins the WsHello seam against **both**
the fake (yields the hello frame) and a real-shaped stub (raises ``UnsupportedProtocol``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest
from spotdl_cli.client import UnsupportedProtocol
from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.tui.screens.queue import QueueScreen
from spotdl_cli.tui.widgets.queue_table import QueueTable
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.factory import ViewModelFactory
from spotdl_cli.viewmodels.queue import WS_PROTOCOL_VERSION, QueueViewModel
from spotdl_cli.views import WsMessage
from textual.widgets import Input, Static
from textual.worker import WorkerState

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import (
    FakeSpotdlClient,
    make_batch,
    make_config,
    make_download_page,
    make_features,
    make_job,
    make_session,
    ws_failed,
    ws_finished,
    ws_hello,
    ws_progress,
    ws_queued,
    ws_started,
)

_ORIGIN = "https://api.example.test"
_TRANSPORT = "remote · api.example.test"


def _factory(client: FakeSpotdlClient) -> ViewModelFactory:
    return ViewModelFactory(
        client,
        FakeCredentialStore(),
        FakeConfigStore(),
        server_origin=_ORIGIN,
        transport_label=_TRANSPORT,
    )


def _client() -> FakeSpotdlClient:
    client = FakeSpotdlClient()
    client.download_page = make_download_page(jobs=[])  # empty seed
    return client


async def _open_queue(app: SpotdlApp, pilot: object) -> QueueScreen:
    await pilot.press("2")  # can_download is True by default → queue section available
    await pilot.pause()  # type: ignore[attr-defined]
    screen = app.screen
    assert isinstance(screen, QueueScreen)
    return screen


def _summary(screen: QueueScreen) -> str:
    return str(screen.query_one("#queue-summary", Static).render())


def _status_cell(screen: QueueScreen, job_id: UUID) -> str:
    row = screen.query_one(QueueTable).get_row(str(job_id))
    return str(row[0])  # (Status, Title, Progress, Step)


def _step_cell(screen: QueueScreen, job_id: UUID) -> str:
    row = screen.query_one(QueueTable).get_row(str(job_id))
    return str(row[3])  # the Step/detail cell (phase, or failure/skip reason)


async def test_frames_update_rows_and_counts() -> None:
    client = _client()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = await _open_queue(app, pilot)
        job, batch = uuid4(), uuid4()
        client.push_ws(ws_queued(job, batch, track_name="One More Time"))
        client.push_ws(ws_started(job, batch))
        client.push_ws(ws_progress(job, batch, phase="convert", percent=60))
        await pilot.pause()
        table = screen.query_one(QueueTable)
        assert table.job_row_count == 1  # one job row (plus its batch header row)
        assert "convert" in _step_cell(screen, job)  # phase in the step cell
        assert "60%" in str(table.get_row(str(job))[2])  # progress cell
        client.push_ws(ws_finished(job, batch))
        await pilot.pause()
        assert "completed 1" in _summary(screen)
        assert "completed" in _status_cell(screen, job)


async def test_failed_job_is_counted_and_shows_error() -> None:
    client = _client()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = await _open_queue(app, pilot)
        first, second, batch = uuid4(), uuid4(), uuid4()
        client.push_ws(ws_queued(first, batch, track_name="Doomed"))
        client.push_ws(ws_started(first, batch))
        client.push_ws(ws_failed(first, batch, error="404 not found"))
        # A second job still flows — the batch is not aborted by one failure.
        client.push_ws(ws_queued(second, batch, track_name="Fine"))
        await pilot.pause()
        assert "failed 1" in _summary(screen)
        assert "404 not found" in _step_cell(screen, first)
        assert screen.query_one(QueueTable).job_row_count == 2


async def test_x_cancels_focused_job() -> None:
    client = _client()
    job, batch = uuid4(), uuid4()
    client.jobs[str(job)] = make_job(id=job, status="cancelled", batch_id=batch)
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = await _open_queue(app, pilot)
        client.push_ws(ws_queued(job, batch, track_name="Interstella"))
        client.push_ws(ws_started(job, batch))
        await pilot.pause()
        await pilot.press("x")
        await pilot.pause()
        assert client.called("cancel_download")
        assert "cancelled" in _status_cell(screen, job)
        assert "cancelled 1" in _summary(screen)


async def test_hello_version_mismatch_toasts_and_stops_worker() -> None:
    client = _client()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = await _open_queue(app, pilot)
        client.push_ws(ws_hello(protocol_version=WS_PROTOCOL_VERSION + 1))
        await pilot.pause()
        assert any("newer download-progress protocol" in n.message for n in app._notifications)
        assert screen._worker.state in {WorkerState.SUCCESS, WorkerState.CANCELLED}


async def test_unmount_cancels_worker() -> None:
    client = _client()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(QueueScreen())
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, QueueScreen)
        worker = screen._worker
        app.pop_screen()
        await pilot.pause()
        assert worker.state is WorkerState.CANCELLED


async def test_enqueue_input_submits_query() -> None:
    client = _client()
    client.submit_download_result = make_batch(jobs=[make_job(), make_job()])
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = await _open_queue(app, pilot)
        input_widget = screen.query_one(Input)
        input_widget.focus()
        input_widget.value = "https://open.spotify.com/track/x"
        await pilot.press("enter")
        await pilot.pause()
        assert client.called("submit_download")
        assert "queued 2" in [n.message for n in app._notifications]


# --- redesign §3: mode-aware queue semantics ---------------------------------


def _mode_client(mode: str) -> FakeSpotdlClient:
    config = make_config(mode=mode, features=make_features(downloads=True))
    client = FakeSpotdlClient(config=config, download_config=config)
    client.download_page = make_download_page(jobs=[])
    return client


async def test_local_mode_labels_downloads_and_hides_fetch() -> None:
    client = _mode_client("hosted")  # community: downloads run on the local engine
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = await _open_queue(app, pilot)
        assert screen.query_one("#queue-summary", Static).border_title == "Downloads (local)"
        assert screen.check_action("fetch_save_file", ()) is None


async def test_selfhost_flips_to_server_queue_and_fetches_save_file() -> None:
    """Flow 3: self-hosted flags flip the queue semantics + WS frames render (§5.3)."""
    client = _mode_client("selfhost")
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = await _open_queue(app, pilot)
        # /config mode flips the panel label + reveals the fetch-save-file action.
        assert screen.query_one("#queue-summary", Static).border_title == "Server queue"
        assert screen.check_action("fetch_save_file", ()) is True
        assert "fetch save file" in str(screen.query_one("#queue-actions", Static).render())
        # WS progress frames render into the grouped table.
        job, batch = uuid4(), uuid4()
        client.push_ws(ws_queued(job, batch, track_name="Aerodynamic"))
        client.push_ws(ws_started(job, batch))
        client.push_ws(ws_progress(job, batch, phase="download", percent=40))
        await pilot.pause()
        assert screen.query_one(QueueTable).job_row_count == 1
        assert "40%" in str(screen.query_one(QueueTable).get_row(str(job))[2])
        # ``f`` surfaces the focused batch's server save-file URL.
        await pilot.press("f")
        await pilot.pause()
        assert any(
            f"/api/v1/downloads/batches/{batch}/save-file" in n.message for n in app._notifications
        )


# --- WsHello seam: both shapes surface the same typed error -------------------


async def test_stream_surfaces_mismatch_from_fake_hello_frame() -> None:
    """Fake-shaped stream: the hello frame is *yielded* and the in-stream check trips."""
    client = FakeSpotdlClient()
    vm = QueueViewModel(client, make_session())
    client.push_ws(ws_hello(protocol_version=WS_PROTOCOL_VERSION + 1))
    client.close_ws()
    results = [update async for update in vm.stream()]
    assert len(results) == 1
    assert results[0].state is LoadState.ERROR
    assert results[0].error is not None
    assert "newer download-progress protocol" in results[0].error.message


class _MismatchClient:
    """Real-shaped stub: ``progress()`` consumes the hello and raises like the client."""

    @asynccontextmanager
    async def progress(self) -> AsyncIterator[AsyncIterator[WsMessage]]:
        async def _frames() -> AsyncIterator[WsMessage]:
            raise UnsupportedProtocol(WS_PROTOCOL_VERSION + 1)
            yield  # pragma: no cover — makes this an async generator

        yield _frames()


async def test_stream_surfaces_mismatch_from_real_client_exception() -> None:
    """Real-shaped stream: ``UnsupportedProtocol`` is recognised structurally."""
    vm = QueueViewModel(_MismatchClient(), make_session())  # type: ignore[arg-type]
    results = [update async for update in vm.stream()]
    assert len(results) == 1
    assert results[0].state is LoadState.ERROR
    assert results[0].error is not None
    assert "newer download-progress protocol" in results[0].error.message


@pytest.mark.parametrize("_", [0])
def test_module_imports(_: int) -> None:
    # Cheap guard that the screen/widget import cleanly (no cycle via app/router).
    assert QueueScreen is not None and QueueTable is not None
