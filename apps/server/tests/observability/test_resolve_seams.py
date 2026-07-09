"""The resolve service actually moves the CONTRACT A2 metrics at its seams.

Drives the real offline resolve flow (migrated tmp DB + fake registry, over
``httpx.ASGITransport``) and asserts the snapshot-cache and matcher metrics move:
a first resolve is a cache *miss* that serves a match ranking; re-resolving the
same URL is a cache *hit*.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from spotdl_core.model import AudioCandidate, ProviderId, Track
from spotdl_server.app import create_app
from spotdl_server.bootstrap import upgrade_to_head
from spotdl_server.observability import metrics
from spotdl_server.settings import DeploymentMode, Settings

from apps.server.tests.fakes import (
    FakeAudioProvider,
    FakeLyricsProvider,
    FakeResolver,
    build_fake_registry,
)

SPOTIFY_URL = "https://open.spotify.com/track/seamtrack"
TRACK = Track(name="Song", artists=("Artist",), duration_ms=200_000, isrc="USABC1234567")
CANDIDATES = (
    AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt-best",
        url="https://audio/yt-best",
        name="Song",
        artists=("Artist",),
        duration_ms=200_000,
    ),
)


@asynccontextmanager
async def _client(data_dir: Path) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(mode=DeploymentMode.SELFHOST, data_dir=data_dir)
    await asyncio.to_thread(upgrade_to_head, settings)
    registry = build_fake_registry(
        FakeResolver(id=ProviderId.SPOTIFY, track=TRACK),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=list(CANDIDATES)),
        FakeLyricsProvider(id=ProviderId.GENIUS, text="la la la"),
    )
    app = create_app(settings, registry=registry)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


def _sample(name: str, labels: dict[str, str]) -> float:
    return metrics.REGISTRY.get_sample_value(name, labels) or 0.0


async def test_resolve_moves_cache_and_matcher_metrics(tmp_path: Path) -> None:
    snap = {"cache": "snapshot"}
    misses = _sample("spotdl_cache_misses_total", snap)
    hits = _sample("spotdl_cache_hits_total", snap)
    served = _sample("spotdl_matches_served_total", {"matcher_version": "v5.0"})

    async with _client(tmp_path) as client:
        first = await client.post("/api/v1/resolve", json={"query": SPOTIFY_URL})
        assert first.status_code == 200, first.text
        # First resolve: cache miss + a persisted match ranking.
        assert _sample("spotdl_cache_misses_total", snap) == misses + 1
        assert _sample("spotdl_matches_served_total", {"matcher_version": "v5.0"}) >= served + 1

        second = await client.post("/api/v1/resolve", json={"query": SPOTIFY_URL})
        assert second.status_code == 200, second.text
        # Re-resolving the same URL is served from the snapshot cache.
        assert _sample("spotdl_cache_hits_total", snap) == hits + 1
