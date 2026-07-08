"""YouTube provider: audio candidates via ``yt-dlp`` **metadata only**.

``yt-dlp`` is the download engine (Plan 4) and a hard dependency, so it is the
natural search backend here -- preferred over the fragile Invidious/pytube
paths. This provider does **not** download audio; it runs a flat
``ytsearch{N}:{query}`` extraction (``extract_flat`` keeps it to one cheap
request) purely to enumerate candidates. The blocking ``yt-dlp`` call runs in a
worker thread, and ``yt_dlp`` is imported **lazily** so a broken install
degrades only this provider.

The pure :func:`map_results` mapper is unit tested from a checked-in fixture.
Its mapping rules are **contract**: ``duration`` is reported in **seconds** and
stored as milliseconds, ``popularity`` is the ``view_count``, and candidates are
never ``verified`` (user-uploaded content, no catalogue guarantee).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from spotdl_core.model import AudioCandidate, ProviderId, Track

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext

__all__ = [
    "YoutubeDLFactory",
    "YouTubeProvider",
    "build_youtube_provider",
    "map_results",
]

_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"

#: Flat, quiet, download-free options: enumerate results without fetching pages.
_YTDL_OPTS: dict[str, Any] = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,
    "skip_download": True,
}


# --- pure mapper ----------------------------------------------------------


def map_results(entries: list[dict[str, Any]]) -> list[AudioCandidate]:
    """Map flat ``yt-dlp`` search entries to audio candidates (best-first).

    Entries without an ``id`` or ``title`` are skipped. ``duration`` (seconds)
    becomes ``duration_ms``; ``uploader`` (falling back to ``channel``) becomes
    the single artist; ``view_count`` becomes ``popularity``.
    """
    candidates: list[AudioCandidate] = []
    for entry in entries:
        video_id = entry.get("id")
        title = entry.get("title")
        if not video_id or not title:
            continue
        url = entry.get("webpage_url") or entry.get("url") or _WATCH_URL.format(video_id=video_id)
        uploader = entry.get("uploader") or entry.get("channel")
        duration = entry.get("duration")
        candidates.append(
            AudioCandidate(
                provider=ProviderId.YOUTUBE,
                provider_id=video_id,
                url=url,
                name=title,
                artists=(uploader,) if uploader else (),
                duration_ms=int(duration) * 1000 if isinstance(duration, int | float) else None,
                verified=False,
                popularity=entry.get("view_count"),
            )
        )
    return candidates


# --- provider -------------------------------------------------------------

#: Builds a ``yt_dlp.YoutubeDL`` (a context manager) from an options dict.
YoutubeDLFactory = Callable[[dict[str, Any]], Any]


def _default_ytdl_factory(opts: dict[str, Any]) -> Any:
    """Lazily import ``yt_dlp`` and build a client (isolation constraint)."""
    from yt_dlp import YoutubeDL  # type: ignore[import-untyped]

    return YoutubeDL(opts)


class YouTubeProvider:
    """YouTube audio-candidate provider (metadata only, via ``yt-dlp``).

    Implements :class:`~spotdl_core.providers.base.ProvidesAudio`. The blocking
    ``yt-dlp`` extraction runs in a worker thread.
    """

    id: ClassVar[ProviderId] = ProviderId.YOUTUBE

    def __init__(self, *, ytdl_factory: YoutubeDLFactory = _default_ytdl_factory) -> None:
        self._ytdl_factory = ytdl_factory

    async def audio_candidates(self, track: Track, *, limit: int = 10) -> list[AudioCandidate]:
        query = f"{track.main_artist} - {track.name}"
        entries = await asyncio.to_thread(self._extract, query, limit)
        return map_results(entries)[:limit]

    def _extract(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Run one flat ``ytsearch`` extraction (blocking; called via a thread)."""
        with self._ytdl_factory(_YTDL_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        entries = (info or {}).get("entries") or []
        return [entry for entry in entries if isinstance(entry, dict)]


# --- factory --------------------------------------------------------------


def build_youtube_provider(ctx: ProviderContext) -> YouTubeProvider:
    """Construct a :class:`YouTubeProvider` from a :class:`ProviderContext`.

    The ``yt_dlp`` import happens lazily on first search, so building the
    provider (and therefore registry construction) never imports the library.
    """
    return YouTubeProvider()
