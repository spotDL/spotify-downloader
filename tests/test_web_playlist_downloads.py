"""Regression tests for downloading lists through the web."""

import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from spotdl.web import routes
from spotdl.web.utils import Signals


@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("previous_count", [0, 3])
async def test_download_every_song(monkeypatch, count, previous_count):
    songs = [SimpleNamespace(name=f"Song {i}") for i in range(count)]
    parse = Mock(return_value=songs)
    download = AsyncMock(return_value=(songs[0], Path("song.mp3")))
    client = SimpleNamespace(
        downloader_settings={"output": "{title}.{output-ext}"},
        downloader=SimpleNamespace(
            settings={},
            pool_download=download,
            progress_handler=Mock(song_count=previous_count),
        ),
    )
    monkeypatch.setattr(routes, "parse_query", parse)
    monkeypatch.setattr(routes.Client, "get_instance", lambda _: client)
    monkeypatch.setattr(
        routes.app_state,
        "web_settings",
        {"web_use_output_dir": True},
        raising=False,
    )
    monkeypatch.setattr(
        routes.app_state,
        "logger",
        logging.getLogger("test"),
        raising=False,
    )
    signals = Signals()
    signals.client_id = "test"
    resource = "track" if count == 1 else "playlist"
    signals.song_url = f"https://open.spotify.com/intl-es/{resource}/example"

    events = [event async for event in routes.gen_download(signals)]

    assert events
    client.downloader.progress_handler.set_song_count.assert_called_once_with(
        previous_count + count
    )
    assert download.await_count == count
    assert [call.args[0] for call in download.await_args_list] == songs
    assert parse.call_args.args[0] == [f"https://open.spotify.com/{resource}/example"]


async def test_song_failure_does_not_stop_playlist(monkeypatch):
    songs = [SimpleNamespace(name="First"), SimpleNamespace(name="Second")]
    download = AsyncMock(
        side_effect=[RuntimeError("Download failed"), (songs[1], Path("second.mp3"))]
    )
    client = SimpleNamespace(
        downloader_settings={"output": "{title}.{output-ext}"},
        downloader=SimpleNamespace(
            settings={},
            pool_download=download,
            progress_handler=Mock(song_count=0),
        ),
    )
    monkeypatch.setattr(routes, "parse_query", Mock(return_value=songs))
    monkeypatch.setattr(routes.Client, "get_instance", lambda _: client)
    monkeypatch.setattr(
        routes.app_state,
        "web_settings",
        {"web_use_output_dir": True},
        raising=False,
    )
    monkeypatch.setattr(
        routes.app_state,
        "logger",
        logging.getLogger("test"),
        raising=False,
    )
    signals = Signals()
    signals.client_id = "test"
    signals.song_url = "https://open.spotify.com/playlist/example"

    events = [event async for event in routes.gen_download(signals)]

    assert events
    assert download.await_count == 2
