"""Offline tests for ``GET /api/v1/search`` (spec §6.2)."""

from __future__ import annotations

from pathlib import Path

from spotdl_core.model import ProviderId, Track

from apps.server.tests.api.support import api_client
from apps.server.tests.fakes import FakeSearcher, build_fake_registry


def _track(name: str) -> Track:
    return Track(
        name=name,
        artists=("Artist",),
        duration_ms=200_000,
        provider=ProviderId.SPOTIFY,
        provider_id=f"sp-{name}",
    )


async def test_search_returns_results(tmp_path: Path) -> None:
    registry = build_fake_registry(
        FakeSearcher(id=ProviderId.SPOTIFY, tracks=[_track("One"), _track("Two")])
    )
    async with api_client(registry, data_dir=tmp_path) as client:
        resp = await client.get("/api/v1/search", params={"q": "adele", "limit": 5})

    assert resp.status_code == 200
    body = resp.json()
    assert {t["name"] for t in body["results"]} == {"One", "Two"}
    assert body["degraded_sources"] == []


async def test_search_missing_query_returns_422(tmp_path: Path) -> None:
    registry = build_fake_registry(FakeSearcher(id=ProviderId.SPOTIFY, tracks=[]))
    async with api_client(registry, data_dir=tmp_path) as client:
        resp = await client.get("/api/v1/search")

    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"


async def test_search_degraded_source_surfaces(tmp_path: Path) -> None:
    registry = build_fake_registry(
        FakeSearcher(id=ProviderId.SPOTIFY, tracks=[_track("One")]),
        failing=[ProviderId.DEEZER],
    )
    async with api_client(registry, data_dir=tmp_path) as client:
        resp = await client.get("/api/v1/search", params={"q": "adele"})

    assert resp.status_code == 200
    assert "deezer" in resp.json()["degraded_sources"]
