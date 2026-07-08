"""Tests for the LRCLIB lyrics provider (Task 11).

LRCLIB exposes an open JSON API, so this provider talks to it directly with
``httpx`` (no scraping, no extra dependency). Every test is offline except the
single ``@pytest.mark.network`` live lookup: the pure parser runs from a
checked-in JSON fixture and HTTP behaviour is mocked with ``respx``.

Fixture lyric bodies are short SYNTHETIC placeholder text -- never real song
lyrics.

Contract asserted here: ``syncedLyrics`` is preferred over ``plainLyrics``
(SYNCED vs PLAIN), duration is sent in **seconds**, and a 404 (with no search
hit) yields ``None`` rather than raising.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from spotdl_core.model import AlbumRef, LyricsKind, ProviderId, Track
from spotdl_core.providers.base import ProvidesLyrics
from spotdl_core.providers.http import create_client
from spotdl_core.providers.lyrics.lrclib import (
    LrclibProvider,
    _parse_lrclib,
    build_lrclib_provider,
)
from spotdl_core.providers.registry import ProviderContext, build_default_registry

_GET_URL = "https://lrclib.net/api/get"
_SEARCH_URL = "https://lrclib.net/api/search"

_TRACK = Track(
    name="Placeholder Song",
    artists=("Placeholder Artist",),
    duration_ms=180_000,
    album=AlbumRef(name="Placeholder Album"),
    provider=ProviderId.SPOTIFY,
    provider_id="x",
)


# --- pure parser ----------------------------------------------------------


def test_parse_lrclib_prefers_synced(load_fixture: Any) -> None:
    payload = load_fixture("lrclib", "get")
    lyrics = _parse_lrclib(payload)
    assert lyrics is not None
    # CONTRACT: synced lyrics are preferred over plain when both are present.
    assert lyrics.kind is LyricsKind.SYNCED
    assert lyrics.source is ProviderId.LRCLIB
    assert "[00:10.00]" in lyrics.text
    assert "Placeholder verse one" in lyrics.text


def test_parse_lrclib_falls_back_to_plain(load_fixture: Any) -> None:
    payload = dict(load_fixture("lrclib", "get"))
    payload["syncedLyrics"] = None
    lyrics = _parse_lrclib(payload)
    assert lyrics is not None
    assert lyrics.kind is LyricsKind.PLAIN
    assert "Placeholder verse one" in lyrics.text
    assert "[00:10.00]" not in lyrics.text


def test_parse_lrclib_empty_returns_none() -> None:
    assert _parse_lrclib({}) is None
    assert _parse_lrclib({"syncedLyrics": "", "plainLyrics": ""}) is None
    assert _parse_lrclib({"instrumental": True, "plainLyrics": None}) is None


# --- provider (respx) -----------------------------------------------------


@respx.mock
async def test_lyrics_returns_synced_from_get(load_fixture: Any) -> None:
    payload = load_fixture("lrclib", "get")
    route = respx.get(_GET_URL).mock(return_value=httpx.Response(200, json=payload))
    async with create_client() as client:
        lyrics = await LrclibProvider(client).lyrics(_TRACK)
    assert lyrics is not None
    assert lyrics.kind is LyricsKind.SYNCED
    params = route.calls.last.request.url.params
    # CONTRACT: duration is sent in whole seconds (duration_ms // 1000).
    assert params["duration"] == "180"
    assert params["artist_name"] == "Placeholder Artist"
    assert params["track_name"] == "Placeholder Song"
    assert params["album_name"] == "Placeholder Album"


@respx.mock
async def test_lyrics_falls_back_to_search_on_404(load_fixture: Any) -> None:
    payload = load_fixture("lrclib", "get")
    respx.get(_GET_URL).mock(return_value=httpx.Response(404))
    search_route = respx.get(_SEARCH_URL).mock(return_value=httpx.Response(200, json=[payload]))
    async with create_client() as client:
        lyrics = await LrclibProvider(client).lyrics(_TRACK)
    assert lyrics is not None
    assert lyrics.kind is LyricsKind.SYNCED
    assert search_route.called


@respx.mock
async def test_lyrics_returns_none_when_nothing_found() -> None:
    respx.get(_GET_URL).mock(return_value=httpx.Response(404))
    respx.get(_SEARCH_URL).mock(return_value=httpx.Response(200, json=[]))
    async with create_client() as client:
        assert await LrclibProvider(client).lyrics(_TRACK) is None


@respx.mock
async def test_lyrics_returns_none_on_search_404() -> None:
    respx.get(_GET_URL).mock(return_value=httpx.Response(404))
    respx.get(_SEARCH_URL).mock(return_value=httpx.Response(404))
    async with create_client() as client:
        assert await LrclibProvider(client).lyrics(_TRACK) is None


# --- wiring / capabilities ------------------------------------------------


async def test_lrclib_advertises_capabilities() -> None:
    provider = build_lrclib_provider(ProviderContext())
    try:
        assert provider.id is ProviderId.LRCLIB
        assert isinstance(provider, ProvidesLyrics)
    finally:
        await provider.aclose()


def test_lrclib_registered_in_default_registry() -> None:
    reg = build_default_registry(ProviderContext())
    assert ProviderId.LRCLIB in reg.registered


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_lrclib_lookup() -> None:
    provider = build_lrclib_provider(ProviderContext())
    try:
        lyrics = await provider.lyrics(
            Track(
                name="Bohemian Rhapsody",
                artists=("Queen",),
                duration_ms=354_000,
                album=AlbumRef(name="A Night at the Opera"),
                provider=ProviderId.SPOTIFY,
                provider_id="x",
            )
        )
    finally:
        await provider.aclose()
    assert lyrics is None or lyrics.source is ProviderId.LRCLIB
