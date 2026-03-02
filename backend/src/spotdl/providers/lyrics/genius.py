"""Genius lyrics provider (async)."""

from __future__ import annotations

import logging
from typing import Any, ClassVar
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from spotdl.providers.lyrics.base import BaseLyricsProvider

logger = logging.getLogger(__name__)


class GeniusProvider(BaseLyricsProvider):
    """
    Genius lyrics provider.

    Uses Genius API for search and web scraping for lyrics extraction.
    Requires a Genius API access token for search functionality.
    """

    name: ClassVar[str] = "Genius"
    max_concurrent_requests: ClassVar[int] = 3

    def __init__(self, access_token: str, client: httpx.AsyncClient | None = None) -> None:
        """
        Initialize Genius provider.

        Args:
            access_token: Genius API access token
            client: Optional shared httpx client
        """
        super().__init__(client)
        self.access_token = access_token
        self.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
            }
        )

    async def get_results(self, name: str, artists: list[str], **kwargs: Any) -> dict[str, str]:
        """Search Genius API for songs."""
        query = f"{name} {' '.join(artists)}"

        try:
            response = await self.client.get(
                "https://api.genius.com/search",
                params={"q": query},
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()

            results: dict[str, str] = {}
            hits = data.get("response", {}).get("hits", [])

            for hit in hits[:10]:  # Limit to top 10 results
                result = hit.get("result", {})
                title = result.get("full_title", "")
                url = result.get("url", "")
                if title and url:
                    results[title] = url

            return results

        except Exception as exc:
            logger.debug("Genius search failed: %s", exc)
            return {}

    async def extract_lyrics(self, url: str) -> str | None:
        """
        Extract lyrics from a Genius page.

        Handles both old and new Genius page layouts.
        """
        for attempt in range(3):
            try:
                response = await self.client.get(url, headers=self.headers)
                if not response.is_success:
                    continue

                soup = BeautifulSoup(response.text.replace("<br/>", "\n"), "html.parser")

                # Remove lyrics header if present
                lyrics_header = soup.select_one("div[class^=LyricsHeader__Container]")
                if lyrics_header:
                    lyrics_header.decompose()

                # Try old format
                lyrics_div = soup.select_one("div.lyrics")
                if lyrics_div:
                    return lyrics_div.get_text().strip()

                # Try new format
                lyrics_containers = soup.select("div[class^=Lyrics__Container]")
                if lyrics_containers:
                    lyrics = "\n".join(con.get_text() for con in lyrics_containers)
                    return lyrics.strip() if lyrics else None

            except Exception as exc:
                logger.debug("Genius scrape attempt %d failed: %s", attempt + 1, exc)
                continue

        return None


class GeniusWebProvider(BaseLyricsProvider):
    """
    Genius provider that uses web scraping only (no API token required).

    This is a fallback for when no Genius API token is available.
    """

    name: ClassVar[str] = "GeniusWeb"
    max_concurrent_requests: ClassVar[int] = 2

    async def get_results(self, name: str, artists: list[str], **kwargs: Any) -> dict[str, str]:
        """Search Genius via web scraping."""
        query = quote(f"{name} {artists[0]}")
        search_url = f"https://genius.com/api/search/multi?q={query}"

        try:
            response = await self.client.get(search_url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            results: dict[str, str] = {}
            sections = data.get("response", {}).get("sections", [])

            for section in sections:
                if section.get("type") != "song":
                    continue
                for hit in section.get("hits", [])[:10]:
                    result = hit.get("result", {})
                    title = result.get("full_title", "")
                    url = result.get("url", "")
                    if title and url:
                        results[title] = url

            return results

        except Exception as exc:
            logger.debug("Genius web search failed: %s", exc)
            return {}

    async def extract_lyrics(self, url: str) -> str | None:
        """Extract lyrics from Genius page."""
        # Same extraction logic as GeniusProvider
        for attempt in range(3):
            try:
                response = await self.client.get(url, headers=self.headers)
                if not response.is_success:
                    continue

                soup = BeautifulSoup(response.text.replace("<br/>", "\n"), "html.parser")

                lyrics_header = soup.select_one("div[class^=LyricsHeader__Container]")
                if lyrics_header:
                    lyrics_header.decompose()

                lyrics_div = soup.select_one("div.lyrics")
                if lyrics_div:
                    return lyrics_div.get_text().strip()

                lyrics_containers = soup.select("div[class^=Lyrics__Container]")
                if lyrics_containers:
                    lyrics = "\n".join(con.get_text() for con in lyrics_containers)
                    return lyrics.strip() if lyrics else None

            except Exception as exc:
                logger.debug("Genius scrape attempt %d failed: %s", attempt + 1, exc)
                continue

        return None
