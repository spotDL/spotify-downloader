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
from spotdl_core.providers.base import Enriches, Resolves, Searches, SearchesEntities
from spotdl_core.providers.errors import EntityNotFound
from spotdl_core.providers.http import create_client
from spotdl_core.providers.metadata.itunes import (
    ITunesProvider,
    build_itunes_provider,
    map_album,
    map_album_hits,
    map_artist_hits,
    map_search,
    map_song_hits,
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


# --- album metadata (copyright + type) ------------------------------------


def test_itunes_map_album_sets_copyright_and_type(load_fixture: Any) -> None:
    payload = load_fixture("itunes", "lookup_album")
    resolved = map_album(payload["results"])
    collection = payload["results"][0]
    assert resolved.album is not None
    assert resolved.album.copyright_text == collection["copyright"]
    assert resolved.album.album_type == collection["collectionType"].lower()  # "album"


# --- entity search --------------------------------------------------------


def test_map_album_hits_upscales_artwork() -> None:
    payload = {
        "results": [
            {
                "collectionId": 697194953,
                "collectionName": "Discovery",
                "artistName": "Daft Punk",
                "artworkUrl100": "https://is1.mzstatic.com/a/100x100bb.jpg",
                "releaseDate": "2001-03-12T08:00:00Z",
            }
        ]
    }
    hits = map_album_hits(payload)
    assert len(hits) == 1
    assert hits[0].entity_type is EntityType.ALBUM
    assert hits[0].provider is ProviderId.ITUNES
    assert hits[0].provider_id == "697194953"
    assert hits[0].subtitle == "Daft Punk"
    assert hits[0].year == 2001
    assert hits[0].cover_url is not None and "600x600" in hits[0].cover_url  # upscaled


def test_map_artist_hits_uses_genre_subtitle() -> None:
    payload = {
        "results": [
            {"artistId": 5468295, "artistName": "Daft Punk", "primaryGenreName": "Electronic"}
        ]
    }
    hits = map_artist_hits(payload)
    assert len(hits) == 1
    assert hits[0].entity_type is EntityType.ARTIST
    assert hits[0].provider_id == "5468295"
    assert hits[0].subtitle == "Electronic"  # primary genre -> subtitle
    assert hits[0].cover_url is None and hits[0].followers is None  # iTunes exposes neither


def test_map_song_hits_from_search_fixture(load_fixture: Any) -> None:
    hits = map_song_hits(load_fixture("itunes", "search"))
    assert hits and all(hit.entity_type is EntityType.TRACK for hit in hits)
    assert all(hit.provider is ProviderId.ITUNES for hit in hits)


@respx.mock
async def test_search_entities_requests_all_three_types(load_fixture: Any) -> None:
    song_payload = load_fixture("itunes", "search")
    respx.get(f"{_API}/search", params={"entity": "song"}).mock(
        return_value=httpx.Response(200, json=song_payload)
    )
    respx.get(f"{_API}/search", params={"entity": "album"}).mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"collectionId": 1, "collectionName": "Discovery"}]},
        )
    )
    respx.get(f"{_API}/search", params={"entity": "musicArtist"}).mock(
        return_value=httpx.Response(
            200, json={"results": [{"artistId": 2, "artistName": "Daft Punk"}]}
        )
    )
    async with create_client(base_url=_API) as client:
        hits = await _provider(client).search_entities("daft punk", limit=5)
    kinds = {hit.entity_type for hit in hits}
    assert kinds == {EntityType.TRACK, EntityType.ALBUM, EntityType.ARTIST}


@respx.mock
async def test_search_entities_playlist_only_returns_nothing() -> None:
    # iTunes has no playlist search -> a playlist-only request issues no request.
    async with create_client(base_url=_API) as client:
        hits = await _provider(client).search_entities(
            "daft punk", types=frozenset({EntityType.PLAYLIST})
        )
    assert hits == []


# --- artist resolve (lookup discography) ----------------------------------


@respx.mock
async def test_resolve_artist_returns_discography() -> None:
    artist_id = "5468295"
    payload = {
        "results": [
            {
                "wrapperType": "artist",
                "artistId": 5468295,
                "artistName": "Daft Punk",
                "primaryGenreName": "Electronic",
            },
            {
                "wrapperType": "collection",
                "collectionId": 697194953,
                "collectionName": "Discovery",
                "artistName": "Daft Punk",
                "collectionType": "Album",
                "releaseDate": "2001-03-12T08:00:00Z",
                "trackCount": 14,
                "artworkUrl100": "https://is1.mzstatic.com/a/100x100bb.jpg",
            },
            {
                "wrapperType": "collection",
                "collectionId": 697194954,
                "collectionName": "Discovery",  # dup name -> deduped
            },
            {
                "wrapperType": "collection",
                "collectionId": 5468291,
                "collectionName": "Homework",
                "collectionType": "Album",
                "releaseDate": "1997-01-20T08:00:00Z",
            },
        ]
    }
    route = respx.get(f"{_API}/lookup").mock(return_value=httpx.Response(200, json=payload))
    ref = PlatformRef(ProviderId.ITUNES, EntityType.ARTIST, artist_id)
    async with create_client(base_url=_API) as client:
        resolved = await _provider(client).resolve(ref)

    assert resolved.entity_type is EntityType.ARTIST
    assert resolved.artist is not None
    assert resolved.artist.genres == ("Electronic",)  # primaryGenreName -> genres
    assert resolved.tracks == ()  # no top tracks; overlap gate uses albums
    assert [album.name for album in resolved.albums] == ["Discovery", "Homework"]  # deduped
    disc = resolved.albums[0]
    assert disc.provider is ProviderId.ITUNES and disc.provider_id == "697194953"
    assert disc.album_type == "album" and disc.year == 2001
    assert disc.cover_url is not None and "600x600" in disc.cover_url
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["entity"] == "album"  # discography expanded via entity=album
    assert params["limit"] == "200"


# --- wiring / capabilities ------------------------------------------------


async def test_provider_advertises_capabilities() -> None:
    provider = build_itunes_provider(ProviderContext())
    try:
        assert provider.id is ProviderId.ITUNES
        assert isinstance(provider, Resolves)
        assert isinstance(provider, Searches)
        assert isinstance(provider, SearchesEntities)
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
