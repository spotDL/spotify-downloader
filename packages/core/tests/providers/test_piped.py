"""Tests for the Piped audio provider (rotating instances) (Task 10).

Every test is offline except the single ``@pytest.mark.network`` live search.
The pure mapper runs from a checked-in Piped ``/search`` fixture; HTTP behaviour
(healthcheck + search, plus instance failover) is mocked with ``respx``.

Two behaviours are contract: Piped ``duration`` is in **seconds** and stored as
milliseconds (``*1000``); when **all** configured instances fail their
health/search, the provider raises :class:`ProviderUnavailable`.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from spotdl_core.model import AudioCandidate, ProviderId, Track
from spotdl_core.providers.audio.piped import (
    PipedProvider,
    _map_piped_search,
    build_piped_provider,
)
from spotdl_core.providers.base import ProvidesAudio
from spotdl_core.providers.errors import ProviderUnavailable
from spotdl_core.providers.http import create_client
from spotdl_core.providers.registry import DEFAULT_PIPED_INSTANCES, ProviderContext

_INST_A = "https://inst-a.example"
_INST_B = "https://inst-b.example"

_QUERY_TRACK = Track(
    name="Get Lucky",
    artists=("Daft Punk",),
    duration_ms=369_000,
    provider=ProviderId.SPOTIFY,
    provider_id="x",
)


# --- pure mapper ----------------------------------------------------------


def test_piped_map_search_from_fixture(load_fixture: Any) -> None:
    payload = load_fixture("piped", "search")
    candidates = _map_piped_search(payload["items"])
    assert candidates
    assert all(isinstance(c, AudioCandidate) for c in candidates)
    assert all(c.provider is ProviderId.PIPED for c in candidates)
    # the non-stream "channel" item is dropped
    assert len(candidates) == 2
    first = candidates[0]
    assert first.provider_id == "5NV6Rdv1a3I"
    assert first.name.startswith("Daft Punk - Get Lucky")
    assert first.artists == ("Daft Punk",)
    # canonical YouTube watch url so the download engine can consume it
    assert first.url == "https://www.youtube.com/watch?v=5NV6Rdv1a3I"
    assert first.popularity == 168_000_000
    # uploaderVerified is surfaced as verified
    assert first.verified is True
    assert candidates[1].verified is False


def test_piped_duration_seconds_to_ms(load_fixture: Any) -> None:
    payload = load_fixture("piped", "search")
    candidates = _map_piped_search(payload["items"])
    # CONTRACT: Piped duration is seconds; the candidate stores milliseconds.
    assert candidates[0].duration_ms == 369 * 1000


def test_piped_map_skips_items_without_video_id() -> None:
    items = [
        {"type": "stream", "title": "no url"},
        {
            "type": "stream",
            "url": "/watch?v=abcABC12345",
            "title": "keep",
            "uploaderName": "A",
            "duration": 10,
        },
    ]
    candidates = _map_piped_search(items)
    assert [c.provider_id for c in candidates] == ["abcABC12345"]


# --- provider (respx) -----------------------------------------------------


@respx.mock
async def test_piped_search_uses_first_healthy_instance(load_fixture: Any) -> None:
    payload = load_fixture("piped", "search")
    health = respx.get(f"{_INST_A}/healthcheck").mock(return_value=httpx.Response(200))
    search = respx.get(f"{_INST_A}/search").mock(return_value=httpx.Response(200, json=payload))
    async with create_client() as client:
        provider = PipedProvider(client, instances=(_INST_A, _INST_B))
        candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    assert [c.provider_id for c in candidates] == ["5NV6Rdv1a3I", "aA_2s_8lE1w"]
    assert health.called
    params = httpx.QueryParams(search.calls.last.request.url.query)
    assert params["q"] == "Daft Punk - Get Lucky"
    assert params["filter"] == "videos"


@respx.mock
async def test_piped_falls_over_to_next_instance(load_fixture: Any) -> None:
    payload = load_fixture("piped", "search")
    # First instance is unhealthy (503 on healthcheck); second is healthy.
    a_health = respx.get(f"{_INST_A}/healthcheck").mock(return_value=httpx.Response(503))
    b_health = respx.get(f"{_INST_B}/healthcheck").mock(return_value=httpx.Response(200))
    b_search = respx.get(f"{_INST_B}/search").mock(return_value=httpx.Response(200, json=payload))
    async with create_client() as client:
        provider = PipedProvider(client, instances=(_INST_A, _INST_B))
        candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    assert a_health.called
    assert b_health.called
    assert b_search.called
    assert candidates[0].provider_id == "5NV6Rdv1a3I"


@respx.mock
async def test_piped_all_instances_down_raises_provider_unavailable() -> None:
    respx.get(f"{_INST_A}/healthcheck").mock(return_value=httpx.Response(503))
    respx.get(f"{_INST_B}/healthcheck").mock(return_value=httpx.Response(502))
    async with create_client() as client:
        provider = PipedProvider(client, instances=(_INST_A, _INST_B))
        with pytest.raises(ProviderUnavailable) as excinfo:
            await provider.audio_candidates(_QUERY_TRACK)
    assert excinfo.value.provider is ProviderId.PIPED


@respx.mock
async def test_piped_search_failure_falls_over(load_fixture: Any) -> None:
    payload = load_fixture("piped", "search")
    # First instance is healthy but its search fails; provider must try the next.
    respx.get(f"{_INST_A}/healthcheck").mock(return_value=httpx.Response(200))
    respx.get(f"{_INST_A}/search").mock(return_value=httpx.Response(500))
    respx.get(f"{_INST_B}/healthcheck").mock(return_value=httpx.Response(200))
    respx.get(f"{_INST_B}/search").mock(return_value=httpx.Response(200, json=payload))
    async with create_client() as client:
        provider = PipedProvider(client, instances=(_INST_A, _INST_B))
        candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    assert candidates[0].provider_id == "5NV6Rdv1a3I"


@respx.mock
async def test_piped_connect_error_falls_over(load_fixture: Any) -> None:
    payload = load_fixture("piped", "search")
    respx.get(f"{_INST_A}/healthcheck").mock(side_effect=httpx.ConnectError("boom"))
    respx.get(f"{_INST_B}/healthcheck").mock(return_value=httpx.Response(200))
    respx.get(f"{_INST_B}/search").mock(return_value=httpx.Response(200, json=payload))
    async with create_client() as client:
        provider = PipedProvider(client, instances=(_INST_A, _INST_B))
        candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    assert candidates[0].provider_id == "5NV6Rdv1a3I"


# --- wiring / capabilities ------------------------------------------------


async def test_piped_advertises_capabilities() -> None:
    provider = build_piped_provider(ProviderContext())
    try:
        assert provider.id is ProviderId.PIPED
        assert isinstance(provider, ProvidesAudio)
    finally:
        await provider.aclose()


def test_piped_default_instances_are_used() -> None:
    provider = build_piped_provider(ProviderContext())
    assert provider._instances == DEFAULT_PIPED_INSTANCES


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_piped_search() -> None:
    provider = build_piped_provider(ProviderContext())
    try:
        candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    finally:
        await provider.aclose()
    assert candidates
    assert all(c.provider is ProviderId.PIPED for c in candidates)
    assert all(c.duration_ms and c.duration_ms > 0 for c in candidates)
