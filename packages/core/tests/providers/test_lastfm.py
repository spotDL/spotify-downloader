"""Tests for the Last.fm metadata provider (Phase 4).

Offline: the pure mappers run on inline JSON and every HTTP call is mocked with
``respx``. Covers the two API endpoints (``artist.getInfo`` / ``track.getInfo``),
the bio HTML/"Read more" stripping, tag→genre flattening, the not-found body
(``{"error": 6}`` → ``None``, never a 404), and the key gate (absent
``SPOTDL_LASTFM_API_KEY`` → the provider is not constructed by the registry).
"""

from __future__ import annotations

import httpx
import pytest
import respx
from spotdl_core.model import ProviderId
from spotdl_core.providers.errors import ProviderUnavailable
from spotdl_core.providers.http import create_client
from spotdl_core.providers.metadata.lastfm import (
    LastfmProvider,
    build_lastfm_provider,
    clean_bio,
    map_artist_info,
    map_track_info,
)
from spotdl_core.providers.registry import (
    LastfmConfig,
    ProviderContext,
    build_default_registry,
)

_API = "https://ws.audioscrobbler.com/2.0/"

_ARTIST_BODY = {
    "artist": {
        "name": "Adele",
        "stats": {"listeners": "5123456", "playcount": "88123456"},
        "bio": {
            "summary": "Adele is an English singer-songwriter. "
            '<a href="https://last.fm/music/Adele">Read more on Last.fm</a>'
        },
        "tags": {"tag": [{"name": "soul"}, {"name": "pop"}, {"name": "british"}]},
    }
}

_TRACK_BODY = {
    "track": {
        "name": "Hello",
        "artist": {"name": "Adele"},
        "listeners": "1234567",
        "playcount": "9876543",
        "toptags": {"tag": [{"name": "pop"}, {"name": "soul"}]},
    }
}


def _provider(client: httpx.AsyncClient) -> LastfmProvider:
    return LastfmProvider(client, api_key="test-key")


# --- pure mappers ---------------------------------------------------------


def test_clean_bio_strips_tags_and_read_more() -> None:
    assert clean_bio('Foo <b>bar</b>. <a href="x">Read more on Last.fm</a>') == "Foo bar."
    assert clean_bio(None) is None
    assert clean_bio("<a>Read more</a>") is None


def test_map_artist_info_extracts_stats_bio_tags() -> None:
    info = map_artist_info(_ARTIST_BODY)
    assert info is not None
    assert info.name == "Adele"
    assert info.listeners == 5_123_456
    assert info.playcount == 88_123_456
    assert info.bio == "Adele is an English singer-songwriter."
    assert info.genres == ("soul", "pop", "british")


def test_map_track_info_extracts_stats_and_tags() -> None:
    info = map_track_info(_TRACK_BODY)
    assert info is not None
    assert info.name == "Hello"
    assert info.artist == "Adele"
    assert info.listeners == 1_234_567
    assert info.playcount == 9_876_543
    assert info.genres == ("pop", "soul")


def test_map_artist_info_error_body_is_none() -> None:
    # Last.fm answers an unknown artist with a 200 body carrying an error code.
    assert map_artist_info({"error": 6, "message": "artist not found"}) is None


def test_map_track_info_error_body_is_none() -> None:
    assert map_track_info({"error": 6, "message": "Track not found"}) is None


# --- HTTP ------------------------------------------------------------------


@respx.mock
async def test_artist_info_calls_endpoint_with_key() -> None:
    route = respx.get(_API).mock(return_value=httpx.Response(200, json=_ARTIST_BODY))
    async with create_client(base_url=_API) as client:
        info = await _provider(client).artist_info("Adele")
    assert info is not None and info.listeners == 5_123_456
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["method"] == "artist.getInfo"
    assert params["artist"] == "Adele"
    assert params["api_key"] == "test-key"
    assert params["format"] == "json"


@respx.mock
async def test_track_info_calls_endpoint() -> None:
    route = respx.get(_API).mock(return_value=httpx.Response(200, json=_TRACK_BODY))
    async with create_client(base_url=_API) as client:
        info = await _provider(client).track_info("Adele", "Hello")
    assert info is not None and info.playcount == 9_876_543
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["method"] == "track.getInfo"
    assert params["artist"] == "Adele"
    assert params["track"] == "Hello"


@respx.mock
async def test_artist_info_not_found_returns_none() -> None:
    respx.get(_API).mock(return_value=httpx.Response(200, json={"error": 6, "message": "no"}))
    async with create_client(base_url=_API) as client:
        assert await _provider(client).artist_info("Nobody") is None


# --- registry gate ---------------------------------------------------------


def test_build_requires_api_key() -> None:
    with pytest.raises(ProviderUnavailable):
        build_lastfm_provider(ProviderContext())


def test_build_with_key_succeeds() -> None:
    provider = build_lastfm_provider(ProviderContext(lastfm=LastfmConfig(api_key="k")))
    assert provider.id is ProviderId.LASTFM


def test_registry_omits_lastfm_without_key() -> None:
    # Registered (appears in ``registered``) but construction fails without a key,
    # so ``get`` reports it unavailable — a silently skipped source, never an error.
    reg = build_default_registry(ProviderContext())
    assert ProviderId.LASTFM in reg.registered
    with pytest.raises(ProviderUnavailable):
        reg.get(ProviderId.LASTFM)


def test_registry_builds_lastfm_with_key() -> None:
    reg = build_default_registry(ProviderContext(lastfm=LastfmConfig(api_key="k")))
    assert isinstance(reg.get(ProviderId.LASTFM), LastfmProvider)
