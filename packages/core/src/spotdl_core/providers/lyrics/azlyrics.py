"""AZLyrics lyrics provider: geo.js token bootstrap + pure scraping.

AZLyrics requires a hidden ``x`` token to accept searches: it is emitted by
``/geo.js`` (``ep.setAttribute("value", "<x>")``). This provider fetches that
script, regex-extracts the token, searches with it, follows the best result, and
takes the **longest classless** ``<div>`` on the page as the lyrics body.
``beautifulsoup4`` is imported **lazily** inside the extractor so a broken
install degrades only this provider (isolation constraint); a parse failure (or
a missing token) yields ``None`` while a transport failure raises
:class:`~spotdl_core.providers.errors.ProviderUnavailable`. Returning ``None``
means "not found", not an error.

The token regex and scrape selectors are fragile implementation and expected to
rot (reference ``spotdl-v4-reference/spotdl/providers/lyrics/azlyrics.py``).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, ClassVar

import httpx

from spotdl_core.model import Lyrics, LyricsKind, ProviderId, Track
from spotdl_core.providers.base import HttpProvider
from spotdl_core.providers.errors import ProviderUnavailable
from spotdl_core.providers.lyrics._match import similarity

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext

__all__ = ["AZLyricsProvider", "build_azlyrics_provider"]

_BASE_URL = "https://www.azlyrics.com"
_GEO_URL = f"{_BASE_URL}/geo.js"
_SEARCH_URL = f"{_BASE_URL}/search/"

#: geo.js emits ``ep.setAttribute("value", "<x token>")``.
_X_CODE_RE = re.compile(r'setAttribute\(\s*"value"\s*,\s*"([^"]+)"\s*\)')

#: A browser-like User-Agent; AZLyrics serves a stripped page to unknown agents.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)


# --- pure helpers ---------------------------------------------------------


def _extract_x_code(js: str) -> str | None:
    """Regex-extract the hidden ``x`` token from a geo.js body, or ``None``."""
    match = _X_CODE_RE.search(js)
    if match is None:
        return None
    token = match.group(1).strip()
    return token or None


def _parse_azlyrics_search(html: str) -> list[tuple[str, str]]:
    """Return ``(label, url)`` for every absolute ``/lyrics/`` result link."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover - exercised only on broken installs
        raise ProviderUnavailable(
            "beautifulsoup4 is not available", provider=ProviderId.AZLYRICS
        ) from exc
    soup = BeautifulSoup(html, "lxml")
    results: list[tuple[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        if not href.startswith("http") or "/lyrics/" not in href:
            continue
        results.append((anchor.get_text(" ", strip=True), href))
    return results


def _best_azlyrics_url(html: str, track: Track) -> str | None:
    """Pick the search result whose label best matches the track, or ``None``."""
    results = _parse_azlyrics_search(html)
    if not results:
        return None
    target = f"{track.main_artist} {track.name}"
    return max(results, key=lambda pair: similarity(pair[0], target))[1]


def _extract_azlyrics(html: str) -> str | None:
    """Return the longest classless ``<div>``'s text, or ``None`` if none."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover - exercised only on broken installs
        raise ProviderUnavailable(
            "beautifulsoup4 is not available", provider=ProviderId.AZLYRICS
        ) from exc
    soup = BeautifulSoup(html, "lxml")
    classless = soup.find_all("div", class_=False)
    if not classless:
        return None
    lyrics_div = max(classless, key=lambda div: len(div.get_text()))
    text = lyrics_div.get_text().strip()
    return text or None


# --- provider -------------------------------------------------------------


class AZLyricsProvider(HttpProvider):
    """AZLyrics lyrics provider (scraper with geo.js token bootstrap).

    Implements :class:`~spotdl_core.providers.base.ProvidesLyrics`.
    """

    id: ClassVar[ProviderId] = ProviderId.AZLYRICS

    async def lyrics(self, track: Track) -> Lyrics | None:
        x_code = _extract_x_code(await self._get_text(_GEO_URL))
        if x_code is None:
            return None
        query = (
            f"{track.name.strip().replace(' ', '+')}+{track.main_artist.strip().replace(' ', '+')}"
        )
        search_html = await self._get_text(_SEARCH_URL, params={"q": query, "x": x_code})
        url = _best_azlyrics_url(search_html, track)
        if url is None:
            return None
        text = _extract_azlyrics(await self._get_text(url))
        if text is None:
            return None
        return Lyrics(kind=LyricsKind.PLAIN, text=text, source=ProviderId.AZLYRICS)

    async def _get_text(self, url: str, *, params: dict[str, Any] | None = None) -> str:
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(
                f"azlyrics request failed: {exc}", provider=ProviderId.AZLYRICS
            ) from exc
        return response.text


# --- factory --------------------------------------------------------------


def build_azlyrics_provider(ctx: ProviderContext) -> AZLyricsProvider:
    """Construct an :class:`AZLyricsProvider` from a :class:`ProviderContext`."""
    from spotdl_core.providers.http import create_client

    return AZLyricsProvider(create_client(user_agent=_USER_AGENT, timeout=30.0))
