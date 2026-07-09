"""Offline tests for ``POST /api/v1/resolve`` (spec §6.2).

Every provider is faked at the registry seam; the app talks to an in-schema
SQLite DB. Asserts the ``ResolveResponse`` contract shape, the ``degraded_sources``
surfacing rule (a failed source is reported but is not fatal when another
succeeds), and the two error envelopes: 400 ``unsupported_url`` and 502
``provider_unavailable``.
"""

from __future__ import annotations

from pathlib import Path

from spotdl_core.model import AudioCandidate, ProviderId, Track

from apps.server.tests.api.support import api_client
from apps.server.tests.fakes import (
    FakeAudioProvider,
    FakeResolver,
    FakeSearcher,
    build_fake_registry,
)

SPOTIFY_URL = "https://open.spotify.com/track/track123"


def _track(name: str = "Song", artist: str = "Artist") -> Track:
    return Track(name=name, artists=(artist,), duration_ms=200_000, isrc="USABC1234567")


async def test_resolve_track_happy_path(tmp_path: Path) -> None:
    registry = build_fake_registry(
        FakeResolver(id=ProviderId.SPOTIFY, track=_track("Hello", "Adele"))
    )
    async with api_client(registry, data_dir=tmp_path) as client:
        resp = await client.post("/api/v1/resolve", json={"query": SPOTIFY_URL})

    assert resp.status_code == 200
    body = resp.json()
    assert body["entity"]["type"] == "track"
    assert body["entity"]["track"]["name"] == "Hello"
    assert body["entity"]["track"]["artists"] == ["Adele"]
    assert body["entity"]["album"] is None
    assert body["degraded_sources"] == []


async def test_resolve_unsupported_url_returns_400(tmp_path: Path) -> None:
    # Not a URL and the searcher finds nothing → UnsupportedURL re-raised → 400.
    registry = build_fake_registry(FakeSearcher(id=ProviderId.DEEZER, tracks=[]))
    async with api_client(registry, data_dir=tmp_path) as client:
        resp = await client.post("/api/v1/resolve", json={"query": "definitely not a url"})

    assert resp.status_code == 400
    assert resp.json()["code"] == "unsupported_url"


async def test_resolve_provider_failure_surfaces_in_degraded_not_502(tmp_path: Path) -> None:
    registry = build_fake_registry(
        FakeResolver(id=ProviderId.SPOTIFY, track=_track()),
        failing=[ProviderId.DEEZER],
    )
    async with api_client(registry, data_dir=tmp_path) as client:
        resp = await client.post("/api/v1/resolve", json={"query": SPOTIFY_URL})

    assert resp.status_code == 200
    body = resp.json()
    assert body["entity"]["track"]["name"] == "Song"
    assert "deezer" in body["degraded_sources"]


async def test_resolve_total_provider_unavailability_returns_502(tmp_path: Path) -> None:
    # The ref parses to SPOTIFY but no Spotify provider is registered.
    registry = build_fake_registry(FakeResolver(id=ProviderId.DEEZER, track=_track()))
    async with api_client(registry, data_dir=tmp_path) as client:
        resp = await client.post("/api/v1/resolve", json={"query": SPOTIFY_URL})

    assert resp.status_code == 502
    assert resp.json()["code"] == "provider_unavailable"


async def test_resolve_kicked_matches_present_in_track_matches_endpoint(tmp_path: Path) -> None:
    candidate = AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt1",
        url="https://audio/yt1",
        name="Song",
        artists=("Artist",),
        duration_ms=200_000,
    )
    registry = build_fake_registry(
        FakeResolver(id=ProviderId.SPOTIFY, track=_track()),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=[candidate]),
    )
    async with api_client(registry, data_dir=tmp_path) as client:
        resolved = (await client.post("/api/v1/resolve", json={"query": SPOTIFY_URL})).json()
        track_id = resolved["entity"]["track"]["id"]
        matches = (await client.get(f"/api/v1/tracks/{track_id}/matches")).json()

    assert matches["track_id"] == track_id
    assert matches["matches"]
    assert matches["matches"][0]["target_provider"] == "youtube"
