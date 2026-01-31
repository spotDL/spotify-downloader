"""YouTube target provider for searching audio sources."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Any

import yt_dlp

from spotdl_cli.core.types import DownloadResult, TargetPlatform
from spotdl_cli.providers.base import SearchError, TargetProvider

if TYPE_CHECKING:
    from spotdl_cli.core.types import Song

logger = logging.getLogger(__name__)

# YouTube video URL pattern
YOUTUBE_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"
)


class YouTubeProvider(TargetProvider):
    """
    YouTube target provider.

    Searches YouTube for audio sources using yt-dlp.
    """

    name = "youtube"
    display_name = "YouTube"

    def __init__(
        self,
        cookies_path: str | None = None,
    ) -> None:
        """Initialize the YouTube provider."""
        super().__init__()
        self._cookies_path = cookies_path

    def _get_yt_dlp_options(self) -> dict[str, Any]:
        """Get yt-dlp options for search."""
        options: dict[str, Any] = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "default_search": "ytsearch",
        }

        if self._cookies_path:
            options["cookiefile"] = self._cookies_path

        return options

    def _extract_info(
        self, url: str, options: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract info using yt-dlp (blocking)."""
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                return ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as e:
            logger.warning(f"yt-dlp extraction error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during extraction: {e}")
            return None

    def _entry_to_result(self, entry: dict[str, Any]) -> DownloadResult | None:
        """Convert yt-dlp entry to DownloadResult."""
        try:
            video_id = entry.get("id", "")
            title = entry.get("title", "")
            duration = entry.get("duration", 0) or 0

            if not video_id or not title:
                return None

            channel = entry.get("channel", "") or entry.get("uploader", "") or ""
            artists = [channel] if channel else []

            url = f"https://www.youtube.com/watch?v={video_id}"
            is_verified = entry.get("channel_is_verified", False)
            album_name = entry.get("album", None)

            return DownloadResult(
                name=title,
                artists=artists,
                artist=channel,
                duration=int(duration),
                platform=TargetPlatform.YOUTUBE,
                platform_id=video_id,
                url=url,
                verified=is_verified,
                album_name=album_name,
                views=entry.get("view_count"),
                cover_url=entry.get("thumbnail"),
            )

        except Exception as e:
            logger.warning(f"Failed to convert entry to result: {e}")
            return None

    async def search(self, song: Song, limit: int = 10) -> list[DownloadResult]:
        """Search YouTube for matching videos."""
        query = self.build_search_query(song)
        options = self._get_yt_dlp_options()
        search_query = f"ytsearch{limit}:{query}"

        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._extract_info,
                search_query,
                options,
            )

            if not results:
                return []

            download_results = []
            entries = results.get("entries", [])

            for entry in entries:
                if not entry:
                    continue

                result = self._entry_to_result(entry)
                if result:
                    download_results.append(result)

            return download_results

        except Exception as e:
            raise SearchError(f"YouTube search failed: {e}") from e

    async def get_video_info(self, video_id: str) -> DownloadResult | None:
        """Get video information by ID."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        options = self._get_yt_dlp_options()
        options["extract_flat"] = False

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._extract_info,
                url,
                options,
            )

            if result:
                return self._entry_to_result(result)
            return None

        except Exception:
            return None

    @staticmethod
    def extract_video_id(url: str) -> str | None:
        """Extract video ID from YouTube URL."""
        match = YOUTUBE_URL_PATTERN.search(url)
        if match:
            return match.group(1)
        return None
