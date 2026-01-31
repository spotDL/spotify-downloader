"""SoundCloud target provider for searching audio sources."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import httpx
from bs4 import BeautifulSoup

from spotdl_core.types.result import Result, TargetPlatform
from spotdl_core.providers.targets.base import (
    SearchError,
    TargetProvider,
)

if TYPE_CHECKING:
    from spotdl_core.types.song import Song

# SoundCloud URL pattern
SOUNDCLOUD_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?soundcloud\.com/([^/]+)/([^/?]+)"
)


class SoundCloudProvider(TargetProvider):
    """
    SoundCloud target provider.

    Searches SoundCloud for audio sources using web scraping.
    """

    name = "soundcloud"
    display_name = "SoundCloud"

    def __init__(self, timeout: float = 30.0) -> None:
        """
        Initialize the SoundCloud provider.

        Args:
            timeout: Request timeout in seconds
        """
        super().__init__()
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _extract_hydration_data(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """
        Extract hydration data from SoundCloud page.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of hydration data objects
        """
        for script in soup.find_all("script"):
            text = script.string or ""
            if "__sc_hydration" in text:
                match = re.search(r"__sc_hydration\s*=\s*(\[.*?\]);", text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except json.JSONDecodeError:
                        pass
        return []

    def _track_to_result(self, track: dict[str, Any]) -> Result:
        """
        Convert SoundCloud track data to Result object.

        Args:
            track: SoundCloud track data

        Returns:
            Result object
        """
        # Get artist info
        user = track.get("user", {})
        artist_name = user.get("username", "Unknown")

        # Get cover URL
        cover_url = track.get("artwork_url")
        if cover_url:
            cover_url = cover_url.replace("-large.", "-t500x500.")
        elif user.get("avatar_url"):
            cover_url = user.get("avatar_url")

        # Parse duration (in milliseconds)
        duration_ms = track.get("duration", 0)
        duration = duration_ms // 1000 if duration_ms else 0

        return Result(
            name=track.get("title", "Unknown"),
            artists=[artist_name],
            artist=artist_name,
            duration=duration,
            platform=TargetPlatform.SOUNDCLOUD,
            platform_id=str(track.get("id", "")),
            url=track.get("permalink_url", ""),
            cover_url=cover_url,
            views=track.get("playback_count"),
        )

    async def search(self, song: Song, limit: int = 10) -> list[Result]:
        """
        Search SoundCloud for matching tracks.

        Args:
            song: Song to search for
            limit: Maximum number of results

        Returns:
            List of Result objects
        """
        query = self.build_search_query(song)

        try:
            import urllib.parse

            client = await self._get_client()
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://soundcloud.com/search/sounds?q={encoded_query}"

            response = await client.get(search_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            hydration_data = self._extract_hydration_data(soup)

            # Find search results in hydration data
            results: list[Result] = []
            for item in hydration_data:
                data = item.get("data", {})
                if isinstance(data, dict) and data.get("collection"):
                    for track in data.get("collection", []):
                        if track.get("kind") == "track" and track.get("id"):
                            result = self._track_to_result(track)
                            results.append(result)
                            if len(results) >= limit:
                                break
                if len(results) >= limit:
                    break

            return results

        except httpx.HTTPError as e:
            raise SearchError(f"SoundCloud search failed: {e}") from e
        except Exception as e:
            raise SearchError(f"SoundCloud search failed: {e}") from e

    async def get_track_info(self, url: str) -> Result | None:
        """
        Get track information from URL.

        Args:
            url: SoundCloud track URL

        Returns:
            Result object or None
        """
        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            hydration_data = self._extract_hydration_data(soup)

            for item in hydration_data:
                if item.get("hydratable") == "sound":
                    track_data = item.get("data", {})
                    if track_data:
                        return self._track_to_result(track_data)

            return None

        except Exception:
            return None

    @staticmethod
    def extract_track_info(url: str) -> tuple[str, str] | None:
        """
        Extract user and track slug from SoundCloud URL.

        Args:
            url: SoundCloud URL

        Returns:
            Tuple of (user, slug) or None
        """
        match = SOUNDCLOUD_URL_PATTERN.search(url)
        if match:
            return (match.group(1), match.group(2))
        return None
