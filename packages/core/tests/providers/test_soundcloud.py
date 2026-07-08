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
    route = respx.get("https://soundcloud.com/search/sounds").mock(
        return_value=httpx.Response(200, text=_html_with_hydration(hydration))
    )
    async with create_client() as client:
        candidates = await SoundCloudProvider(client).audio_candidates(_QUERY_TRACK, limit=5)
    assert [c.provider_id for c in candidates] == ["264032352", "264032999"]
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["q"] == "Daft Punk - Get Lucky"


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
    respx.get("https://soundcloud.com/search/sounds").mock(return_value=httpx.Response(503))
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
