"""Musixmatch lyrics provider: pure scraping, no token.

Musixmatch has no open token flow here, so this provider **scrapes**: it fetches
the search page, collects ``a[href^='/lyrics/']`` links, follows the one whose
title best matches the track, and joins the ``p.mxm-lyrics__content`` paragraphs
on the lyrics page. ``beautifulsoup4`` is imported **lazily** inside the parse
helpers so a broken install degrades only this provider (isolation constraint);
a parse failure yields ``None`` while a transport failure raises
:class:`~spotdl_core.providers.errors.ProviderUnavailable`. Returning ``None``
means "not found", not an error.

The scrape selectors are fragile implementation and expected to rot (reference
``spotdl-v4-reference/spotdl/providers/lyrics/musixmatch.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar
from urllib.parse import quote

import httpx

from spotdl_core.model import Lyrics, LyricsKind, ProviderId, Track
from spotdl_core.providers.base import HttpProvider
from spotdl_core.providers.errors import ProviderUnavailable
from spotdl_core.providers.lyrics._match import similarity

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext

__all__ = ["MusixmatchProvider", "build_musixmatch_provider"]

_BASE_URL = "https://www.musixmatch.com"
_SEARCH_URL = f"{_BASE_URL}/search/"

#: A browser-like User-Agent; Musixmatch serves a stripped page to unknown agents.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)


# --- pure helpers ---------------------------------------------------------


def _parse_musixmatch_search(html: str) -> list[tuple[str, str]]:
    """Return ``(title, absolute_url)`` pairs for every ``/lyrics/`` result."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover - exercised only on broken installs
        raise ProviderUnavailable(
            "beautifulsoup4 is not available", provider=ProviderId.MUSIXMATCH
        ) from exc
    soup = BeautifulSoup(html, "lxml")
    results: list[tuple[str, str]] = []
    for anchor in soup.select("a[href^='/lyrics/']"):
        href = anchor.get("href")
        if not isinstance(href, str) or not href:
            continue
        results.append((anchor.get_text(strip=True), _BASE_URL + href))
    return results


def _best_musixmatch_url(html: str, track: Track) -> str | None:
    """Pick the search result whose title best matches the track, or ``None``."""
    results = _parse_musixmatch_search(html)
    if not results:
        return None
    target = f"{track.name} {track.main_artist}"
    return max(results, key=lambda pair: similarity(pair[0], target))[1]


def _extract_musixmatch(html: str) -> str | None:
    """Join the ``p.mxm-lyrics__content`` paragraphs, or ``None`` if absent."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover - exercised only on broken installs
        raise ProviderUnavailable(
            "beautifulsoup4 is not available", provider=ProviderId.MUSIXMATCH
        ) from exc
    soup = BeautifulSoup(html, "lxml")
    paragraphs = soup.select("p.mxm-lyrics__content")
    text = "\n".join(paragraph.get_text() for paragraph in paragraphs).strip()
    return text or None


# --- provider -------------------------------------------------------------


class MusixmatchProvider(HttpProvider):
    """Musixmatch lyrics provider (scraper).

    Implements :class:`~spotdl_core.providers.base.ProvidesLyrics`.
    """

    id: ClassVar[ProviderId] = ProviderId.MUSIXMATCH

    async def lyrics(self, track: Track) -> Lyrics | None:
        query = quote(f"{track.name} - {track.main_artist}", safe="")
        search_html = await self._get_text(_SEARCH_URL + query)
        url = _best_musixmatch_url(search_html, track)
        if url is None:
            return None
        text = _extract_musixmatch(await self._get_text(url))
        if text is None:
            return None
        return Lyrics(kind=LyricsKind.PLAIN, text=text, source=ProviderId.MUSIXMATCH)

    async def _get_text(self, url: str) -> str:
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(
                f"musixmatch request failed: {exc}", provider=ProviderId.MUSIXMATCH
            ) from exc
        return response.text


# --- factory --------------------------------------------------------------


def build_musixmatch_provider(ctx: ProviderContext) -> MusixmatchProvider:
    """Construct a :class:`MusixmatchProvider` from a :class:`ProviderContext`."""
    from spotdl_core.providers.http import create_client

    return MusixmatchProvider(create_client(user_agent=_USER_AGENT, timeout=30.0))
