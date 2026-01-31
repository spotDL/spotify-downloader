"""YouTube target provider for searching audio sources."""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

import httpx

from spotdl_core.core.types.result import Result, TargetPlatform
from spotdl_core.providers.targets.base import (
    SearchError,
    TargetProvider,
)

if TYPE_CHECKING:
    from spotdl_core.core.types.song import Song

# YouTube video URL pattern
YOUTUBE_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"
)


class YouTubeProvider(TargetProvider):
    """
    YouTube target provider.

    Searches YouTube for audio sources using the Invidious API
    (a privacy-respecting YouTube frontend) or yt-dlp for extraction.
    """

    name = "youtube"
    display_name = "YouTube"

    # List of Invidious instances to try
    INVIDIOUS_INSTANCES = [
        "https://vid.puffyan.us",
        "https://invidious.snopyta.org",
        "https://yewtu.be",
        "https://invidious.kavin.rocks",
        "https://inv.riverside.rocks",
    ]

    def __init__(
        self,
        timeout: float = 30.0,
        invidious_instance: str | None = None,
    ) -> None:
        """
        Initialize the YouTube provider.

        Args:
            timeout: Request timeout in seconds
            invidious_instance: Custom Invidious instance URL
        """
        super().__init__()
        self._timeout = timeout
        self._invidious_instance = invidious_instance
        self._client: httpx.AsyncClient | None = None
        self._working_instance: str | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; SpotDL/5.0)"
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _get_working_instance(self) -> str:
        """
        Find a working Invidious instance.

        Returns:
            Working instance URL

        Raises:
            SearchError: If no working instance found
        """
        if self._invidious_instance:
            return self._invidious_instance

        if self._working_instance:
            return self._working_instance

        client = await self._get_client()

        for instance in self.INVIDIOUS_INSTANCES:
            try:
                response = await client.get(f"{instance}/api/v1/stats", timeout=5.0)
                if response.status_code == 200:
                    self._working_instance = instance
                    return instance
            except httpx.HTTPError:
                continue

        raise SearchError("No working Invidious instance found")

    def _result_to_result(self, video: dict[str, Any]) -> Result:
        """
        Convert Invidious video data to Result object.

        Args:
            video: Video data from Invidious API

        Returns:
            Result object
        """
        video_id = video.get("videoId", "")

        # Get thumbnail
        thumbnails = video.get("videoThumbnails", [])
        cover_url = None
        if thumbnails:
            # Get highest quality thumbnail
            sorted_thumbs = sorted(
                thumbnails,
                key=lambda x: x.get("width", 0) * x.get("height", 0),
                reverse=True,
            )
            cover_url = sorted_thumbs[0].get("url")

        # Build artists list
        author = video.get("author", "Unknown")
        artists = [author]

        return Result(
            name=video.get("title", "Unknown"),
            artists=artists,
            artist=author,
            duration=video.get("lengthSeconds", 0),
            platform=TargetPlatform.YOUTUBE,
            platform_id=video_id,
            url=f"https://www.youtube.com/watch?v={video_id}",
            cover_url=cover_url,
            views=video.get("viewCount"),
            verified=video.get("isVerified", False),
        )

    async def search(self, song: Song, limit: int = 10) -> list[Result]:
        """
        Search YouTube for matching videos.

        Args:
            song: Song to search for
            limit: Maximum number of results

        Returns:
            List of Result objects
        """
        query = self.build_search_query(song)

        try:
            instance = await self._get_working_instance()
            client = await self._get_client()

            # URL encode the query
            import urllib.parse
            encoded_query = urllib.parse.quote(query)

            # Search using Invidious API
            response = await client.get(
                f"{instance}/api/v1/search",
                params={
                    "q": query,
                    "type": "video",
                    "sort_by": "relevance",
                },
            )
            response.raise_for_status()
            data = response.json()

            results: list[Result] = []
            for video in data[:limit]:
                if video.get("type") != "video":
                    continue

                result = self._result_to_result(video)
                results.append(result)

            return results

        except httpx.HTTPError as e:
            raise SearchError(f"YouTube search failed: {e}") from e
        except Exception as e:
            raise SearchError(f"YouTube search failed: {e}") from e

    async def search_by_isrc(self, isrc: str) -> Result | None:
        """
        Search YouTube by ISRC code.

        Args:
            isrc: ISRC code to search for

        Returns:
            Matching Result or None
        """
        try:
            instance = await self._get_working_instance()
            client = await self._get_client()

            response = await client.get(
                f"{instance}/api/v1/search",
                params={
                    "q": isrc,
                    "type": "video",
                },
            )
            response.raise_for_status()
            data = response.json()

            for video in data:
                if video.get("type") == "video":
                    return self._result_to_result(video)

            return None

        except Exception:
            return None

    async def get_video_info(self, video_id: str) -> Result | None:
        """
        Get video information by ID.

        Args:
            video_id: YouTube video ID

        Returns:
            Result object or None
        """
        try:
            instance = await self._get_working_instance()
            client = await self._get_client()

            response = await client.get(f"{instance}/api/v1/videos/{video_id}")
            response.raise_for_status()
            video = response.json()

            return self._result_to_result(video)

        except Exception:
            return None

    @staticmethod
    def extract_video_id(url: str) -> str | None:
        """
        Extract video ID from YouTube URL.

        Args:
            url: YouTube URL

        Returns:
            Video ID or None
        """
        match = YOUTUBE_URL_PATTERN.search(url)
        if match:
            return match.group(1)
        return None
