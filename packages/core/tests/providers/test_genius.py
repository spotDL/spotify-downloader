"""Tests for the Genius lyrics provider (Task 11).

Genius needs an API token: search hits come from ``api.genius.com`` (JSON) and
the lyrics are scraped from the result's ``genius.com`` HTML page. Every test is
offline except the single ``@pytest.mark.network`` live lookup; the pure
extractor runs from a checked-in HTML fixture and HTTP behaviour is mocked with
``respx``.

Fixture lyric bodies are short SYNTHETIC placeholder text -- never real song
lyrics.

Contract asserted here: a Genius provider built without a token is
``ProviderUnavailable`` (so the registry omits it), and a successful lookup
returns ``PLAIN`` lyrics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from spotdl_core.model import LyricsKind, ProviderId, Track
from spotdl_core.providers.base import ProvidesLyrics
from spotdl_core.providers.errors import ProviderUnavailable
from spotdl_core.providers.lyrics.genius import (
    _extract_genius_lyrics,
    build_genius_provider,
)
from spotdl_core.providers.registry import ProviderContext, build_default_registry

_FIXTURES = Path(__file__).parent / "fixtures"
_SEARCH_URL = "https://api.genius.com/search"
_PAGE_URL = "https://genius.com/placeholder-artist-placeholder-song-lyrics"

_TRACK = Track(
    name="Placeholder Song",
    artists=("Placeholder Artist",),
    duration_ms=180_000,
    provider=ProviderId.SPOTIFY,
    provider_id="x",
)


def _song_page() -> str:
    return (_FIXTURES / "genius" / "song_page.html").read_text(encoding="utf-8")


# --- pure extractor -------------------------------------------------------


def test_extract_genius_lyrics_joins_containers() -> None:
    text = _extract_genius_lyrics(_song_page())
    assert text is not None
    assert "Placeholder verse one" in text
    assert "Placeholder chorus line" in text
    # <br/> becomes a newline
    assert "\n" in text
    # the LyricsHeader container is stripped
    assert "Contributors" not in text


def test_extract_genius_lyrics_returns_none_without_containers() -> None:
    assert _extract_genius_lyrics("<html><body><p>no lyrics</p></body></html>") is None


# --- provider (respx) -----------------------------------------------------


@respx.mock
async def test_lyrics_returns_plain(load_fixture: Any) -> None:
    search = respx.get(_SEARCH_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("genius", "search"))
    )
    respx.get(_PAGE_URL).mock(return_value=httpx.Response(200, text=_song_page()))
    provider = build_genius_provider(ProviderContext(genius_token="tok"))
    try:
        lyrics = await provider.lyrics(_TRACK)
    finally:
        await provider.aclose()
    assert lyrics is not None
    assert lyrics.kind is LyricsKind.PLAIN
    assert lyrics.source is ProviderId.GENIUS
    assert "Placeholder verse one" in lyrics.text
    # search carried the bearer token and the query
    assert search.calls.last.request.headers["Authorization"] == "Bearer tok"
    assert "Placeholder Song" in search.calls.last.request.url.params["q"]


@respx.mock
async def test_lyrics_returns_none_on_empty_search() -> None:
    respx.get(_SEARCH_URL).mock(return_value=httpx.Response(200, json={"response": {"hits": []}}))
    provider = build_genius_provider(ProviderContext(genius_token="tok"))
    try:
        assert await provider.lyrics(_TRACK) is None
    finally:
        await provider.aclose()


@respx.mock
async def test_lyrics_returns_none_when_page_has_no_lyrics(load_fixture: Any) -> None:
    respx.get(_SEARCH_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("genius", "search"))
    )
    respx.get(_PAGE_URL).mock(
        return_value=httpx.Response(200, text="<html><body>nothing</body></html>")
    )
    provider = build_genius_provider(ProviderContext(genius_token="tok"))
    try:
        assert await provider.lyrics(_TRACK) is None
    finally:
        await provider.aclose()


# --- token gate / capabilities --------------------------------------------


def test_genius_unavailable_without_token() -> None:
    # CONTRACT: no token -> the factory raises ProviderUnavailable, so the
    # registry omits Genius and records it in `unavailable`.
    with pytest.raises(ProviderUnavailable):
        build_genius_provider(ProviderContext())


async def test_genius_advertises_capabilities() -> None:
    provider = build_genius_provider(ProviderContext(genius_token="tok"))
    try:
        assert provider.id is ProviderId.GENIUS
        assert isinstance(provider, ProvidesLyrics)
    finally:
        await provider.aclose()


def test_genius_unavailable_in_registry_without_token() -> None:
    reg = build_default_registry(ProviderContext())
    assert ProviderId.GENIUS in reg.registered
    lyricists = reg.capable(ProvidesLyrics)
    assert all(p.id is not ProviderId.GENIUS for p in lyricists)
    assert ProviderId.GENIUS in reg.unavailable


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_genius_lookup() -> None:
    import os

    token = os.environ.get("SPOTDL_GENIUS_TOKEN")
    if not token:
        pytest.skip("SPOTDL_GENIUS_TOKEN not set")
    provider = build_genius_provider(ProviderContext(genius_token=token))
    try:
        lyrics = await provider.lyrics(
            Track(
                name="Bohemian Rhapsody",
                artists=("Queen",),
                duration_ms=354_000,
                provider=ProviderId.SPOTIFY,
                provider_id="x",
            )
        )
    finally:
        await provider.aclose()
    assert lyrics is None or lyrics.source is ProviderId.GENIUS
