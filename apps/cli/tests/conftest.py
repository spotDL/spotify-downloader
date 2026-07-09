"""Shared pytest fixtures for the ``spotdl_cli`` suite.

Mirrors the server suite's env isolation: strip ``SPOTDL_``-prefixed
environment variables so a developer's real config never leaks into a test run
(the embedded ``Settings`` the CLI builds read the same ``SPOTDL_`` prefix).

Also exposes ``fake_factory`` — the app factory the embedded-transport tests
hand to :class:`~spotdl_cli.transport.EmbeddedTransport`. It builds the real
server app via the ``create_app(settings, registry=..., download_engine=...)``
seams, wiring the **server suite's** fake providers and offline download engine
so the CLI's embedded path is exercised end-to-end without touching the network.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from spotdl_core.model import ProviderId, Track
from spotdl_server.app import create_app
from spotdl_server.settings import Settings

from apps.server.tests.conftest import FakeDownloadEngine
from apps.server.tests.fakes import FakeResolver, build_fake_registry


@pytest.fixture(autouse=True)
def _isolate_spotdl_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip ``SPOTDL_``-prefixed env vars so tests relying on ``Settings()``
    defaults are hermetic regardless of the developer's ambient shell."""
    for key in list(os.environ):
        if key.startswith("SPOTDL_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def fake_factory() -> Callable[[Settings], FastAPI]:
    """Build the server app with fake providers + an offline download engine.

    A ``FakeResolver`` returns a canned "Hello" track for any ref, so the
    embedded ``POST /resolve`` path resolves without a real provider. When the
    settings enable downloads (selfhost/embedded), the offline
    :class:`FakeDownloadEngine` is injected so the download pool the lifespan
    boots never reaches for yt-dlp/ffmpeg or the network.
    """

    def factory(settings: Settings) -> FastAPI:
        registry = build_fake_registry(
            FakeResolver(
                id=ProviderId.SPOTIFY,
                track=Track(
                    name="Hello", artists=("Adele",), duration_ms=200_000, isrc="USABC1234567"
                ),
            )
        )
        download_engine = None
        if settings.downloads_enabled():
            download_engine = FakeDownloadEngine(config=settings.download_config())
        return create_app(settings, registry=registry, download_engine=download_engine)

    return factory
