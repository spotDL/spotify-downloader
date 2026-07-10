"""Tests for the SoundCloud audio provider (scraper) (Task 10).

Every test is offline except the single ``@pytest.mark.network`` live search.
The pure mapper runs from the checked-in ``__sc_hydration`` blob fixture, and
all HTTP behaviour (search HTML page, track page) is mocked with ``respx``.

The mapping contract asserted here: SoundCloud ``duration`` is already in
**milliseconds** and is stored as-is (no ``*1000``); ``playback_count`` becomes
``popularity`` and ``permalink_url`` becomes the candidate url.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx
from spotdl_core.model import AudioCandidate, EntityType, ProviderId, Track
from spotdl_core.providers.audio.soundcloud import (
    SoundCloudProvider,
    _map_soundcloud_hydration,
    build_soundcloud_provider,
)
from spotdl_core.providers.base import ProvidesAudio, Resolves
from spotdl_core.providers.errors import EntityNotFound, ProviderUnavailable
from spotdl_core.providers.http import create_client
from spotdl_core.providers.registry import ProviderContext
from spotdl_core.providers.urls import PlatformRef

_QUERY_TRACK = Track(
    name="Get Lucky",
    artists=("Daft Punk",),
    duration_ms=369_000,
    provider=ProviderId.SPOTIFY,
    provider_id="x",
)


def _html_with_hydration(hydration: Any) -> str:
    """Wrap a hydration blob in a minimal SoundCloud-style HTML page."""
    blob = json.dumps(hydration)
    return (
        "<!DOCTYPE html><html><head></head><body>"
        "<script>window.__sc_hydration = " + blob + ";</script>"
        "</body></html>"
    )


# --- pure mapper ----------------------------------------------------------


def test_soundcloud_map_hydration_from_fixture(load_fixture: Any) -> None:
    hydration = load_fixture("soundcloud", "search")
    candidates = _map_soundcloud_hydration(hydration)
    assert candidates
    assert all(isinstance(c, AudioCandidate) for c in candidates)
    assert all(c.provider is ProviderId.SOUNDCLOUD for c in candidates)
    # the "user" collection entry (kind != track) is dropped
    assert len(candidates) == 2
    first = candidates[0]
    assert first.provider_id == "264032352"
    assert first.name == "Get Lucky (feat. Pharrell Williams)"
    assert first.artists == ("Daft Punk",)
    assert first.url == "https://soundcloud.com/daftpunkofficialmusic/get-lucky"
    assert first.popularity == 4_200_000
    # SoundCloud candidates carry no catalogue guarantee.
    assert first.verified is False


def test_soundcloud_duration_is_milliseconds_as_is(load_fixture: Any) -> None:
    hydration = load_fixture("soundcloud", "search")
    candidates = _map_soundcloud_hydration(hydration)
    # CONTRACT: SoundCloud ``duration`` is already in ms and must NOT be *1000.
    assert candidates[0].duration_ms == 224_896
    assert candidates[1].duration_ms == 369_000


def test_soundcloud_map_skips_items_without_id_or_title() -> None:
    hydration = [
        {
            "data": {
                "collection": [
                    {"kind": "track", "title": "no id"},
                    {"kind": "track", "id": 5},
                    {"kind": "track", "id": 7, "title": "keep", "user": {"username": "A"}},
                ]
            }
        },
    ]
    candidates = _map_soundcloud_hydration(hydration)
    assert [c.provider_id for c in candidates] == ["7"]


# --- provider (respx) -----------------------------------------------------


@respx.mock
async def test_soundcloud_search_scrapes_hydration(load_fixture: Any) -> None:
    hydration = load_fixture("soundcloud", "search")
    # Keyless: discovery runs first — the homepage carries no asset bundles, so
    # discovery yields nothing and the provider falls back to the page scrape.
    respx.get("https://soundcloud.com/").mock(
        return_value=httpx.Response(200, text="<html><body>no assets</body></html>")
    )
    route = respx.get("https://soundcloud.com/search/sounds").mock(
        return_value=httpx.Response(200, text=_html_with_hydration(hydration))
    )
    async with create_client() as client:
        candidates = await SoundCloudProvider(client).audio_candidates(_QUERY_TRACK, limit=5)
    assert [c.provider_id for c in candidates] == ["264032352", "264032999"]
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["q"] == "Daft Punk - Get Lucky"


@respx.mock
async def test_soundcloud_api_search_used_when_client_id_present() -> None:
    # api-v2 returns a `collection` payload; the same hydration mapper consumes it.
    body = {
        "collection": [
            {
                "id": 999,
                "kind": "track",
                "title": "Get Lucky (API)",
                "duration": 224_896,
                "permalink_url": "https://soundcloud.com/daftpunk/get-lucky-api",
                "playback_count": 7,
                "user": {"username": "Daft Punk"},
            }
        ]
    }
    route = respx.get("https://api-v2.soundcloud.com/search/tracks").mock(
        return_value=httpx.Response(200, json=body)
    )
    search_page = respx.get("https://soundcloud.com/search/sounds").mock(
        return_value=httpx.Response(200, text="<html></html>")
    )
    async with create_client() as client:
        provider = SoundCloudProvider(client, client_id="test-client-id")
        candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    # the api-v2 path is taken; the scrape page is never requested
    assert route.called
    assert not search_page.called
    assert [c.provider_id for c in candidates] == ["999"]
    assert candidates[0].duration_ms == 224_896
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["q"] == "Daft Punk - Get Lucky"
    assert params["client_id"] == "test-client-id"


@respx.mock
async def test_soundcloud_resolve_track_from_sound_hydratable() -> None:
    hydration = [
        {
            "hydratable": "sound",
            "data": {
                "id": 111,
                "kind": "track",
                "title": "Some Song",
                "duration": 200_000,
                "permalink_url": "https://soundcloud.com/artist/some-song",
                "playback_count": 42,
                "user": {"username": "The Artist"},
            },
        },
    ]
    respx.get("https://soundcloud.com/artist/some-song").mock(
        return_value=httpx.Response(200, text=_html_with_hydration(hydration))
    )
    ref = PlatformRef(ProviderId.SOUNDCLOUD, EntityType.TRACK, "artist/some-song")
    async with create_client() as client:
        resolved = await SoundCloudProvider(client).resolve(ref)
    assert resolved.entity_type is EntityType.TRACK
    assert resolved.track is not None
    assert resolved.track.name == "Some Song"
    assert resolved.track.artists == ("The Artist",)
    # ms as-is on the resolve path too
    assert resolved.track.duration_ms == 200_000


@respx.mock
async def test_soundcloud_resolve_missing_sound_raises_not_found() -> None:
    respx.get("https://soundcloud.com/artist/missing").mock(
        return_value=httpx.Response(200, text=_html_with_hydration([{"hydratable": "user"}]))
    )
    ref = PlatformRef(ProviderId.SOUNDCLOUD, EntityType.TRACK, "artist/missing")
    async with create_client() as client:
        with pytest.raises(EntityNotFound):
            await SoundCloudProvider(client).resolve(ref)


@respx.mock
async def test_soundcloud_http_error_raises_provider_unavailable() -> None:
    # Discovery finds no id (homepage carries no assets) → scrape fallback; the
    # scrape page's 503 is a transport failure and raises.
    respx.get("https://soundcloud.com/").mock(
        return_value=httpx.Response(200, text="<html></html>")
    )
    respx.get("https://soundcloud.com/search/sounds").mock(return_value=httpx.Response(503))
    async with create_client() as client:
        with pytest.raises(ProviderUnavailable):
            await SoundCloudProvider(client).audio_candidates(_QUERY_TRACK)


# --- client_id discovery (respx) ------------------------------------------


@respx.mock
async def test_soundcloud_discovers_client_id_then_uses_api_v2() -> None:
    # Keyless: scrape the homepage → asset bundle → 32-char client_id, then search
    # via api-v2 with the discovered id (the scrape page is never touched).
    asset_url = "https://a-v2.sndcdn.com/assets/50-abcdef0.js"
    home = respx.get("https://soundcloud.com/").mock(
        return_value=httpx.Response(
            200, text=f'<html><head><script crossorigin src="{asset_url}"></script></head></html>'
        )
    )
    client_id = "a" * 32
    asset = respx.get(asset_url).mock(
        return_value=httpx.Response(200, text=f'window.foo={{client_id:"{client_id}"}};')
    )
    body = {
        "collection": [
            {
                "id": 42,
                "kind": "track",
                "title": "Master of Puppets",
                "duration": 515_000,
                "permalink_url": "https://soundcloud.com/metallica/master-of-puppets",
                "playback_count": 9,
                "user": {"username": "Metallica"},
            }
        ]
    }
    api = respx.get("https://api-v2.soundcloud.com/search/tracks").mock(
        return_value=httpx.Response(200, json=body)
    )
    scrape = respx.get("https://soundcloud.com/search/sounds").mock(
        return_value=httpx.Response(200, text="<html></html>")
    )
    async with create_client() as client:
        provider = SoundCloudProvider(client)  # no operator client_id
        candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    assert home.called and asset.called and api.called
    assert not scrape.called  # api-v2 path taken, not the hydration scrape
    assert [c.provider_id for c in candidates] == ["42"]
    params = httpx.QueryParams(api.calls.last.request.url.query)
    assert params["client_id"] == client_id


@respx.mock
async def test_soundcloud_configured_client_id_skips_discovery() -> None:
    # An operator-provided id is authoritative: discovery must never be attempted.
    home = respx.get("https://soundcloud.com/").mock(
        return_value=httpx.Response(200, text="<html></html>")
    )
    body = {
        "collection": [
            {
                "id": 1,
                "kind": "track",
                "title": "T",
                "duration": 1_000,
                "permalink_url": "https://soundcloud.com/a/t",
                "user": {"username": "A"},
            }
        ]
    }
    api = respx.get("https://api-v2.soundcloud.com/search/tracks").mock(
        return_value=httpx.Response(200, json=body)
    )
    async with create_client() as client:
        provider = SoundCloudProvider(client, client_id="operator-id")
        candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    assert api.called
    assert not home.called  # discovery skipped entirely
    assert [c.provider_id for c in candidates] == ["1"]


@respx.mock
async def test_soundcloud_rediscovers_client_id_on_401() -> None:
    # A rotated id: api-v2 rejects the first (stale) id with 401 → the provider
    # re-discovers ONCE and retries with the fresh id.
    asset_url = "https://a-v2.sndcdn.com/assets/app.js"
    stale, fresh = "s" * 32, "f" * 32
    respx.get("https://soundcloud.com/").mock(
        return_value=httpx.Response(200, text=f'<script crossorigin src="{asset_url}"></script>')
    )
    ids = iter([stale, fresh])
    respx.get(asset_url).mock(
        side_effect=lambda request: httpx.Response(200, text=f'client_id="{next(ids)}"')
    )
    body = {
        "collection": [
            {
                "id": 7,
                "kind": "track",
                "title": "T",
                "duration": 1_000,
                "permalink_url": "https://soundcloud.com/a/t",
                "user": {"username": "A"},
            }
        ]
    }

    def _api(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("client_id") == stale:
            return httpx.Response(401)
        return httpx.Response(200, json=body)

    api = respx.get("https://api-v2.soundcloud.com/search/tracks").mock(side_effect=_api)
    async with create_client() as client:
        provider = SoundCloudProvider(client)
        candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    assert [c.provider_id for c in candidates] == ["7"]
    assert len(api.calls) == 2  # stale (401) then fresh (200)


@respx.mock
async def test_soundcloud_api_transport_error_raises_provider_unavailable() -> None:
    # A non-auth api-v2 failure (503, not 401/403) is a transport failure → raise.
    asset_url = "https://a-v2.sndcdn.com/assets/app.js"
    respx.get("https://soundcloud.com/").mock(
        return_value=httpx.Response(200, text=f'<script crossorigin src="{asset_url}"></script>')
    )
    respx.get(asset_url).mock(return_value=httpx.Response(200, text=f'client_id="{"c" * 32}"'))
    respx.get("https://api-v2.soundcloud.com/search/tracks").mock(return_value=httpx.Response(503))
    async with create_client() as client:
        with pytest.raises(ProviderUnavailable):
            await SoundCloudProvider(client).audio_candidates(_QUERY_TRACK)


# --- wiring / capabilities ------------------------------------------------


async def test_soundcloud_advertises_capabilities() -> None:
    provider = build_soundcloud_provider(ProviderContext())
    try:
        assert provider.id is ProviderId.SOUNDCLOUD
        assert isinstance(provider, ProvidesAudio)
        assert isinstance(provider, Resolves)
    finally:
        await provider.aclose()


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_soundcloud_search() -> None:
    provider = build_soundcloud_provider(ProviderContext())
    try:
        candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    finally:
        await provider.aclose()
    assert candidates
    assert all(c.provider is ProviderId.SOUNDCLOUD for c in candidates)
