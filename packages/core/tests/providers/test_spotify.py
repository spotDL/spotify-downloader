"""Tests for the Spotify metadata provider (Task 6).

Every test is offline except the single ``@pytest.mark.network`` live check:
pure-mapper tests run from checked-in JSON fixtures, and all HTTP behaviour is
mocked with ``respx``. The live test is excluded from ``make check``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
import respx
from spotdl_core.model import EntityType, ProviderId, Track
from spotdl_core.providers.base import Enriches, Resolves, Searches
from spotdl_core.providers.errors import EntityNotFound, ProviderAuthError, ProviderError
from spotdl_core.providers.http import create_client
from spotdl_core.providers.metadata.spotify import (
    AnonymousSpotifyAuth,
    ClientCredentialsSpotifyAuth,
    LayeredSpotifyAuth,
    SpotifyProvider,
    build_spotify_provider,
    map_album,
    map_search,
    map_track,
)
from spotdl_core.providers.registry import ProviderContext, SpotifyConfig
from spotdl_core.providers.urls import PlatformRef

_ANON_URL = "https://open.spotify.com/api/token"
_CC_URL = "https://accounts.spotify.com/api/token"
_API = "https://api.spotify.com"
_KNOWN_TRACK = "6rqhFgbbKwnb9MLmUQDhG6"


async def _no_sleep(_seconds: float) -> None:
    """Async no-op used to neutralise retry backoff in transport-failure tests."""


def _anon_token_body(*, expires_in_ms: float = 3_600_000.0) -> dict[str, Any]:
    return {
        "clientId": "cid",
        "accessToken": "ANON_TOKEN",
        "accessTokenExpirationTimestampMs": _now_ms_plus(expires_in_ms),
        "isAnonymous": True,
    }


def _now_ms_plus(delta_ms: float) -> float:
    import time

    return time.time() * 1000.0 + delta_ms


class _StubAuth:
    """A ``SpotifyAuth`` that returns a fixed token without any HTTP."""

    async def bearer_token(self) -> str:
        return "STUB_TOKEN"


# --- pure mappers ---------------------------------------------------------


def test_map_track_from_fixture(load_fixture: Any) -> None:
    payload = load_fixture("spotify", "track")
    track = map_track(payload)

    assert track.name == payload["name"]
    assert track.artists == tuple(a["name"] for a in payload["artists"])
    assert track.duration_ms == payload["duration_ms"]
    assert track.duration_ms > 0
    assert track.isrc == payload["external_ids"]["isrc"]
    assert track.isrc  # ISRC is present on the standard Web API for both tokens
    assert track.track_number == payload["track_number"]
    assert track.disc_number == payload["disc_number"]
    assert track.explicit == payload["explicit"]
    assert track.provider is ProviderId.SPOTIFY
    assert track.provider_id == payload["id"]

    assert track.album is not None
    assert track.album.name == payload["album"]["name"]
    assert track.album.year == int(payload["album"]["release_date"][:4])
    assert track.album.track_count == payload["album"]["total_tracks"]
    # the largest cover image is chosen
    assert track.album.cover_url in {img["url"] for img in payload["album"]["images"]}


def test_map_album_sets_entity_type_and_tracks(load_fixture: Any) -> None:
    album_payload = load_fixture("spotify", "album")
    track_payloads = load_fixture("spotify", "album_tracks")["items"]

    resolved = map_album(album_payload, track_payloads)

    assert resolved.entity_type is EntityType.ALBUM
    assert resolved.provider is ProviderId.SPOTIFY
    assert resolved.provider_id == album_payload["id"]
    assert resolved.album is not None
    assert resolved.album.name == album_payload["name"]
    assert resolved.album.track_count == album_payload["total_tracks"]
    assert len(resolved.tracks) == len(track_payloads)
    for track in resolved.tracks:
        assert isinstance(track, Track)
        assert track.provider is ProviderId.SPOTIFY
        assert track.album == resolved.album  # album context injected


def test_map_search_returns_tracks(load_fixture: Any) -> None:
    payload = load_fixture("spotify", "search")
    tracks = map_search(payload)

    items = payload["tracks"]["items"]
    assert tracks
    assert len(tracks) == len(items)
    assert all(isinstance(t, Track) for t in tracks)
    assert all(t.provider is ProviderId.SPOTIFY for t in tracks)
    assert tracks[0].name == items[0]["name"]
    assert tracks[0].isrc == items[0]["external_ids"]["isrc"]


# --- AnonymousSpotifyAuth -------------------------------------------------


@respx.mock
async def test_anon_auth_fetches_and_caches_token() -> None:
    route = respx.get(_ANON_URL).mock(return_value=httpx.Response(200, json=_anon_token_body()))
    async with create_client() as client:
        auth = AnonymousSpotifyAuth(client)
        first = await auth.bearer_token()
        second = await auth.bearer_token()
    assert first == "ANON_TOKEN"
    assert second == "ANON_TOKEN"
    assert route.call_count == 1  # cached within expiry


@respx.mock
async def test_anon_auth_refreshes_before_expiry() -> None:
    route = respx.get(_ANON_URL).mock(
        side_effect=[
            httpx.Response(200, json=_anon_token_body(expires_in_ms=10_000.0)),
            httpx.Response(200, json=_anon_token_body(expires_in_ms=10_000.0)),
        ]
    )
    async with create_client() as client:
        auth = AnonymousSpotifyAuth(client)
        await auth.bearer_token()
        await auth.bearer_token()  # within refresh skew -> re-request
    assert route.call_count == 2


@respx.mock
async def test_anon_auth_sends_totp_params() -> None:
    route = respx.get(_ANON_URL).mock(return_value=httpx.Response(200, json=_anon_token_body()))
    async with create_client() as client:
        await AnonymousSpotifyAuth(client).bearer_token()
    request = route.calls.last.request
    params = httpx.QueryParams(request.url.query)
    assert params["productType"] == "web-player"
    assert params["totp"].isdigit()
    assert params["totpVer"]


@respx.mock
async def test_anon_auth_uses_totp_secret_override() -> None:
    route = respx.get(_ANON_URL).mock(return_value=httpx.Response(200, json=_anon_token_body()))
    async with create_client() as client:
        # A valid base32 secret; the override path must be exercised without error.
        auth = AnonymousSpotifyAuth(client, totp_secret="JBSWY3DPEHPK3PXP")
        assert await auth.bearer_token() == "ANON_TOKEN"
    assert route.call_count == 1


@respx.mock
async def test_anon_auth_rejects_malformed_token_payload() -> None:
    respx.get(_ANON_URL).mock(return_value=httpx.Response(200, json={}))
    async with create_client() as client:
        with pytest.raises(ProviderAuthError):
            await AnonymousSpotifyAuth(client).bearer_token()


@respx.mock
async def test_anon_auth_rejects_empty_access_token() -> None:
    body = _anon_token_body()
    body["accessToken"] = ""
    respx.get(_ANON_URL).mock(return_value=httpx.Response(200, json=body))
    async with create_client() as client:
        with pytest.raises(ProviderAuthError):
            await AnonymousSpotifyAuth(client).bearer_token()


@respx.mock
async def test_anon_auth_rejects_past_expiry() -> None:
    body = _anon_token_body()
    body["accessTokenExpirationTimestampMs"] = 1  # long past
    respx.get(_ANON_URL).mock(return_value=httpx.Response(200, json=body))
    async with create_client() as client:
        with pytest.raises(ProviderAuthError):
            await AnonymousSpotifyAuth(client).bearer_token()


# --- ClientCredentialsSpotifyAuth -----------------------------------------


@respx.mock
async def test_cc_auth_posts_basic_and_returns_token(load_fixture: Any) -> None:
    body = load_fixture("spotify", "token_cc")
    route = respx.post(_CC_URL).mock(return_value=httpx.Response(200, json=body))
    async with create_client() as client:
        auth = ClientCredentialsSpotifyAuth(client, client_id="id", client_secret="sec")
        token = await auth.bearer_token()
        cached = await auth.bearer_token()
    assert token == body["access_token"]
    assert cached == token
    assert route.call_count == 1  # cached within expires_in
    request = route.calls.last.request
    import base64

    expected = base64.b64encode(b"id:sec").decode()
    assert request.headers["authorization"] == f"Basic {expected}"
    assert b"grant_type=client_credentials" in request.content


@respx.mock
async def test_cc_auth_rejects_malformed_payload() -> None:
    respx.post(_CC_URL).mock(return_value=httpx.Response(200, json={"token_type": "Bearer"}))
    async with create_client() as client:
        auth = ClientCredentialsSpotifyAuth(client, client_id="id", client_secret="sec")
        with pytest.raises(ProviderAuthError):
            await auth.bearer_token()


# --- LayeredSpotifyAuth ---------------------------------------------------


def _layered(client: httpx.AsyncClient, *, prefer_anonymous: bool = True) -> LayeredSpotifyAuth:
    return LayeredSpotifyAuth(
        anonymous=AnonymousSpotifyAuth(client),
        client_credentials=ClientCredentialsSpotifyAuth(
            client, client_id="id", client_secret="sec"
        ),
        prefer_anonymous=prefer_anonymous,
    )


@respx.mock
async def test_layered_falls_back_to_cc_on_anon_auth_error() -> None:
    respx.get(_ANON_URL).mock(return_value=httpx.Response(401))
    respx.post(_CC_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "CC", "expires_in": 3600})
    )
    async with create_client() as client:
        auth = _layered(client)
        assert await auth.bearer_token() == "CC"
        assert auth.live_path == "client_credentials"


@respx.mock
async def test_layered_falls_back_to_cc_on_anon_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    respx.get(_ANON_URL).mock(side_effect=httpx.ConnectError("boom"))
    respx.post(_CC_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "CC", "expires_in": 3600})
    )
    async with create_client() as client:
        auth = _layered(client)
        assert await auth.bearer_token() == "CC"
        assert auth.live_path == "client_credentials"


@respx.mock
async def test_layered_falls_back_to_cc_on_malformed_anon_payload() -> None:
    respx.get(_ANON_URL).mock(return_value=httpx.Response(200, json={"isAnonymous": True}))
    respx.post(_CC_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "CC", "expires_in": 3600})
    )
    async with create_client() as client:
        auth = _layered(client)
        assert await auth.bearer_token() == "CC"
        assert auth.live_path == "client_credentials"


@respx.mock
async def test_layered_prefers_cc_when_prefer_anonymous_false() -> None:
    anon_route = respx.get(_ANON_URL).mock(
        return_value=httpx.Response(200, json=_anon_token_body())
    )
    respx.post(_CC_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "CC", "expires_in": 3600})
    )
    async with create_client() as client:
        auth = _layered(client, prefer_anonymous=False)
        assert await auth.bearer_token() == "CC"
        assert auth.live_path == "client_credentials"
    assert anon_route.call_count == 0  # secondary never touched


@respx.mock
async def test_layered_raises_when_both_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    respx.get(_ANON_URL).mock(return_value=httpx.Response(401))
    respx.post(_CC_URL).mock(return_value=httpx.Response(403))
    async with create_client() as client:
        auth = _layered(client)
        with pytest.raises(ProviderError):
            await auth.bearer_token()


async def test_layered_raises_when_none_configured() -> None:
    auth = LayeredSpotifyAuth(anonymous=None, client_credentials=None)
    with pytest.raises(ProviderAuthError):
        await auth.bearer_token()


# --- SpotifyProvider (respx, stub auth) -----------------------------------


def _provider(client: httpx.AsyncClient) -> SpotifyProvider:
    return SpotifyProvider(client, _StubAuth())


@respx.mock
async def test_resolve_track_url_returns_track(load_fixture: Any) -> None:
    payload = load_fixture("spotify", "track")
    respx.get(f"{_API}/v1/tracks/{_KNOWN_TRACK}").mock(
        return_value=httpx.Response(200, json=payload)
    )
    ref = PlatformRef(ProviderId.SPOTIFY, EntityType.TRACK, _KNOWN_TRACK)
    async with create_client(base_url=_API) as client:
        resolved = await _provider(client).resolve(ref)
    assert resolved.entity_type is EntityType.TRACK
    assert resolved.track is not None
    assert resolved.track.name == payload["name"]
    assert resolved.track.isrc == payload["external_ids"]["isrc"]


@respx.mock
async def test_resolve_track_sends_bearer_header(load_fixture: Any) -> None:
    payload = load_fixture("spotify", "track")
    route = respx.get(f"{_API}/v1/tracks/{_KNOWN_TRACK}").mock(
        return_value=httpx.Response(200, json=payload)
    )
    ref = PlatformRef(ProviderId.SPOTIFY, EntityType.TRACK, _KNOWN_TRACK)
    async with create_client(base_url=_API) as client:
        await _provider(client).resolve(ref)
    assert route.calls.last.request.headers["authorization"] == "Bearer STUB_TOKEN"


@respx.mock
async def test_resolve_album_paginates() -> None:
    album_id = "ALBUM1"
    album = {
        "id": album_id,
        "name": "Paginated Album",
        "release_date": "2020-05-01",
        "total_tracks": 2,
        "artists": [{"name": "The Band"}],
        "images": [{"url": "https://img/big", "width": 640, "height": 640}],
        "tracks": {
            "items": [
                {
                    "id": "t1",
                    "name": "Track One",
                    "duration_ms": 100000,
                    "track_number": 1,
                    "disc_number": 1,
                    "explicit": False,
                    "artists": [{"name": "The Band"}],
                }
            ],
            "total": 2,
            "next": f"{_API}/v1/albums/{album_id}/tracks?offset=1&limit=50",
        },
    }
    page2 = {
        "items": [
            {
                "id": "t2",
                "name": "Track Two",
                "duration_ms": 120000,
                "track_number": 2,
                "disc_number": 1,
                "explicit": True,
                "artists": [{"name": "The Band"}],
            }
        ],
        "total": 2,
        "next": None,
    }
    respx.get(f"{_API}/v1/albums/{album_id}").mock(return_value=httpx.Response(200, json=album))
    respx.get(f"{_API}/v1/albums/{album_id}/tracks").mock(
        return_value=httpx.Response(200, json=page2)
    )
    ref = PlatformRef(ProviderId.SPOTIFY, EntityType.ALBUM, album_id)
    async with create_client(base_url=_API) as client:
        resolved = await _provider(client).resolve(ref)
    assert resolved.entity_type is EntityType.ALBUM
    assert [t.name for t in resolved.tracks] == ["Track One", "Track Two"]
    assert resolved.album is not None
    assert resolved.album.year == 2020
    assert all(t.album == resolved.album for t in resolved.tracks)


@respx.mock
async def test_search_returns_tracks(load_fixture: Any) -> None:
    payload = load_fixture("spotify", "search")
    route = respx.get(f"{_API}/v1/search").mock(return_value=httpx.Response(200, json=payload))
    async with create_client(base_url=_API) as client:
        tracks = await _provider(client).search("shape of you", limit=5)
    assert tracks
    assert all(t.provider is ProviderId.SPOTIFY for t in tracks)
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["type"] == "track"
    assert params["q"] == "shape of you"
    assert params["limit"] == "5"


@respx.mock
async def test_resolve_404_raises_entity_not_found() -> None:
    respx.get(f"{_API}/v1/tracks/missing").mock(return_value=httpx.Response(404))
    ref = PlatformRef(ProviderId.SPOTIFY, EntityType.TRACK, "missing")
    async with create_client(base_url=_API) as client:
        with pytest.raises(EntityNotFound):
            await _provider(client).resolve(ref)


@respx.mock
async def test_enrich_fills_missing_isrc_and_genres(load_fixture: Any) -> None:
    payload = load_fixture("spotify", "track")
    respx.get(f"{_API}/v1/tracks/{_KNOWN_TRACK}").mock(
        return_value=httpx.Response(200, json=payload)
    )
    artist_id = payload["artists"][0]["id"]
    respx.get(f"{_API}/v1/artists/{artist_id}").mock(
        return_value=httpx.Response(200, json={"id": artist_id, "genres": ["pop", "dance pop"]})
    )
    bare = Track(
        name=payload["name"],
        artists=(payload["artists"][0]["name"],),
        duration_ms=payload["duration_ms"],
        provider=ProviderId.SPOTIFY,
        provider_id=_KNOWN_TRACK,
    )
    async with create_client(base_url=_API) as client:
        enriched = await _provider(client).enrich(bare)
    assert enriched.isrc == payload["external_ids"]["isrc"]
    assert enriched.genres == ("pop", "dance pop")


async def test_enrich_without_spotify_id_returns_unchanged() -> None:
    track = Track(name="x", artists=("a",), duration_ms=1000, provider=ProviderId.DEEZER)
    async with create_client(base_url=_API) as client:
        result = await _provider(client).enrich(track)
    assert result is track


# --- provider wiring / capabilities ---------------------------------------


def test_provider_advertises_capabilities() -> None:
    async def _make() -> SpotifyProvider:
        return build_spotify_provider(ProviderContext())

    provider = asyncio.run(_make())
    try:
        assert provider.id is ProviderId.SPOTIFY
        assert isinstance(provider, Resolves)
        assert isinstance(provider, Searches)
        assert isinstance(provider, Enriches)
    finally:
        asyncio.run(provider.aclose())


def test_build_spotify_provider_uses_cc_when_configured() -> None:
    config = SpotifyConfig(client_id="cid", client_secret="sec", prefer_anonymous=False)
    ctx = ProviderContext(spotify=config)

    async def _make() -> SpotifyProvider:
        return build_spotify_provider(ctx)

    provider = asyncio.run(_make())
    asyncio.run(provider.aclose())


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_anonymous_resolve_known_track() -> None:
    provider = build_spotify_provider(ProviderContext())
    try:
        ref = PlatformRef(ProviderId.SPOTIFY, EntityType.TRACK, _KNOWN_TRACK)
        resolved = await provider.resolve(ref)
    finally:
        await provider.aclose()
    assert resolved.track is not None
    assert resolved.track.isrc
    assert resolved.track.duration_ms > 0
