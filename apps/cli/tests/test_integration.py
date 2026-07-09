"""End-to-end CLI integration (Plan 8 Task 13).

Drives the real command surface through ``CliRunner`` against an **embedded**
server (a tmp data dir, migrations and all) whose providers are faked at the
Plan 5 ``create_app(registry=...)`` seam and whose downloads run through the
offline :class:`FakeDownloadEngine` (``download_engine=...``). Nothing here
touches the network, yt-dlp, or ffmpeg:

* ``download`` submits over the embedded loopback server, streams WS progress to
  terminal, and the fake engine writes a real file at the templated output path;
* ``search`` / ``url`` resolve against the fakes over the ASGI resolution path;
* the bare-query / TTY dispatch and the ``tui`` stub are exercised directly.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi import FastAPI
from spotdl_cli.__main__ import _dispatch, app
from spotdl_cli.client import SpotdlClient
from spotdl_cli.commands import _support
from spotdl_cli.commands import download as dl
from spotdl_cli.commands.tui import TUI_STUB_MESSAGE
from spotdl_cli.errors import ExitCode
from spotdl_cli.transport import EmbeddedTransport
from spotdl_core.model import AudioCandidate, ProviderId, Track
from spotdl_server.app import create_app
from spotdl_server.settings import DeploymentMode, Settings
from typer.testing import CliRunner

from apps.server.tests.conftest import FakeDownloadEngine
from apps.server.tests.fakes import (
    FakeAudioProvider,
    FakeResolver,
    FakeSearcher,
    build_fake_registry,
)

runner = CliRunner()

TRACK = Track(name="Hello", artists=("Adele",), duration_ms=200_000, isrc="USABC1234567")
TRACK_URL = "https://open.spotify.com/track/track123"


def _rich_factory(settings: Settings) -> FastAPI:
    """Build the embedded app with resolve + search + audio fakes (and the engine).

    Distinct provider ids so all three capability protocols are covered without a
    registration clash: SPOTIFY resolves the URL to ``TRACK``, ITUNES answers
    search, YOUTUBE supplies the audio candidate the matcher/download consume.
    """
    candidate = AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt1",
        url="https://audio/yt1",
        name="Hello",
        artists=("Adele",),
        duration_ms=200_000,
    )
    registry = build_fake_registry(
        FakeResolver(id=ProviderId.SPOTIFY, track=TRACK),
        FakeSearcher(id=ProviderId.ITUNES, tracks=[TRACK]),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=[candidate]),
    )
    engine = (
        FakeDownloadEngine(config=settings.download_config())
        if settings.downloads_enabled()
        else None
    )
    return create_app(settings, registry=registry, download_engine=engine)


# --- download: full submit → WS progress → file on disk -----------------------


def test_download_end_to_end_writes_templated_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = tmp_path / "out"

    @asynccontextmanager
    async def _open(*, offline: bool, settings_env: dict[str, str]) -> AsyncIterator[SpotdlClient]:
        for key, value in settings_env.items():
            monkeypatch.setenv(key, value)
        settings = Settings(mode=DeploymentMode.EMBEDDED, data_dir=tmp_path)
        transport = EmbeddedTransport(settings, app_factory=_rich_factory, enable_downloads=True)
        await transport.start()
        try:
            yield SpotdlClient(resolution=transport, downloads=transport)
        finally:
            await transport.aclose()

    monkeypatch.setattr(dl, "_open_client", _open)

    result = runner.invoke(
        app,
        ["download", TRACK_URL, "-o", f"{library}/{{artists}}/{{title}}.{{output-ext}}"],
    )

    assert result.exit_code == ExitCode.OK, result.output
    assert "1 downloaded" in result.output
    produced = list(library.rglob("*.mp3"))
    assert produced, f"no output file under {library}: {list(library.rglob('*'))}"
    output = produced[0]
    assert output.parent.name == "Adele"
    assert output.name == "Hello.mp3"
    assert output.read_bytes()  # the fake engine wrote real bytes


# --- search / url over the resolution transport -------------------------------


def _patch_resolution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, enable_downloads: bool = False
) -> None:
    @asynccontextmanager
    async def _open(
        *, offline: bool = False, need_downloads: bool = False, require_remote: bool = False
    ) -> AsyncIterator[SpotdlClient]:
        settings = Settings(mode=DeploymentMode.EMBEDDED, data_dir=tmp_path)
        transport = EmbeddedTransport(
            settings,
            app_factory=_rich_factory,
            enable_downloads=enable_downloads or need_downloads,
        )
        await transport.start()
        try:
            yield SpotdlClient(resolution=transport, downloads=transport)
        finally:
            await transport.aclose()

    monkeypatch.setattr(_support, "open_client", _open)


def test_search_lists_fake_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_resolution(monkeypatch, tmp_path)
    result = runner.invoke(app, ["search", "adele hello"])
    assert result.exit_code == 0, result.output
    assert "Hello" in result.output
    assert "Adele" in result.output


def test_url_prints_top_audio_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_resolution(monkeypatch, tmp_path)
    result = runner.invoke(app, ["url", TRACK_URL])
    assert result.exit_code == 0, result.output
    assert "https://audio/yt1" in result.output


# --- bare-query / TTY dispatch + tui stub -------------------------------------


def test_bare_argv_non_tty_shows_help() -> None:
    """CliRunner's stdout is not a TTY → the empty argv falls through to help."""
    result = runner.invoke(app, [])
    assert "Usage:" in result.output


def test_dispatch_bare_tty_routes_to_tui(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)
    assert _dispatch([]) == ["tui"]


def test_dispatch_bare_non_tty_falls_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False, raising=False)
    assert _dispatch([]) == []


def test_dispatch_unknown_first_token_routes_to_download() -> None:
    assert _dispatch([TRACK_URL]) == ["download", TRACK_URL]


def test_dispatch_known_command_passes_through() -> None:
    assert _dispatch(["config", "get"]) == ["config", "get"]
    assert _dispatch(["--version"]) == ["--version"]


def test_tui_command_prints_stub() -> None:
    result = runner.invoke(app, ["tui"])
    assert result.exit_code == 0, result.output
    assert TUI_STUB_MESSAGE in result.output
