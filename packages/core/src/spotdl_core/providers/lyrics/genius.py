"""Genius lyrics provider: token-gated API search + HTML scrape.

Genius exposes a JSON search API but serves the lyrics themselves only as HTML,
so this provider does both: it searches ``api.genius.com`` (authenticated with a
bearer token), picks the hit whose title best matches the track, then fetches
that result's ``genius.com`` page and extracts the ``Lyrics__Container`` blocks.

Token requirement is a **contract**: without ``ctx.genius_token`` the factory
raises :class:`~spotdl_core.providers.errors.ProviderNotConfigured`, so the
registry omits Genius from ``capable(ProvidesLyrics)`` and records it in
``unavailable`` — while consumers (the resolve layer) treat a key-less Genius as
a deliberate absence, never a degraded source. ``beautifulsoup4`` is imported
**lazily** inside the extractor so a broken install degrades only this provider;
a parse failure yields ``None`` while a transport failure raises
``ProviderUnavailable``. Returning ``None`` means "not found", not an error.

The scrape selectors are fragile implementation and expected to rot (reference
``spotdl-v4-reference/spotdl/providers/lyrics/genius.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

import httpx

from spotdl_core.model import Lyrics, LyricsKind, ProviderId, Track
from spotdl_core.providers.base import HttpProvider
from spotdl_core.providers.errors import (
    EntityNotFound,
    ProviderNotConfigured,
    ProviderUnavailable,
)
from spotdl_core.providers.http import request_json
from spotdl_core.providers.lyrics._match import similarity

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext

__all__ = ["GeniusProvider", "build_genius_provider"]

_SEARCH_URL = "https://api.genius.com/search"

#: Minimum title similarity for a search hit to be accepted as the right song.
_MIN_SCORE = 0.5


# --- pure helpers ---------------------------------------------------------


def _best_hit_url(payload: Any, track: Track) -> str | None:
    """Return the URL of the best-matching Genius search hit, or ``None``.

    Hits are scored by title similarity to ``"<name> <artist>"``; the best is
    returned only if it clears :data:`_MIN_SCORE`.
    """
    hits = []
    if isinstance(payload, dict):
        response = payload.get("response")
        if isinstance(response, dict):
            raw = response.get("hits")
            if isinstance(raw, list):
                hits = raw
    target = f"{track.name} {track.main_artist}"
    best_url: str | None = None
    best_score = -1.0
    for hit in hits:
        result = hit.get("result") if isinstance(hit, dict) else None
        if not isinstance(result, dict):
            continue
        url = result.get("url")
        if not isinstance(url, str) or not url:
            continue
        candidate = result.get("full_title") or result.get("title") or ""
        score = similarity(str(candidate), target)
        if score > best_score:
            best_score = score
            best_url = url
    if best_url is None or best_score < _MIN_SCORE:
        return None
    return best_url


def _extract_genius_lyrics(html: str) -> str | None:
    """Extract lyrics text from a Genius song page, or ``None`` if absent.

    ``<br>``/``<br/>`` become newlines; the ``LyricsHeader__Container`` block is
    removed; the ``Lyrics__Container`` blocks (or the legacy ``div.lyrics``) are
    joined. ``beautifulsoup4`` is imported lazily (isolation constraint).
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover - exercised only on broken installs
        raise ProviderUnavailable(
            "beautifulsoup4 is not available", provider=ProviderId.GENIUS
        ) from exc
    soup = BeautifulSoup(html.replace("<br/>", "\n").replace("<br>", "\n"), "lxml")
    for header in soup.select("div[class^=LyricsHeader__Container]"):
        header.decompose()
    containers = soup.select("div[class^=Lyrics__Container]")
    if containers:
        text = "\n".join(container.get_text() for container in containers)
    else:
        legacy = soup.select_one("div.lyrics")
        if legacy is None:
            return None
        text = legacy.get_text()
    text = text.strip()
    return text or None


# --- provider -------------------------------------------------------------


class GeniusProvider(HttpProvider):
    """Genius lyrics provider (API search + HTML scrape).

    Implements :class:`~spotdl_core.providers.base.ProvidesLyrics`.
    """

    id: ClassVar[ProviderId] = ProviderId.GENIUS

    async def lyrics(self, track: Track) -> Lyrics | None:
        params = {"q": f"{track.name} {track.main_artist}"}
        try:
            payload = await request_json(
                self._client, "GET", _SEARCH_URL, provider=ProviderId.GENIUS, params=params
            )
        except EntityNotFound:
            return None
        url = _best_hit_url(payload, track)
        if url is None:
            return None
        text = _extract_genius_lyrics(await self._get_text(url))
        if text is None:
            return None
        return Lyrics(kind=LyricsKind.PLAIN, text=text, source=ProviderId.GENIUS)

    async def _get_text(self, url: str) -> str:
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(
                f"genius request failed: {exc}", provider=ProviderId.GENIUS
            ) from exc
        return response.text


# --- factory --------------------------------------------------------------


def build_genius_provider(ctx: ProviderContext) -> GeniusProvider:
    """Construct a :class:`GeniusProvider`; require a token (contract).

    Raises :class:`ProviderNotConfigured` when ``ctx.genius_token`` is unset so the
    registry omits Genius rather than constructing a provider that always fails —
    and, being a deliberate absence, it never surfaces as a degraded source.
    """
    token = ctx.genius_token
    if not token:
        raise ProviderNotConfigured(
            "genius requires an access token (ctx.genius_token)", provider=ProviderId.GENIUS
        )
    from spotdl_core.providers.http import create_client

    client = create_client(headers={"Authorization": f"Bearer {token}"})
    return GeniusProvider(client)
