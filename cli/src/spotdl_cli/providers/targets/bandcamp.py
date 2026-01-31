"""Bandcamp target provider for searching audio sources."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

import httpx

from spotdl_cli.core.types import DownloadResult, TargetPlatform
from spotdl_cli.providers.base import SearchError, TargetProvider

if TYPE_CHECKING:
    from spotdl_cli.core.types import Song

logger = logging.getLogger(__name__)

# Bandcamp URL pattern
BANDCAMP_URL_PATTERN = re.compile(
    r"(?:https?://)?([^.]+)\.bandcamp\.com/(track|album)/([^/?]+)"
)


class BandcampTargetProvider(TargetProvider):
    """
    Bandcamp target provider.

    Searches Bandcamp for audio sources using the search API.
    """

    name = "bandcamp"
    display_name = "Bandcamp"

    SEARCH_URL = "https://bandcamp.com/api/bcsearch_public_api/1/autocomplete_elastic"

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize the Bandcamp provider."""
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
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _result_to_download_result(
        self, item: dict[str, Any], item_type: str
    ) -> DownloadResult | None:
        """Convert Bandcamp search result to DownloadResult."""
        try:
            if item_type == "t":  # Track
                name = item.get("name", "Unknown")
                artist = item.get("band_name", "Unknown")
                url = item.get("url", "")
                art_id = item.get("art_id")
                item_id = item.get("id", "")

                # Build cover URL
                cover_url = None
                if art_id:
                    cover_url = f"https://f4.bcbits.com/img/a{art_id}_10.jpg"

                return DownloadResult(
                    name=name,
                    artists=[artist],
                    artist=artist,
                    duration=0,  # Bandcamp search doesn't return duration
                    platform=TargetPlatform.BANDCAMP,
                    platform_id=str(item_id),
                    url=url,
                    cover_url=cover_url,
                )

            return None

        except Exception as e:
            logger.warning(f"Failed to parse Bandcamp result: {e}")
            return None

    async def search(self, song: Song, limit: int = 10) -> list[DownloadResult]:
        """Search Bandcamp for matching tracks."""
        query = self.build_search_query(song)

        try:
            client = await self._get_client()

            # Use Bandcamp's autocomplete API
            response = await client.post(
                self.SEARCH_URL,
                json={
                    "search_text": query,
                    "search_filter": "t",  # Tracks only
                    "full_page": False,
                    "fan_id": None,
                },
            )
            response.raise_for_status()
            data = response.json()

            results: list[DownloadResult] = []

            # Process track results
            autocomplete_results = data.get("auto", {}).get("results", [])
            for item in autocomplete_results[:limit]:
                item_type = item.get("type", "")
                if item_type == "t":  # Track
                    result = self._result_to_download_result(item, item_type)
                    if result:
                        results.append(result)

            return results

        except httpx.HTTPError as e:
            raise SearchError(f"Bandcamp search failed: {e}") from e
        except Exception as e:
            raise SearchError(f"Bandcamp search failed: {e}") from e

    async def get_track_info(self, url: str) -> DownloadResult | None:
        """Get track information from URL."""
        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()

            # Extract track data from page
            match = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                response.text,
                re.DOTALL,
            )

            if match:
                data = json.loads(match.group(1))

                # Handle MusicRecording type
                if data.get("@type") == "MusicRecording":
                    name = data.get("name", "Unknown")
                    artist = data.get("byArtist", {}).get("name", "Unknown")
                    duration_iso = data.get("duration", "")

                    # Parse ISO 8601 duration (e.g., "PT3M45S")
                    duration = 0
                    if duration_iso:
                        duration_match = re.match(
                            r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_iso
                        )
                        if duration_match:
                            hours = int(duration_match.group(1) or 0)
                            minutes = int(duration_match.group(2) or 0)
                            seconds = int(duration_match.group(3) or 0)
                            duration = hours * 3600 + minutes * 60 + seconds

                    # Get cover
                    cover_url = data.get("image")

                    return DownloadResult(
                        name=name,
                        artists=[artist],
                        artist=artist,
                        duration=duration,
                        platform=TargetPlatform.BANDCAMP,
                        platform_id=url,
                        url=url,
                        cover_url=cover_url,
                    )

            return None

        except Exception as e:
            logger.warning(f"Failed to get Bandcamp track info: {e}")
            return None

    @staticmethod
    def extract_track_info(url: str) -> tuple[str, str, str] | None:
        """Extract artist, type, and slug from Bandcamp URL."""
        match = BANDCAMP_URL_PATTERN.search(url)
        if match:
            return (match.group(1), match.group(2), match.group(3))
        return None
