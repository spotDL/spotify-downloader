"""Tests for the Musixmatch lyrics provider (Task 11).

Musixmatch has no public token flow here, so this provider **scrapes**: it hits
the search page, follows the best ``/lyrics/`` link, and joins the
``p.mxm-lyrics__content`` paragraphs. Every test is offline except the single
``@pytest.mark.network`` live lookup; the pure extractor runs from a checked-in
HTML fixture and HTTP behaviour is mocked with ``respx``.

Fixture lyric bodies are short SYNTHETIC placeholder text -- never real song
lyrics. Selectors here are fragile scraper implementation, expected to rot.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from spotdl_core.model import LyricsKind, ProviderId, Track
from spotdl_core.providers.base import ProvidesLyrics
from spotdl_core.providers.lyrics.musixmatch import (
    MusixmatchProvider,
    _extract_musixmatch,
    build_musixmatch_provider,
)
from spotdl_core.providers.registry import ProviderContext, build_default_registry

_FIXTURES = Path(__file__).parent / "fixtures"
_LYRICS_URL = "https://www.musixmatch.com/lyrics/Placeholder-Artist/Placeholder-Song"

_TRACK = Track(
    name="Placeholder Song",
    artists=("Placeholder Artist",),
    duration_ms=180_000,
    provider=ProviderId.SPOTIFY,
    provider_id="x",
)


def _read(name: str) -> str:
    return (_FIXTURES / "musixmatch" / name).read_text(encoding="utf-8")


# --- pure extractor -------------------------------------------------------


def test_extract_musixmatch_joins_paragraphs() -> None:
    text = _extract_musixmatch(_read("lyrics_page.html"))
    assert text is not None
    assert "Placeholder verse one" in text
    assert "Placeholder chorus line" in text


def test_extract_musixmatch_returns_none_when_empty() -> None:
    assert _extract_musixmatch("<html><body><p>no lyrics</p></body></html>") is None


# --- provider (respx) -----------------------------------------------------


@respx.mock
async def test_lyrics_returns_plain() -> None:
    search = respx.get(url__startswith="https://www.musixmatch.com/search/").mock(
        return_value=httpx.Response(200, text=_read("search.html"))
    )
    respx.get(_LYRICS_URL).mock(return_value=httpx.Response(200, text=_read("lyrics_page.html")))
    provider = MusixmatchProvider(_client())
    try:
        lyrics = await provider.lyrics(_TRACK)
    finally:
        await provider.aclose()
    assert lyrics is not None
    assert lyrics.kind is LyricsKind.PLAIN
    assert lyrics.source is ProviderId.MUSIXMATCH
    assert "Placeholder verse one" in lyrics.text
    assert search.called


@respx.mock
async def test_lyrics_returns_none_when_no_search_results() -> None:
    respx.get(url__startswith="https://www.musixmatch.com/search/").mock(
        return_value=httpx.Response(200, text="<html><body>no results</body></html>")
    )
    provider = MusixmatchProvider(_client())
    try:
        assert await provider.lyrics(_TRACK) is None
    finally:
        await provider.aclose()


# --- wiring / capabilities ------------------------------------------------


async def test_musixmatch_advertises_capabilities() -> None:
    provider = build_musixmatch_provider(ProviderContext())
    try:
        assert provider.id is ProviderId.MUSIXMATCH
        assert isinstance(provider, ProvidesLyrics)
    finally:
        await provider.aclose()


def test_musixmatch_registered_in_default_registry() -> None:
    reg = build_default_registry(ProviderContext())
    assert ProviderId.MUSIXMATCH in reg.registered


def _client() -> httpx.AsyncClient:
    from spotdl_core.providers.http import create_client

    return create_client()


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_musixmatch_lookup() -> None:
    provider = build_musixmatch_provider(ProviderContext())
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
    assert lyrics is None or lyrics.source is ProviderId.MUSIXMATCH
