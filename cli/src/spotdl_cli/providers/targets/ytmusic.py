"""YouTube Music target provider for searching audio sources."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Any

from spotdl_cli.core.types import DownloadResult, TargetPlatform
from spotdl_cli.providers.base import SearchError, TargetProvider

if TYPE_CHECKING:
    from spotdl_cli.core.types import Song

logger = logging.getLogger(__name__)

# YouTube Music URL pattern
YTMUSIC_URL_PATTERN = re.compile(
    r"(?:https?://)?music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)"
)


class YouTubeMusicTargetProvider(TargetProvider):
    """
    YouTube Music target provider.

    Searches YouTube Music for audio sources using ytmusicapi.
    """

    name = "youtube_music"
    display_name = "YouTube Music"

    def __init__(self, auth_file: str | None = None) -> None:
        """Initialize the YouTube Music provider."""
        super().__init__()
        self._auth_file = auth_file
        self._client: Any = None

    def _get_client(self) -> Any:
        """Get or create the YTMusic client."""
        if self._client is None:
            from ytmusicapi import YTMusic

            if self._auth_file:
                self._client = YTMusic(self._auth_file)
            else:
                self._client = YTMusic()
        return self._client

    def _result_to_result(self, song_data: dict[str, Any]) -> DownloadResult:
        """Convert YouTube Music song data to DownloadResult object."""
        video_id = song_data.get("videoId", "")

        # Get artists
        artists_data = song_data.get("artists", [])
        artists = [a.get("name", "") for a in artists_data if a.get("name")]
        if not artists:
            artists = [song_data.get("author", "Unknown")]

        primary_artist = artists[0] if artists else "Unknown"

        # Get duration
        duration = 0
        duration_str = song_data.get("duration", "")
        duration_seconds = song_data.get("duration_seconds")

        if duration_seconds:
            duration = int(duration_seconds)
        elif duration_str:
            parts = duration_str.split(":")
            try:
                if len(parts) == 2:
                    duration = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except ValueError:
                pass

        # Get album info
        album_data = song_data.get("album", {}) or {}
        album_name = album_data.get("name", "") if isinstance(album_data, dict) else ""

        # Get thumbnail
        thumbnails = song_data.get("thumbnails", [])
        cover_url = None
        if thumbnails:
            sorted_thumbs = sorted(
                thumbnails,
                key=lambda x: x.get("width", 0) * x.get("height", 0),
                reverse=True,
            )
            cover_url = sorted_thumbs[0].get("url")

        # Check if explicit
        explicit = song_data.get("isExplicit", False)

        return DownloadResult(
            name=song_data.get("title", "Unknown"),
            artists=artists,
            artist=primary_artist,
            duration=duration,
            platform=TargetPlatform.YOUTUBE_MUSIC,
            platform_id=video_id,
            url=f"https://music.youtube.com/watch?v={video_id}",
            album_name=album_name,
            cover_url=cover_url,
            verified=explicit,  # Use explicit as a proxy for verified official track
        )

    async def search(self, song: Song, limit: int = 10) -> list[DownloadResult]:
        """Search YouTube Music for matching tracks."""
        query = self.build_search_query(song)

        try:
            client = self._get_client()
            loop = asyncio.get_event_loop()

            # Search for songs
            search_results = await loop.run_in_executor(
                None,
                lambda: client.search(query, filter="songs", limit=limit),
            )

            results: list[DownloadResult] = []
            for item in search_results:
                if item.get("videoId"):
                    result = self._result_to_result(item)
                    results.append(result)

            return results

        except Exception as e:
            raise SearchError(f"YouTube Music search failed: {e}") from e

    async def search_by_isrc(self, isrc: str) -> DownloadResult | None:
        """Search YouTube Music by ISRC code."""
        try:
            client = self._get_client()
            loop = asyncio.get_event_loop()

            search_results = await loop.run_in_executor(
                None,
                lambda: client.search(isrc, filter="songs", limit=1),
            )

            for item in search_results:
                if item.get("videoId"):
                    return self._result_to_result(item)

            return None

        except Exception:
            return None

    async def get_song_info(self, video_id: str) -> DownloadResult | None:
        """Get song information by video ID."""
        try:
            client = self._get_client()
            loop = asyncio.get_event_loop()

            song_data = await loop.run_in_executor(None, client.get_song, video_id)

            if song_data is None:
                return None

            # Build unified data structure
            video_details = song_data.get("videoDetails", {})
            unified_data = {
                "videoId": video_id,
                "title": video_details.get("title", ""),
                "author": video_details.get("author", ""),
                "duration_seconds": video_details.get("lengthSeconds"),
                "thumbnails": video_details.get("thumbnail", {}).get("thumbnails", []),
            }

            return self._result_to_result(unified_data)

        except Exception:
            return None

    @staticmethod
    def extract_video_id(url: str) -> str | None:
        """Extract video ID from YouTube Music URL."""
        match = YTMUSIC_URL_PATTERN.search(url)
        if match:
            return match.group(1)

        # Also try standard YouTube pattern
        yt_match = re.search(r"[?&]v=([a-zA-Z0-9_-]+)", url)
        if yt_match:
            return yt_match.group(1)

        return None
