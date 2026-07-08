"""Tests for the AZLyrics lyrics provider (Task 11).

AZLyrics requires a ``geo.js`` bootstrap: a hidden ``x`` token is regex-extracted
from that script and passed to the search endpoint, then the result page's
longest classless ``<div>`` is taken as the lyrics body. Every test is offline
except the single ``@pytest.mark.network`` live lookup; the pure extractor and
the token parser run from checked-in fixtures and HTTP behaviour is mocked with
``respx``.

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
from spotdl_core.providers.http import create_client
from spotdl_core.providers.lyrics.azlyrics import (
    AZLyricsProvider,
    _extract_azlyrics,
    _extract_x_code,
    build_azlyrics_provider,
)
from spotdl_core.providers.registry import ProviderContext, build_default_registry

_FIXTURES = Path(__file__).parent / "fixtures"
_GEO_URL = "https://www.azlyrics.com/geo.js"
_SEARCH_URL = "https://www.azlyrics.com/search/"
_RESULT_URL = "https://www.azlyrics.com/lyrics/placeholderartist/placeholdersong.html"

_GEO_JS = """
var az_country_code;
az_country_code = "US";
(function() {
    var ep = document.createElement("input");
    ep.setAttribute("type", "hidden");
    ep.setAttribute("name", "x");
    ep.setAttribute("value", "placeholdertoken1234");
    var els = document.querySelectorAll('form.search');
    for (var n = 0; n < els.length; n++) {
        els[n].appendChild(ep.cloneNode());
    }
})();
"""

_TRACK = Track(
    name="Placeholder Song",
    artists=("Placeholder Artist",),
    duration_ms=180_000,
    provider=ProviderId.SPOTIFY,
    provider_id="x",
)


def _read(name: str) -> str:
    return (_FIXTURES / "azlyrics" / name).read_text(encoding="utf-8")


# --- pure parsers ---------------------------------------------------------


def test_extract_x_code() -> None:
    assert _extract_x_code(_GEO_JS) == "placeholdertoken1234"


def test_extract_x_code_returns_none_when_absent() -> None:
    assert _extract_x_code("var az_country_code = 'US';") is None


def test_extract_azlyrics_picks_longest_classless_div() -> None:
    text = _extract_azlyrics(_read("lyrics_page.html"))
    assert text is not None
    assert "Placeholder verse one" in text
    assert "Placeholder chorus line" in text
    # not the short "Submit Corrections" div
    assert "Submit Corrections" not in text


def test_extract_azlyrics_returns_none_without_divs() -> None:
    assert _extract_azlyrics("<html><body><p>no divs</p></body></html>") is None


# --- provider (respx) -----------------------------------------------------


@respx.mock
async def test_lyrics_returns_plain() -> None:
    respx.get(_GEO_URL).mock(return_value=httpx.Response(200, text=_GEO_JS))
    search = respx.get(_SEARCH_URL).mock(
        return_value=httpx.Response(200, text=_read("search.html"))
    )
    respx.get(_RESULT_URL).mock(return_value=httpx.Response(200, text=_read("lyrics_page.html")))
    async with create_client() as client:
        lyrics = await AZLyricsProvider(client).lyrics(_TRACK)
    assert lyrics is not None
    assert lyrics.kind is LyricsKind.PLAIN
    assert lyrics.source is ProviderId.AZLYRICS
    assert "Placeholder verse one" in lyrics.text
    params = search.calls.last.request.url.params
    assert params["x"] == "placeholdertoken1234"
    assert "Placeholder" in params["q"]


@respx.mock
async def test_lyrics_returns_none_without_x_code() -> None:
    respx.get(_GEO_URL).mock(return_value=httpx.Response(200, text="no token here"))
    async with create_client() as client:
        assert await AZLyricsProvider(client).lyrics(_TRACK) is None


@respx.mock
async def test_lyrics_returns_none_when_no_results() -> None:
    respx.get(_GEO_URL).mock(return_value=httpx.Response(200, text=_GEO_JS))
    respx.get(_SEARCH_URL).mock(
        return_value=httpx.Response(200, text="<html><body>no results</body></html>")
    )
    async with create_client() as client:
        assert await AZLyricsProvider(client).lyrics(_TRACK) is None


# --- wiring / capabilities ------------------------------------------------


async def test_azlyrics_advertises_capabilities() -> None:
    provider = build_azlyrics_provider(ProviderContext())
    try:
        assert provider.id is ProviderId.AZLYRICS
        assert isinstance(provider, ProvidesLyrics)
    finally:
        await provider.aclose()


def test_azlyrics_registered_in_default_registry() -> None:
    reg = build_default_registry(ProviderContext())
    assert ProviderId.AZLYRICS in reg.registered


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_azlyrics_lookup() -> None:
    provider = build_azlyrics_provider(ProviderContext())
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
    assert lyrics is None or lyrics.source is ProviderId.AZLYRICS
