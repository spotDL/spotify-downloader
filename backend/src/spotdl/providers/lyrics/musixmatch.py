"""MusixMatch lyrics provider (async)."""

from __future__ import annotations

import logging
from typing import Any, ClassVar
from urllib.parse import quote

from bs4 import BeautifulSoup

from spotdl.providers.lyrics.base import BaseLyricsProvider

logger = logging.getLogger(__name__)


class MusixMatchProvider(BaseLyricsProvider):
    """MusixMatch lyrics provider via web scraping."""

    name: ClassVar[str] = "MusixMatch"
    max_concurrent_requests: ClassVar[int] = 2

    async def get_results(
        self, name: str, artists: list[str], track_search: bool = False, **kwargs: Any
    ) -> dict[str, str]:
        """Search MusixMatch for lyrics."""
        # Filter artists not in song name
        artists_filtered = [artist for artist in artists if artist.lower() not in name.lower()]
        artists_str = ", ".join(artists_filtered) if artists_filtered else artists[0]

        # URL-encode query
        query = quote(f"{name} - {artists_str}", safe="")
        if track_search:
            query += "/tracks"

        search_url = f"https://www.musixmatch.com/search/{query}"

        try:
            response = await self.client.get(search_url, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            song_links = soup.select("a[href^='/lyrics/']")

            if not song_links and not track_search:
                # Retry with track search
                return await self.get_results(name, artists, track_search=True)

            results: dict[str, str] = {}
            for link in song_links:
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if title and href:
                    results[title] = f"https://www.musixmatch.com{href}"

            return results

        except Exception as exc:
            logger.debug("MusixMatch search failed: %s", exc)
            return {}

    async def extract_lyrics(self, url: str) -> str | None:
        """Extract lyrics from MusixMatch page."""
        try:
            response = await self.client.get(url, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            lyrics_paragraphs = soup.select("p.mxm-lyrics__content")

            if not lyrics_paragraphs:
                return None

            lyrics = "\n".join(p.get_text() for p in lyrics_paragraphs)
            return lyrics.strip() if lyrics else None

        except Exception as exc:
            logger.debug("MusixMatch extraction failed: %s", exc)
            return None
