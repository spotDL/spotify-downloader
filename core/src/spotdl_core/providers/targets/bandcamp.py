"""Bandcamp target provider for searching audio sources."""

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

# Bandcamp URL pattern
BANDCAMP_URL_PATTERN = re.compile(
    r"(?:https?://)?([^.]+)\.bandcamp\.com/(track|album)/([^/?]+)"
)


class BandcampProvider(TargetProvider):
    """
    Bandcamp target provider.

    Searches Bandcamp for audio sources using web scraping.
    """

    name = "bandcamp"
    display_name = "Bandcamp"

    def __init__(self, timeout: float = 30.0) -> None:
        """
        Initialize the Bandcamp provider.

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

    def _parse_search_result(self, result_elem: Any) -> Result | None:
        """
        Parse a search result element from Bandcamp.

        Args:
            result_elem: BeautifulSoup element for search result

        Returns:
            Result object or None
        """
        try:
            # Get track URL
            link = result_elem.find("a", class_="artcont")
            if not link:
                return None

            track_url = link.get("href", "")
            if not track_url or "/track/" not in track_url:
                return None

            # Get basic info from search result
            heading = result_elem.find("div", class_="heading")
            subhead = result_elem.find("div", class_="subhead")

            name = heading.get_text(strip=True) if heading else ""
            artist_album = subhead.get_text(strip=True) if subhead else ""

            # Parse "by Artist from Album"
            artist_name = "Unknown"
            album_name = ""
            if " by " in artist_album:
                parts = artist_album.split(" by ", 1)
                if len(parts) > 1:
                    artist_part = parts[1]
                    if " from " in artist_part:
                        artist_album_parts = artist_part.split(" from ")
                        artist_name = artist_album_parts[0].strip()
                        if len(artist_album_parts) > 1:
                            album_name = artist_album_parts[1].strip()
                    else:
                        artist_name = artist_part.strip()

            # Get cover
            img = result_elem.find("img")
            cover_url = img.get("src") if img else None
            if cover_url:
                # Get higher resolution
                cover_url = re.sub(r"_\d+\.jpg$", "_10.jpg", cover_url)

            return Result(
                name=name,
                artists=[artist_name],
                artist=artist_name,
                duration=0,  # Duration not available in search results
                platform=TargetPlatform.BANDCAMP,
                platform_id="",  # ID not available in search results
                url=track_url,
                album_name=album_name,
                cover_url=cover_url,
            )

        except Exception:
            return None

    async def search(self, song: Song, limit: int = 10) -> list[Result]:
        """
        Search Bandcamp for matching tracks.

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
            search_url = f"https://bandcamp.com/search?q={encoded_query}&item_type=t"

            response = await client.get(search_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Find search results
            results: list[Result] = []
            result_elems = soup.find_all("li", class_="searchresult")

            for elem in result_elems[:limit]:
                result = self._parse_search_result(elem)
                if result:
                    results.append(result)

            return results

        except httpx.HTTPError as e:
            raise SearchError(f"Bandcamp search failed: {e}") from e
        except Exception as e:
            raise SearchError(f"Bandcamp search failed: {e}") from e

    async def get_track_info(self, url: str) -> Result | None:
        """
        Get track information from URL.

        Args:
            url: Bandcamp track URL

        Returns:
            Result object or None
        """
        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Extract TralbumData
            for script in soup.find_all("script"):
                text = script.string or ""
                if "TralbumData" in text:
                    match = re.search(r"TralbumData\s*=\s*(\{.*?\});", text, re.DOTALL)
                    if match:
                        try:
                            json_str = match.group(1)
                            json_str = re.sub(r"//.*?\n", "\n", json_str)
                            json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
                            data = json.loads(json_str)

                            trackinfo = data.get("trackinfo", [])
                            if trackinfo:
                                track = trackinfo[0]

                                # Get cover URL
                                art_id = data.get("art_id")
                                cover_url = f"https://f4.bcbits.com/img/a{art_id}_10.jpg" if art_id else None

                                return Result(
                                    name=track.get("title", "Unknown"),
                                    artists=[data.get("artist", "Unknown")],
                                    artist=data.get("artist", "Unknown"),
                                    duration=int(track.get("duration", 0)),
                                    platform=TargetPlatform.BANDCAMP,
                                    platform_id=str(track.get("id", "")),
                                    url=url,
                                    album_name=data.get("current", {}).get("title", ""),
                                    cover_url=cover_url,
                                )
                        except json.JSONDecodeError:
                            pass

            return None

        except Exception:
            return None

    @staticmethod
    def extract_url_info(url: str) -> dict[str, str] | None:
        """
        Extract subdomain, type, and slug from Bandcamp URL.

        Args:
            url: Bandcamp URL

        Returns:
            Dictionary with subdomain, type, slug or None
        """
        match = BANDCAMP_URL_PATTERN.search(url)
        if match:
            return {
                "subdomain": match.group(1),
                "type": match.group(2),
                "slug": match.group(3),
            }
        return None
