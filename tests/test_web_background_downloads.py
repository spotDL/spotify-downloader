"""Regression tests for background web downloads."""

import asyncio
import logging
from unittest.mock import Mock

from spotdl.utils.web import Client, app_state
from spotdl.web import routes
from spotdl.web.utils import Signals


def make_client():
    client = Client.__new__(Client)
    client.client_id = "background-test"
    client.download_tasks = set()
    client.download_lock = asyncio.Lock()
    client.disconnect_timer = None
    client.downloader_settings = {"output": "{artists} - {title}.{output-ext}"}
    return client


async def test_request_cancellation_does_not_cancel_download(monkeypatch):
    client = make_client()
    started = asyncio.Event()
    release = asyncio.Event()
    completed = asyncio.Event()

    async def fake_download(signals):
        started.set()
        await release.wait()
        completed.set()
        yield "finished"

    monkeypatch.setattr(routes, "gen_download", fake_download)
    monkeypatch.setattr(routes.Client, "get_instance", lambda _: client)
    monkeypatch.setattr(app_state, "logger", logging.getLogger("test"), raising=False)

    async def request():
        signals = Signals()
        signals.client_id = client.client_id
        assert routes.start_background_download(signals)
        await asyncio.Event().wait()

    request_task = asyncio.create_task(request())
    await asyncio.wait_for(started.wait(), timeout=1)
    download_task = next(iter(client.download_tasks))

    request_task.cancel()
    await asyncio.gather(request_task, return_exceptions=True)
    assert not download_task.cancelled()

    release.set()
    await asyncio.wait_for(download_task, timeout=1)
    await asyncio.sleep(0)
    assert completed.is_set()
    assert not client.download_tasks


async def test_disconnect_retains_client_with_running_download(monkeypatch):
    client = make_client()
    release = asyncio.Event()
    task = client.start_download(release.wait())
    clients = {client.client_id: client}
    timer = Mock()

    monkeypatch.setattr(app_state, "clients", clients)
    monkeypatch.setattr(app_state, "logger", logging.getLogger("test"), raising=False)
    schedule = Mock(return_value=timer)
    monkeypatch.setattr(asyncio.get_running_loop(), "call_later", schedule)

    try:
        client.disconnect_now()
        assert clients[client.client_id] is client
        schedule.assert_called_once_with(15, client.disconnect_now)
    finally:
        release.set()
        await task
        await asyncio.sleep(0)

    client.disconnect_now()
    assert client.client_id not in clients


async def test_background_failure_is_retrieved_and_logged(monkeypatch):
    client = make_client()
    logger = Mock()
    monkeypatch.setattr(app_state, "logger", logger, raising=False)

    async def fail():
        raise RuntimeError("Expected failure")

    task = client.start_download(fail())
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.sleep(0)

    assert not client.download_tasks
    logger.error.assert_called_once()


async def test_queues_for_one_client_run_sequentially(monkeypatch):
    client = make_client()
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    order = []

    async def fake_download(signals):
        order.append(signals.song_url)
        if signals.song_url == "first":
            first_started.set()
            await release_first.wait()
        yield "finished"

    monkeypatch.setattr(routes, "gen_download", fake_download)
    monkeypatch.setattr(routes.Client, "get_instance", lambda _: client)
    monkeypatch.setattr(app_state, "logger", logging.getLogger("test"), raising=False)

    first = Signals()
    first.client_id = client.client_id
    first.song_url = "first"
    second = Signals()
    second.client_id = client.client_id
    second.song_url = "second"

    assert routes.start_background_download(first)
    await asyncio.wait_for(first_started.wait(), timeout=1)
    assert routes.start_background_download(second)
    await asyncio.sleep(0)
    tasks = list(client.download_tasks)

    try:
        assert order == ["first"]
    finally:
        release_first.set()
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=1)

    assert order == ["first", "second"]


async def test_reconnect_cancels_session_cleanup(monkeypatch):
    client = make_client()
    timer = Mock()
    client.disconnect_timer = timer
    clients = {}
    monkeypatch.setattr(app_state, "clients", clients)
    monkeypatch.setattr(app_state, "logger", logging.getLogger("test"), raising=False)

    await client.connect()

    timer.cancel.assert_called_once()
    assert client.disconnect_timer is None
    assert clients[client.client_id] is client


async def test_cancelled_download_is_released_without_error(monkeypatch):
    client = make_client()
    logger = Mock()
    monkeypatch.setattr(app_state, "logger", logger, raising=False)
    task = client.start_download(asyncio.Event().wait())
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.sleep(0)
    assert not client.download_tasks
    logger.error.assert_not_called()


async def test_shutdown_cancels_queues_before_directory_cleanup(monkeypatch):
    from spotdl.web import api

    client = make_client()
    task = client.start_download(asyncio.Event().wait())
    await asyncio.sleep(0)
    timer = Mock()
    client.disconnect_timer = timer
    monkeypatch.setattr(app_state, "clients", {client.client_id: client})
    monkeypatch.setattr(app_state, "logger", logging.getLogger("test"), raising=False)
    monkeypatch.setattr(
        app_state,
        "web_settings",
        {"keep_sessions": False, "web_use_output_dir": False},
        raising=False,
    )
    monkeypatch.setattr(api.Path, "exists", lambda _: True)

    def remove_directory(_):
        assert task.cancelled()
        assert not client.download_tasks

    cleanup = Mock(side_effect=remove_directory)
    monkeypatch.setattr(api.shutil, "rmtree", cleanup)
    await api.shutdown_event()
    timer.cancel.assert_called_once()
    cleanup.assert_called_once()
    assert client.disconnect_timer is None


def test_missing_session_does_not_start_download(monkeypatch):
    monkeypatch.setattr(routes.Client, "get_instance", lambda _: None)
    signals = Signals()
    signals.client_id = "expired"
    assert routes.start_background_download(signals) is False


async def test_destination_is_captured_before_queue_runs(monkeypatch):
    client = make_client()
    client.music_output = "/music/chosen/{title}.mp3"
    captured = []

    async def fake_download(signals):
        captured.append(signals.download_output)
        yield "finished"

    monkeypatch.setattr(routes, "gen_download", fake_download)
    monkeypatch.setattr(routes.Client, "get_instance", lambda _: client)
    signals = Signals()
    assert routes.start_background_download(signals)
    client.music_output = "/music/other/{title}.mp3"
    await asyncio.gather(*client.download_tasks)
    assert captured == ["/music/chosen/{title}.mp3"]
