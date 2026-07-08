"""LRCLIB lyrics provider: the one synced-lyrics source in v1.

LRCLIB (https://lrclib.net) publishes an open, documented JSON API, so this
provider talks to it **directly** with ``httpx`` -- no scraping, no
``beautifulsoup4``, and no heavy third-party bundle. It is the only provider
that can return time-synced (LRC) lyrics.

Lookup strategy (spec §5.2, brief Task 11):

1. ``GET /api/get`` with the exact ``artist_name``/``track_name``/``album_name``
   and ``duration`` (in **seconds**). A 404 means "no exact match", not an error.
2. On a 404, fall back to ``GET /api/search?q=...`` and take the first hit that
   carries lyrics.

The SYNCED-vs-PLAIN preference is a **contract**: when a payload has non-empty
``syncedLyrics`` it wins over ``plainLyrics``; either way the result carries
``source = LRCLIB``. Returning ``None`` means "not found" and is never an error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from spotdl_core.model import Lyrics, LyricsKind, ProviderId, Track
from spotdl_core.providers.base import HttpProvider
from spotdl_core.providers.errors import EntityNotFound
from spotdl_core.providers.http import request_json

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext

__all__ = ["LrclibProvider", "build_lrclib_provider"]

_BASE_URL = "https://lrclib.net"
_GET_URL = f"{_BASE_URL}/api/get"
_SEARCH_URL = f"{_BASE_URL}/api/search"

#: LRCLIB asks API clients to identify themselves with a descriptive UA.
_USER_AGENT = "spotdl/5.0 (https://github.com/spotDL/spotify-downloader)"


# --- pure parser ----------------------------------------------------------


def _parse_lrclib(payload: Any) -> Lyrics | None:
    """Map one LRCLIB record to :class:`Lyrics`, preferring synced lyrics.

    CONTRACT: non-empty ``syncedLyrics`` -> ``SYNCED``; otherwise non-empty
    ``plainLyrics`` -> ``PLAIN``; otherwise ``None`` (an instrumental track or a
    record with no lyrics).
    """
    if not isinstance(payload, dict):
        return None
    synced = payload.get("syncedLyrics")
    if isinstance(synced, str) and synced.strip():
        return Lyrics(kind=LyricsKind.SYNCED, text=synced.strip(), source=ProviderId.LRCLIB)
    plain = payload.get("plainLyrics")
    if isinstance(plain, str) and plain.strip():
        return Lyrics(kind=LyricsKind.PLAIN, text=plain.strip(), source=ProviderId.LRCLIB)
    return None


# --- provider -------------------------------------------------------------


class LrclibProvider(HttpProvider):
    """LRCLIB lyrics provider (direct JSON API).

    Implements :class:`~spotdl_core.providers.base.ProvidesLyrics`.
    """

    id: ClassVar[ProviderId] = ProviderId.LRCLIB

    async def lyrics(self, track: Track) -> Lyrics | None:
        payload = await self._get_exact(track)
        if payload is not None:
            found = _parse_lrclib(payload)
            if found is not None:
                return found
        return await self._search(track)

    async def _get_exact(self, track: Track) -> Any | None:
        """Query ``/api/get``; a 404 returns ``None`` (no exact match)."""
        params = {
            "artist_name": track.main_artist,
            "track_name": track.name,
            "album_name": track.album.name if track.album and track.album.name else "",
            "duration": track.duration_ms // 1000,
        }
        try:
            return await request_json(
                self._client, "GET", _GET_URL, provider=ProviderId.LRCLIB, params=params
            )
        except EntityNotFound:
            return None

    async def _search(self, track: Track) -> Lyrics | None:
        """Fall back to ``/api/search`` and take the first hit with lyrics."""
        params = {"q": f"{track.name} {track.main_artist}"}
        try:
            results = await request_json(
                self._client, "GET", _SEARCH_URL, provider=ProviderId.LRCLIB, params=params
            )
        except EntityNotFound:
            return None
        if not isinstance(results, list):
            return None
        for item in results:
            found = _parse_lrclib(item)
            if found is not None:
                return found
        return None


# --- factory --------------------------------------------------------------


def build_lrclib_provider(ctx: ProviderContext) -> LrclibProvider:
    """Construct an :class:`LrclibProvider` from a :class:`ProviderContext`."""
    from spotdl_core.providers.http import create_client

    return LrclibProvider(create_client(user_agent=_USER_AGENT))
