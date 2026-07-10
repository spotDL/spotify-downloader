"""Tests for the Deezer metadata provider (Task 7).

Every test is offline except the single ``@pytest.mark.network`` live check:
pure-mapper tests run from checked-in JSON fixtures, and all HTTP behaviour is
mocked with ``respx``. The classic mapping bugs are asserted explicitly: Deezer
``duration`` is in **seconds** (must be ``*1000`` for ``duration_ms``), and a
"not found" is signalled by an HTTP 200 body carrying ``{"error": {...}}``.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from spotdl_core.model import EntityType, ProviderId, Track
from spotdl_core.providers.base import Enriches, Resolves, Searches, SearchesEntities
from spotdl_core.providers.errors import EntityNotFound, ProviderUnavailable
from spotdl_core.providers.http import create_client
from spotdl_core.providers.metadata.deezer import (
    DeezerProvider,
    build_deezer_provider,
    map_album,
    map_album_hits,
    map_artist_hits,
    map_playlist_hits,
    map_search,
    map_track,
    map_track_hits,
)
from spotdl_core.providers.registry import ProviderContext
from spotdl_core.providers.urls import PlatformRef

_API = "https://api.deezer.com"
_KNOWN_TRACK = "3135556"


def _provider(client: httpx.AsyncClient) -> DeezerProvider:
    return DeezerProvider(client)


# --- pure mappers ---------------------------------------------------------


def test_deezer_map_track_from_fixture(load_fixture: Any) -> None:
    payload = load_fixture("deezer", "track")
    track = map_track(payload)

    assert track.name == payload["title"]
    assert track.provider is ProviderId.DEEZER
    assert track.provider_id == str(payload["id"])
    assert track.isrc == payload["isrc"]
    assert track.track_number == payload["track_position"]
    assert track.disc_number == payload["disk_number"]
    assert track.explicit == payload["explicit_lyrics"]
    # main artist plus contributors, de-duplicated, order preserved
    assert track.artists[0] == payload["artist"]["name"]
    assert track.album is not None
    assert track.album.name == payload["album"]["title"]
    assert track.album.year == int(payload["album"]["release_date"][:4])
    assert track.album.cover_url == payload["album"]["cover_xl"]


def test_deezer_duration_seconds_to_ms(load_fixture: Any) -> None:
    payload = load_fixture("deezer", "track")
    track = map_track(payload)
    # CONTRACT: Deezer reports duration in seconds; the model stores milliseconds.
    assert track.duration_ms == int(payload["duration"]) * 1000
    assert track.duration_ms == 226_000


def test_deezer_map_album_injects_album_context(load_fixture: Any) -> None:
    album_payload = load_fixture("deezer", "album")
    # Track 3135556 belongs to album 302127 (Discovery); use it as a full track.
    full_track = load_fixture("deezer", "track")
    resolved = map_album(album_payload, [full_track])

    assert resolved.entity_type is EntityType.ALBUM
    assert resolved.provider is ProviderId.DEEZER
    assert resolved.provider_id == str(album_payload["id"])
    assert resolved.album is not None
    assert resolved.album.name == album_payload["title"]
    assert resolved.album.track_count == album_payload["nb_tracks"]
    assert len(resolved.tracks) == 1
    assert resolved.tracks[0].album == resolved.album  # album context injected


def test_deezer_map_search_returns_tracks(load_fixture: Any) -> None:
    payload = load_fixture("deezer", "search")
    tracks = map_search(payload)
    items = payload["data"]
    assert tracks
    assert len(tracks) == len(items)
    assert all(isinstance(t, Track) for t in tracks)
    assert all(t.provider is ProviderId.DEEZER for t in tracks)
    assert tracks[0].name == items[0]["title"]
    # seconds -> ms holds for search results too
    assert tracks[0].duration_ms == int(items[0]["duration"]) * 1000


# --- provider (respx) -----------------------------------------------------


@respx.mock
async def test_resolve_track_returns_track(load_fixture: Any) -> None:
    payload = load_fixture("deezer", "track")
    respx.get(f"{_API}/track/{_KNOWN_TRACK}").mock(return_value=httpx.Response(200, json=payload))
    ref = PlatformRef(ProviderId.DEEZER, EntityType.TRACK, _KNOWN_TRACK)
    async with create_client(base_url=_API) as client:
        resolved = await _provider(client).resolve(ref)
    assert resolved.entity_type is EntityType.TRACK
    assert resolved.track is not None
    assert resolved.track.isrc == payload["isrc"]
    assert resolved.track.duration_ms == int(payload["duration"]) * 1000


@respx.mock
async def test_resolve_album_refetches_each_track() -> None:
    album_id = "42"
    album = {
        "id": album_id,
        "title": "Small Album",
        "release_date": "2019-01-01",
        "nb_tracks": 2,
        "cover_xl": "https://img/xl",
        "artist": {"name": "The Band"},
        "tracks": {"data": [{"id": 1}, {"id": 2}]},
    }
    track1 = {
        "id": 1,
        "title": "One",
        "duration": 100,
        "isrc": "AAA",
        "track_position": 1,
        "disk_number": 1,
        "explicit_lyrics": False,
        "artist": {"name": "The Band"},
        "album": {"title": "Small Album", "release_date": "2019-01-01"},
    }
    track2 = {**track1, "id": 2, "title": "Two", "duration": 200, "track_position": 2}
    respx.get(f"{_API}/album/{album_id}").mock(return_value=httpx.Response(200, json=album))
    respx.get(f"{_API}/track/1").mock(return_value=httpx.Response(200, json=track1))
    respx.get(f"{_API}/track/2").mock(return_value=httpx.Response(200, json=track2))
    ref = PlatformRef(ProviderId.DEEZER, EntityType.ALBUM, album_id)
    async with create_client(base_url=_API) as client:
        resolved = await _provider(client).resolve(ref)
    assert resolved.entity_type is EntityType.ALBUM
    assert [t.name for t in resolved.tracks] == ["One", "Two"]
    # re-fetched full tracks carry the isrc that album-listing entries lack
    assert resolved.tracks[0].isrc == "AAA"
    assert resolved.tracks[1].duration_ms == 200_000
    assert all(t.album == resolved.album for t in resolved.tracks)


@respx.mock
async def test_search_returns_tracks(load_fixture: Any) -> None:
    payload = load_fixture("deezer", "search")
    route = respx.get(f"{_API}/search/track").mock(return_value=httpx.Response(200, json=payload))
    async with create_client(base_url=_API) as client:
        tracks = await _provider(client).search("daft punk", limit=5)
    assert tracks
    assert all(t.provider is ProviderId.DEEZER for t in tracks)
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["q"] == "daft punk"
    assert params["limit"] == "5"


def test_deezer_map_entity_hits() -> None:
    album = map_album_hits(
        {
            "data": [
                {
                    "id": 302127,
                    "title": "Discovery",
                    "artist": {"name": "Daft Punk"},
                    "cover_xl": "https://img/xl",
                }
            ]
        }
    )
    assert len(album) == 1
    assert album[0].entity_type is EntityType.ALBUM
    assert album[0].provider is ProviderId.DEEZER
    assert album[0].provider_id == "302127"
    assert album[0].subtitle == "Daft Punk"
    assert album[0].cover_url == "https://img/xl"
    assert album[0].year is None  # album search carries no release_date

    artist = map_artist_hits(
        {"data": [{"id": 27, "name": "Daft Punk", "picture_big": "https://p"}]}
    )
    assert artist[0].entity_type is EntityType.ARTIST
    assert artist[0].subtitle is None
    assert artist[0].cover_url == "https://p"

    playlist = map_playlist_hits(
        {"data": [{"id": 908622995, "title": "Rock", "user": {"name": "Jane"}}]}
    )
    assert playlist[0].entity_type is EntityType.PLAYLIST
    assert playlist[0].provider_id == "908622995"
    assert playlist[0].subtitle == "Jane"


def test_deezer_map_track_hits_from_search(load_fixture: Any) -> None:
    hits = map_track_hits(load_fixture("deezer", "search"))
    assert hits
    assert all(hit.entity_type is EntityType.TRACK for hit in hits)
    assert all(hit.provider is ProviderId.DEEZER for hit in hits)
    assert hits[0].isrc is not None  # track hits carry isrc for de-dup


def test_deezer_provider_satisfies_searches_entities() -> None:
    assert isinstance(_provider(httpx.AsyncClient()), SearchesEntities)


@respx.mock
async def test_search_entities_parallel_per_type() -> None:
    track_route = respx.get(f"{_API}/search/track").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": 1,
                        "title": "One More Time",
                        "duration": 320,
                        "isrc": "GBDUW0000048",
                        "artist": {"name": "Daft Punk"},
                        "album": {"title": "Discovery", "cover_xl": "https://img/xl"},
                    }
                ]
            },
        )
    )
    album_route = respx.get(f"{_API}/search/album").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"id": 302127, "title": "Discovery", "artist": {"name": "Daft Punk"}}]},
        )
    )
    artist_route = respx.get(f"{_API}/search/artist").mock(
        return_value=httpx.Response(200, json={"data": [{"id": 27, "name": "Daft Punk"}]})
    )
    playlist_route = respx.get(f"{_API}/search/playlist").mock(
        return_value=httpx.Response(
            200, json={"data": [{"id": 9, "title": "Best of Daft", "user": {"name": "Deezer"}}]}
        )
    )
    async with create_client(base_url=_API) as client:
        hits = await _provider(client).search_entities("daft punk", limit=5)

    assert track_route.called and album_route.called
    assert artist_route.called and playlist_route.called
    assert {hit.entity_type for hit in hits} == {
        EntityType.TRACK,
        EntityType.ALBUM,
        EntityType.ARTIST,
        EntityType.PLAYLIST,
    }


@respx.mock
async def test_search_entities_only_requested_types() -> None:
    album_route = respx.get(f"{_API}/search/album").mock(
        return_value=httpx.Response(200, json={"data": [{"id": 1, "title": "A"}]})
    )
    track_route = respx.get(f"{_API}/search/track").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    async with create_client(base_url=_API) as client:
        hits = await _provider(client).search_entities("x", types=frozenset({EntityType.ALBUM}))

    assert album_route.called
    assert not track_route.called  # only the requested type is queried
    assert [hit.entity_type for hit in hits] == [EntityType.ALBUM]


@respx.mock
async def test_search_entities_propagates_provider_error() -> None:
    respx.get(f"{_API}/search/track").mock(
        return_value=httpx.Response(
            200, json={"error": {"type": "DataException", "message": "no", "code": 800}}
        )
    )
    respx.get(f"{_API}/search/album").mock(return_value=httpx.Response(200, json={"data": []}))
    respx.get(f"{_API}/search/artist").mock(return_value=httpx.Response(200, json={"data": []}))
    respx.get(f"{_API}/search/playlist").mock(return_value=httpx.Response(200, json={"data": []}))
    async with create_client(base_url=_API) as client:
        with pytest.raises((EntityNotFound, ProviderUnavailable)):
            await _provider(client).search_entities("boom")


@respx.mock
async def test_deezer_200_error_body_raises_entity_not_found() -> None:
    # CONTRACT: Deezer signals "not found" via HTTP 200 with an ``error`` object.
    respx.get(f"{_API}/track/999").mock(
        return_value=httpx.Response(
            200, json={"error": {"type": "DataException", "message": "no data", "code": 800}}
        )
    )
    ref = PlatformRef(ProviderId.DEEZER, EntityType.TRACK, "999")
    async with create_client(base_url=_API) as client:
        with pytest.raises(EntityNotFound):
            await _provider(client).resolve(ref)


@respx.mock
async def test_search_empty_returns_empty_list() -> None:
    respx.get(f"{_API}/search/track").mock(
        return_value=httpx.Response(200, json={"data": [], "total": 0})
    )
    async with create_client(base_url=_API) as client:
        assert await _provider(client).search("nothing at all") == []


@respx.mock
async def test_enrich_fills_missing_isrc_from_deezer_id(load_fixture: Any) -> None:
    payload = load_fixture("deezer", "track")
    respx.get(f"{_API}/track/{_KNOWN_TRACK}").mock(return_value=httpx.Response(200, json=payload))
    bare = Track(
        name=payload["title"],
        artists=(payload["artist"]["name"],),
        duration_ms=int(payload["duration"]) * 1000,
        provider=ProviderId.DEEZER,
        provider_id=_KNOWN_TRACK,
    )
    async with create_client(base_url=_API) as client:
        enriched = await _provider(client).enrich(bare)
    assert enriched.isrc == payload["isrc"]
    assert enriched.album is not None


# --- wiring / capabilities ------------------------------------------------


async def test_provider_advertises_capabilities() -> None:
    provider = build_deezer_provider(ProviderContext())
    try:
        assert provider.id is ProviderId.DEEZER
        assert isinstance(provider, Resolves)
        assert isinstance(provider, Searches)
        assert isinstance(provider, Enriches)
    finally:
        await provider.aclose()


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_deezer_resolve_known_track() -> None:
    provider = build_deezer_provider(ProviderContext())
    try:
        ref = PlatformRef(ProviderId.DEEZER, EntityType.TRACK, _KNOWN_TRACK)
        resolved = await provider.resolve(ref)
    finally:
        await provider.aclose()
    assert resolved.track is not None
    assert resolved.track.isrc
    assert resolved.track.duration_ms > 0
