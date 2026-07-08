"""Tests for the iTunes (Apple Music) metadata provider (Task 7).

Every test is offline except the single ``@pytest.mark.network`` live check:
pure-mapper tests run from checked-in JSON fixtures, and all HTTP behaviour is
mocked with ``respx``. The classic mapping bugs are asserted explicitly: iTunes
``trackTimeMillis`` is already **milliseconds** (used as-is, never multiplied),
iTunes exposes **no ISRC**, and the lookup API returns
``{"resultCount": 0, "results": []}`` for a miss.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from spotdl_core.model import EntityType, ProviderId, Track
from spotdl_core.providers.base import Enriches, Resolves, Searches
from spotdl_core.providers.errors import EntityNotFound
from spotdl_core.providers.http import create_client
from spotdl_core.providers.metadata.itunes import (
    ITunesProvider,
    build_itunes_provider,
    map_album,
    map_search,
    map_track,
)
from spotdl_core.providers.registry import ProviderContext
from spotdl_core.providers.urls import PlatformRef

_API = "https://itunes.apple.com"


def _provider(client: httpx.AsyncClient) -> ITunesProvider:
    return ITunesProvider(client)


def _track_result(load_fixture: Any) -> dict[str, Any]:
    return load_fixture("itunes", "lookup_track")["results"][0]


# --- pure mappers ---------------------------------------------------------


def test_itunes_map_track_from_fixture(load_fixture: Any) -> None:
    result = _track_result(load_fixture)
    track = map_track(result)

    assert track.name == result["trackName"]
    assert track.artists == (result["artistName"],)
    assert track.provider is ProviderId.ITUNES
    assert track.provider_id == str(result["trackId"])
    assert track.track_number == result["trackNumber"]
    assert track.disc_number == result["discNumber"]
    assert track.genres == (result["primaryGenreName"],)
    assert track.year == int(result["releaseDate"][:4])
    assert track.album is not None
    assert track.album.name == result["collectionName"]


def test_itunes_duration_is_ms(load_fixture: Any) -> None:
    result = _track_result(load_fixture)
    track = map_track(result)
    # CONTRACT: trackTimeMillis is already milliseconds; used directly (no *1000).
    assert track.duration_ms == result["trackTimeMillis"]
    assert track.duration_ms == 224_693


def test_itunes_has_no_isrc(load_fixture: Any) -> None:
    # CONTRACT: iTunes exposes no ISRC.
    assert map_track(_track_result(load_fixture)).isrc is None


def test_itunes_artwork_upgraded_to_600(load_fixture: Any) -> None:
    result = _track_result(load_fixture)
    track = map_track(result)
    assert track.album is not None and track.album.cover_url is not None
    assert "600x600" in track.album.cover_url
    assert "100x100" not in track.album.cover_url


def test_itunes_explicit_flag(load_fixture: Any) -> None:
    result = dict(_track_result(load_fixture))
    result["trackExplicitness"] = "explicit"
    assert map_track(result).explicit is True
    result["trackExplicitness"] = "notExplicit"
    assert map_track(result).explicit is False


def test_itunes_map_album_sets_entity_type_and_tracks(load_fixture: Any) -> None:
    payload = load_fixture("itunes", "lookup_album")
    resolved = map_album(payload["results"])
    track_results = [r for r in payload["results"] if r.get("wrapperType") == "track"]

    assert resolved.entity_type is EntityType.ALBUM
    assert resolved.provider is ProviderId.ITUNES
    assert resolved.album is not None
    assert len(resolved.tracks) == len(track_results)
    for track in resolved.tracks:
        assert track.provider is ProviderId.ITUNES
        assert track.album == resolved.album  # album context injected


def test_itunes_map_search_returns_tracks(load_fixture: Any) -> None:
    payload = load_fixture("itunes", "search")
    tracks = map_search(payload)
    assert tracks
    assert all(isinstance(t, Track) for t in tracks)
    assert all(t.provider is ProviderId.ITUNES for t in tracks)
    assert all(t.isrc is None for t in tracks)


# --- provider (respx) -----------------------------------------------------


@respx.mock
async def test_resolve_track_returns_track(load_fixture: Any) -> None:
    payload = load_fixture("itunes", "lookup_track")
    track_id = str(payload["results"][0]["trackId"])
    respx.get(f"{_API}/lookup", params={"id": track_id}).mock(
        return_value=httpx.Response(200, json=payload)
    )
    ref = PlatformRef(ProviderId.ITUNES, EntityType.TRACK, track_id)
    async with create_client(base_url=_API) as client:
        resolved = await _provider(client).resolve(ref)
    assert resolved.entity_type is EntityType.TRACK
    assert resolved.track is not None
    assert resolved.track.duration_ms == payload["results"][0]["trackTimeMillis"]
    assert resolved.track.isrc is None


@respx.mock
async def test_resolve_album_expands_tracks(load_fixture: Any) -> None:
    payload = load_fixture("itunes", "lookup_album")
    collection_id = str(payload["results"][0]["collectionId"])
    route = respx.get(f"{_API}/lookup").mock(return_value=httpx.Response(200, json=payload))
    ref = PlatformRef(ProviderId.ITUNES, EntityType.ALBUM, collection_id)
    async with create_client(base_url=_API) as client:
        resolved = await _provider(client).resolve(ref)
    assert resolved.entity_type is EntityType.ALBUM
    assert resolved.tracks
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["entity"] == "song"  # album tracks expanded via entity=song


@respx.mock
async def test_resolve_empty_raises_entity_not_found() -> None:
    respx.get(f"{_API}/lookup").mock(
        return_value=httpx.Response(200, json={"resultCount": 0, "results": []})
    )
    ref = PlatformRef(ProviderId.ITUNES, EntityType.TRACK, "0")
    async with create_client(base_url=_API) as client:
        with pytest.raises(EntityNotFound):
            await _provider(client).resolve(ref)


@respx.mock
async def test_search_returns_tracks(load_fixture: Any) -> None:
    payload = load_fixture("itunes", "search")
    route = respx.get(f"{_API}/search").mock(return_value=httpx.Response(200, json=payload))
    async with create_client(base_url=_API) as client:
        tracks = await _provider(client).search("daft punk", limit=5)
    assert tracks
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["media"] == "music"
    assert params["entity"] == "song"
    assert params["limit"] == "5"


@respx.mock
async def test_search_empty_returns_empty_list() -> None:
    respx.get(f"{_API}/search").mock(
        return_value=httpx.Response(200, json={"resultCount": 0, "results": []})
    )
    async with create_client(base_url=_API) as client:
        assert await _provider(client).search("no results whatsoever") == []


@respx.mock
async def test_enrich_fills_missing_genres_via_search(load_fixture: Any) -> None:
    payload = load_fixture("itunes", "search")
    respx.get(f"{_API}/search").mock(return_value=httpx.Response(200, json=payload))
    first = payload["results"][0]
    bare = Track(
        name=first["trackName"],
        artists=(first["artistName"],),
        duration_ms=first["trackTimeMillis"],
        provider=ProviderId.SPOTIFY,
    )
    async with create_client(base_url=_API) as client:
        enriched = await _provider(client).enrich(bare)
    assert enriched.genres  # a genre was filled from iTunes
    assert enriched.isrc is None  # iTunes never supplies an ISRC


# --- wiring / capabilities ------------------------------------------------


async def test_provider_advertises_capabilities() -> None:
    provider = build_itunes_provider(ProviderContext())
    try:
        assert provider.id is ProviderId.ITUNES
        assert isinstance(provider, Resolves)
        assert isinstance(provider, Searches)
        assert isinstance(provider, Enriches)
    finally:
        await provider.aclose()


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_itunes_resolve_known_track() -> None:
    provider = build_itunes_provider(ProviderContext())
    try:
        ref = PlatformRef(ProviderId.ITUNES, EntityType.TRACK, "697195787")
        resolved = await provider.resolve(ref)
    finally:
        await provider.aclose()
    assert resolved.track is not None
    assert resolved.track.duration_ms > 0
    assert resolved.track.isrc is None
