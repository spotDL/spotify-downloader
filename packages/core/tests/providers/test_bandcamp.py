"""Tests for the Bandcamp audio provider (scraper) (Task 10).

Every test is offline except the single ``@pytest.mark.network`` live search.
The search mapper runs from a checked-in HTML fixture and the track-detail
mapper from a checked-in ``TralbumData`` JSON blob; HTTP behaviour is mocked
with ``respx``.

The mapping contract asserted here: Bandcamp ``trackinfo[0].duration`` is in
**seconds** and is converted to milliseconds (``*1000``); the cover art is
``https://f4.bcbits.com/img/a{art_id}_10.jpg``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from spotdl_core.model import AudioCandidate, EntityType, ProviderId, Track
from spotdl_core.providers.audio.bandcamp import (
    _SEARCH_URL,
    BandcampProvider,
    _map_bandcamp_search,
    _map_bandcamp_tralbum,
    build_bandcamp_provider,
)
from spotdl_core.providers.base import ProvidesAudio, Resolves
from spotdl_core.providers.errors import EntityNotFound, ProviderUnavailable
from spotdl_core.providers.http import create_client
from spotdl_core.providers.registry import ProviderContext
from spotdl_core.providers.urls import PlatformRef

_FIXTURES = Path(__file__).parent / "fixtures"

_QUERY_TRACK = Track(
    name="Daddy's Car",
    artists=("Children Of Zeus",),
    duration_ms=245_000,
    provider=ProviderId.SPOTIFY,
    provider_id="x",
)

_TRACK_URL = "https://childrenofzeus.bandcamp.com/track/daddys-car"


def _search_html() -> str:
    return (_FIXTURES / "bandcamp" / "search.html").read_text(encoding="utf-8")


# --- pure mappers ---------------------------------------------------------


def test_bandcamp_map_search_parses_track_results() -> None:
    candidates = _map_bandcamp_search(_search_html())
    assert candidates
    assert all(isinstance(c, AudioCandidate) for c in candidates)
    assert all(c.provider is ProviderId.BANDCAMP for c in candidates)
    # only the two TRACK results are returned; the ALBUM result is dropped
    assert len(candidates) == 2
    first = candidates[0]
    assert first.name == "Daddy's Car"
    assert first.artists == ("Children Of Zeus",)
    assert first.url == "https://childrenofzeus.bandcamp.com/track/daddys-car"
    # numeric id parsed from the ``data-search`` blob
    assert first.provider_id == "3164368466"
    # search results have no duration
    assert first.duration_ms is None
    # album parsed from a "from <album> by <artist>" subhead is retained
    assert first.album == "Travel Light"
    # subhead with only "by <artist>" still parses the artist and leaves album unset
    assert candidates[1].artists == ("Another Band",)
    assert candidates[1].album is None


def test_bandcamp_map_tralbum_from_fixture(load_fixture: Any) -> None:
    data = load_fixture("bandcamp", "tralbum")
    track = _map_bandcamp_tralbum(data, _TRACK_URL)
    assert isinstance(track, Track)
    assert track.name == "Daddy's Car"
    assert track.artists == ("Children Of Zeus",)
    assert track.provider is ProviderId.BANDCAMP
    assert track.provider_id == "3164368466"
    assert track.album is not None
    assert track.album.name == "Travel Light"
    # CONTRACT: cover art url derived from art_id
    assert track.album.cover_url == "https://f4.bcbits.com/img/a1178591453_10.jpg"


def test_bandcamp_duration_seconds_to_ms(load_fixture: Any) -> None:
    data = load_fixture("bandcamp", "tralbum")
    track = _map_bandcamp_tralbum(data, _TRACK_URL)
    # CONTRACT: Bandcamp duration is seconds; the model stores milliseconds.
    assert track.duration_ms == int(round(245.36 * 1000))


# --- provider (respx) -----------------------------------------------------


@respx.mock
async def test_bandcamp_search_scrapes_results() -> None:
    route = respx.get("https://bandcamp.com/search").mock(
        return_value=httpx.Response(200, text=_search_html())
    )
    async with create_client() as client:
        candidates = await BandcampProvider(client).audio_candidates(_QUERY_TRACK, limit=5)
    assert [c.provider_id for c in candidates] == ["3164368466", "987654321"]
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["q"] == "Children Of Zeus - Daddy's Car"
    assert params["item_type"] == "t"


@respx.mock
async def test_bandcamp_resolve_track_from_tralbum(load_fixture: Any) -> None:
    data = load_fixture("bandcamp", "tralbum")
    html = "<html><body><script>var TralbumData = " + json.dumps(data) + ";</script></body></html>"
    respx.get(_TRACK_URL).mock(return_value=httpx.Response(200, text=html))
    ref = PlatformRef(
        ProviderId.BANDCAMP, EntityType.TRACK, "childrenofzeus/track/daddys-car", url=_TRACK_URL
    )
    async with create_client() as client:
        resolved = await BandcampProvider(client).resolve(ref)
    assert resolved.entity_type is EntityType.TRACK
    assert resolved.track is not None
    assert resolved.track.name == "Daddy's Car"
    assert resolved.track.duration_ms == int(round(245.36 * 1000))


@respx.mock
async def test_bandcamp_resolve_missing_tralbum_raises_not_found() -> None:
    respx.get(_TRACK_URL).mock(
        return_value=httpx.Response(200, text="<html><body>no data</body></html>")
    )
    ref = PlatformRef(
        ProviderId.BANDCAMP, EntityType.TRACK, "childrenofzeus/track/daddys-car", url=_TRACK_URL
    )
    async with create_client() as client:
        with pytest.raises(EntityNotFound):
            await BandcampProvider(client).resolve(ref)


@respx.mock
async def test_bandcamp_http_error_raises_provider_unavailable() -> None:
    respx.get("https://bandcamp.com/search").mock(return_value=httpx.Response(500))
    async with create_client() as client:
        with pytest.raises(ProviderUnavailable):
            await BandcampProvider(client).audio_candidates(_QUERY_TRACK)


# --- wiring / capabilities ------------------------------------------------


async def test_bandcamp_advertises_capabilities() -> None:
    provider = build_bandcamp_provider(ProviderContext())
    try:
        assert provider.id is ProviderId.BANDCAMP
        assert isinstance(provider, ProvidesAudio)
        assert isinstance(provider, Resolves)
    finally:
        await provider.aclose()


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_bandcamp_search() -> None:
    provider = build_bandcamp_provider(ProviderContext())
    try:
        candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    finally:
        await provider.aclose()
    assert all(c.provider is ProviderId.BANDCAMP for c in candidates)


@respx.mock
async def test_client_challenge_page_is_an_honest_degradation() -> None:
    """Bandcamp's anti-bot page (HTTP 200) must raise, not read as 'no matches'.

    Regression (found live): the "Client Challenge" shell parses to zero results,
    so Bandcamp silently contributed nothing while looking healthy.
    """
    challenge = "<!DOCTYPE html><html><head><title>Client Challenge</title></head></html>"
    respx.get(f"{_SEARCH_URL}").mock(return_value=httpx.Response(200, text=challenge))
    provider = build_bandcamp_provider(ProviderContext())
    track = Track(name="Sweden", artists=("C418",), duration_ms=210_000)
    try:
        with pytest.raises(ProviderUnavailable):
            await provider.audio_candidates(track)
    finally:
        await provider.aclose()
