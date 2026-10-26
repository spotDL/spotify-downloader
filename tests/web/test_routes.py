import asyncio
import logging
from types import SimpleNamespace

import pytest

from spotdl.types.options import DownloaderOptions
from spotdl.utils import web as web_utils
from spotdl.utils.config import DOWNLOADER_OPTIONS
from spotdl.utils.web import Client, app_state
from spotdl.web import routes


@pytest.fixture(autouse=True)
def fake_app_state(monkeypatch):
    """Set up the parts of the app state that clients use"""

    monkeypatch.setattr(
        app_state,
        "downloader_settings",
        DownloaderOptions(**DOWNLOADER_OPTIONS),  # type: ignore
        raising=False,
    )
    monkeypatch.setattr(app_state, "loop", None, raising=False)
    monkeypatch.setattr(
        app_state, "logger", logging.getLogger("spotdl-test"), raising=False
    )
    monkeypatch.setattr(app_state, "clients", {})


@pytest.fixture(autouse=True)
def fake_downloader(monkeypatch):
    """Don't create a real downloader, it needs ffmpeg"""

    monkeypatch.setattr(
        web_utils,
        "Downloader",
        lambda settings, loop=None: SimpleNamespace(settings=dict(settings)),
    )


@pytest.fixture(autouse=True)
def no_status_delay(monkeypatch):
    """Don't wait before clearing the settings status message"""

    real_sleep = asyncio.sleep

    async def fake_sleep(delay, *args, **kwargs):
        await real_sleep(0)

    monkeypatch.setattr(routes.asyncio, "sleep", fake_sleep)


@pytest.fixture()
def client():
    client = Client("test-client")
    app_state.clients[client.client_id] = client

    return client


def post_settings(settings):
    """Call the settings handler and return the events it sends as text"""

    signals = {"client_id": "test-client"}
    if settings is not None:
        signals["downloader_settings"] = settings

    async def run():
        response = await routes.handle_post_client_settings(signals)
        return "".join(
            [
                chunk if isinstance(chunk, str) else chunk.decode()
                async for chunk in response.body_iterator
            ]
        )

    return asyncio.run(run())


@pytest.mark.parametrize(
    "key, value",
    [
        ("ffmpeg", "calc.exe"),
        ("yt_dlp_args", "--exec 'touch /tmp/pwned'"),
        ("ffmpeg_args", "-y /tmp/pwned"),
        ("output", "/{title}.{output-ext}"),
        ("cookie_file", "/etc/passwd"),
    ],
)
def test_post_settings_ignores_restricted(client, key, value):
    original = client.downloader_settings[key]
    settings = dict(client.downloader_settings)
    settings[key] = value

    response = post_settings(settings)

    assert "settings-is-saved" in response
    assert client.downloader_settings[key] == original
    assert client.downloader.settings[key] == original


def test_post_settings_applies_allowed(client):
    settings = dict(client.downloader_settings)
    settings["format"] = "flac"

    response = post_settings(settings)

    assert "settings-is-saved" in response
    assert client.downloader_settings["format"] == "flac"
    # The downloader is re-initialized with the new settings
    assert client.downloader.settings["format"] == "flac"


@pytest.mark.parametrize("settings", [{"format": "exe"}, "not settings"])
def test_post_settings_rejects_invalid(client, settings):
    original = dict(client.downloader_settings)

    response = post_settings(settings)

    assert "settings-is-not-saved" in response
    assert client.downloader_settings == original


def test_post_settings_without_settings_keeps_settings(client):
    original = dict(client.downloader_settings)

    response = post_settings(None)

    assert "settings-is-saved" in response
    assert client.downloader_settings == original
