"""Offline tests for the typed entity GETs (spec §6.2).

A canonical entity is first persisted by ``POST /resolve`` (the only writer);
these tests then read it back through the typed GETs and the ``/matches`` /
``/lyrics`` sub-resources, and assert the 404 ``not_found`` envelope for absent
and syntactically-invalid ids.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from spotdl_core.model import AudioCandidate, ProviderId, Track

from apps.server.tests.api.support import api_client
from apps.server.tests.fakes import (
    FakeAudioProvider,
    FakeResolver,
    build_fake_registry,
)

SPOTIFY_URL = "https://open.spotify.com/track/track123"


def _track() -> Track:
    return Track(name="Song", artists=("Artist",), duration_ms=200_000, isrc="USABC1234567")


def _candidate() -> AudioCandidate:
    return AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt1",
        url="https://audio/yt1",
        name="Song",
        artists=("Artist",),
        duration_ms=200_000,
    )


async def _resolve_track_id(client, url: str = SPOTIFY_URL) -> str:  # type: ignore[no-untyped-def]
    body = (await client.post("/api/v1/resolve", json={"query": url})).json()
    return body["entity"]["track"]["id"]


async def test_get_track_returns_track_out(tmp_path: Path) -> None:
    registry = build_fake_registry(FakeResolver(id=ProviderId.SPOTIFY, track=_track()))
    async with api_client(registry, data_dir=tmp_path) as client:
        track_id = await _resolve_track_id(client)
        resp = await client.get(f"/api/v1/tracks/{track_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == track_id
    assert body["name"] == "Song"
    assert body["artists"] == ["Artist"]


async def test_get_track_unknown_id_returns_404(tmp_path: Path) -> None:
    registry = build_fake_registry(FakeResolver(id=ProviderId.SPOTIFY, track=_track()))
    async with api_client(registry, data_dir=tmp_path) as client:
        resp = await client.get(f"/api/v1/tracks/{uuid.uuid4()}")

    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


async def test_get_track_invalid_uuid_returns_422(tmp_path: Path) -> None:
    registry = build_fake_registry(FakeResolver(id=ProviderId.SPOTIFY, track=_track()))
    async with api_client(registry, data_dir=tmp_path) as client:
        resp = await client.get("/api/v1/tracks/not-a-uuid")

    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"


async def test_track_matches_shape(tmp_path: Path) -> None:
    registry = build_fake_registry(
        FakeResolver(id=ProviderId.SPOTIFY, track=_track()),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=[_candidate()]),
    )
    async with api_client(registry, data_dir=tmp_path) as client:
        track_id = await _resolve_track_id(client)
        resp = await client.get(f"/api/v1/tracks/{track_id}/matches")

    assert resp.status_code == 200
    body = resp.json()
    assert body["track_id"] == track_id
    assert body["matches"][0]["target_provider"] == "youtube"
    assert body["matches"][0]["status"] == "auto"
    assert "net_score" in body["matches"][0]


async def test_track_lyrics_shape_empty(tmp_path: Path) -> None:
    registry = build_fake_registry(FakeResolver(id=ProviderId.SPOTIFY, track=_track()))
    async with api_client(registry, data_dir=tmp_path) as client:
        track_id = await _resolve_track_id(client)
        resp = await client.get(f"/api/v1/tracks/{track_id}/lyrics")

    assert resp.status_code == 200
    body = resp.json()
    assert body["track_id"] == track_id
    assert body["lyrics"] == []


async def test_matches_on_unknown_track_returns_404(tmp_path: Path) -> None:
    registry = build_fake_registry(FakeResolver(id=ProviderId.SPOTIFY, track=_track()))
    async with api_client(registry, data_dir=tmp_path) as client:
        resp = await client.get(f"/api/v1/tracks/{uuid.uuid4()}/matches")

    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


async def test_get_album_unknown_id_returns_404(tmp_path: Path) -> None:
    registry = build_fake_registry(FakeResolver(id=ProviderId.SPOTIFY, track=_track()))
    async with api_client(registry, data_dir=tmp_path) as client:
        for kind in ("albums", "artists", "playlists"):
            resp = await client.get(f"/api/v1/{kind}/{uuid.uuid4()}")
            assert resp.status_code == 404
            assert resp.json()["code"] == "not_found"
