"""Piped target provider for searching audio sources."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import httpx

from spotdl_core.types.result import Result, TargetPlatform
from spotdl_core.providers.targets.base import (
    SearchError,
    TargetProvider,
)

if TYPE_CHECKING:
    from spotdl_core.types.song import Song

# Piped video URL pattern (same as YouTube)
PIPED_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:piped\.(?:video|kavin\.rocks|silkky\.cloud)|pipedapi\.kavin\.rocks)/watch\?v=([a-zA-Z0-9_-]{11})"
)


class PipedProvider(TargetProvider):
    """
    Piped target provider.

    Piped is an alternative privacy-friendly frontend for YouTube.
    This provider uses Piped instances to search for audio sources.
    """

    name = "piped"
    display_name = "Piped"

    # List of Piped API instances to try
    PIPED_INSTANCES = [
        "https://pipedapi.kavin.rocks",
        "https://api.piped.yt",
        "https://pipedapi.adminforge.de",
        "https://api.piped.privacydev.net",
        "https://pipedapi.in.projectsegfau.lt",
    ]

    def __init__(
        self,
        timeout: float = 30.0,
        piped_instance: str | None = None,
    ) -> None:
        """
        Initialize the Piped provider.

        Args:
            timeout: Request timeout in seconds
            piped_instance: Custom Piped API instance URL
        """
        super().__init__()
        self._timeout = timeout
        self._piped_instance = piped_instance
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
        Find a working Piped API instance.

        Returns:
            Working instance URL

        Raises:
            SearchError: If no working instance found
        """
        if self._piped_instance:
            return self._piped_instance

        if self._working_instance:
            return self._working_instance

        client = await self._get_client()

        for instance in self.PIPED_INSTANCES:
            try:
                response = await client.get(f"{instance}/healthcheck", timeout=5.0)
                if response.status_code == 200:
                    self._working_instance = instance
                    return instance
            except httpx.HTTPError:
                continue

        raise SearchError("No working Piped instance found")

    def _item_to_result(self, item: dict[str, Any]) -> Result:
        """
        Convert Piped search item to Result object.

        Args:
            item: Item data from Piped API

        Returns:
            Result object
        """
        # Piped returns URL in format "/watch?v=VIDEO_ID"
        url = item.get("url", "")
        video_id = ""
        if url.startswith("/watch?v="):
            video_id = url.replace("/watch?v=", "")

        # Get thumbnail
        thumbnail = item.get("thumbnail", "")

        # Get uploader (artist)
        uploader = item.get("uploaderName", item.get("uploader", "Unknown"))

        return Result(
            name=item.get("title", "Unknown"),
            artists=[uploader],
            artist=uploader,
            duration=item.get("duration", 0),
            platform=TargetPlatform.PIPED,
            platform_id=video_id,
            url=f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
            cover_url=thumbnail,
            views=item.get("views"),
            verified=item.get("uploaderVerified", False),
        )

    async def search(self, song: Song, limit: int = 10) -> list[Result]:
        """
        Search Piped for matching videos.

        Args:
            song: Song to search for
            limit: Maximum number of results

        Returns:
            List of Result objects
        """
        query = self.build_search_query(song)

        try:
            import urllib.parse

            instance = await self._get_working_instance()
            client = await self._get_client()

            encoded_query = urllib.parse.quote(query)

            response = await client.get(
                f"{instance}/search",
                params={
                    "q": query,
                    "filter": "videos",
                },
            )
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])

            results: list[Result] = []
            for item in items[:limit]:
                # Only include video items
                if item.get("type") != "stream":
                    continue

                result = self._item_to_result(item)
                results.append(result)

            return results

        except httpx.HTTPError as e:
            raise SearchError(f"Piped search failed: {e}") from e
        except Exception as e:
            raise SearchError(f"Piped search failed: {e}") from e

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

            response = await client.get(f"{instance}/streams/{video_id}")
            response.raise_for_status()
            data = response.json()

            return Result(
                name=data.get("title", "Unknown"),
                artists=[data.get("uploader", "Unknown")],
                artist=data.get("uploader", "Unknown"),
                duration=data.get("duration", 0),
                platform=TargetPlatform.PIPED,
                platform_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                cover_url=data.get("thumbnailUrl"),
                views=data.get("views"),
                verified=data.get("uploaderVerified", False),
            )

        except Exception:
            return None

    async def get_audio_stream_url(self, video_id: str) -> str | None:
        """
        Get the audio stream URL for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            Audio stream URL or None
        """
        try:
            instance = await self._get_working_instance()
            client = await self._get_client()

            response = await client.get(f"{instance}/streams/{video_id}")
            response.raise_for_status()
            data = response.json()

            # Get audio streams
            audio_streams = data.get("audioStreams", [])
            if not audio_streams:
                return None

            # Sort by bitrate (highest first)
            sorted_streams = sorted(
                audio_streams,
                key=lambda x: x.get("bitrate", 0),
                reverse=True,
            )

            # Return highest quality audio stream
            return sorted_streams[0].get("url")

        except Exception:
            return None

    @staticmethod
    def extract_video_id(url: str) -> str | None:
        """
        Extract video ID from Piped or YouTube URL.

        Args:
            url: Piped or YouTube URL

        Returns:
            Video ID or None
        """
        # Try Piped pattern
        match = PIPED_URL_PATTERN.search(url)
        if match:
            return match.group(1)

        # Try standard YouTube pattern
        yt_match = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", url)
        if yt_match:
            return yt_match.group(1)

        # Try youtu.be pattern
        short_match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
        if short_match:
            return short_match.group(1)

        return None
