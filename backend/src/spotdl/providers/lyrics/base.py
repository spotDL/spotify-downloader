"""Base lyrics provider class."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, ClassVar

import httpx
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class BaseLyricsProvider(ABC):
    """
    Abstract base class for lyrics providers.

    Subclasses must implement:
    - get_results(): Search for matching songs
    - extract_lyrics(): Extract lyrics from a URL

    The base class provides:
    - Shared HTTP client management
    - Fuzzy title matching
    - Rate limiting via semaphore
    """

    name: ClassVar[str] = "Base"
    max_concurrent_requests: ClassVar[int] = 3

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        """
        Initialize the provider.

        Args:
            client: Optional shared httpx client for connection pooling.
        """
        self._client = client
        self._owns_client = client is None
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client."""
        if self._client is None:
            raise RuntimeError(
                "Provider not initialized. Use 'async with provider:' or call __aenter__ first."
            )
        return self._client

    async def __aenter__(self) -> BaseLyricsProvider:
        """Async context manager entry."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers=self.headers,
            )
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def get_results(self, name: str, artists: list[str], **kwargs: Any) -> dict[str, str]:
        """
        Search for songs matching name and artists.

        Args:
            name: Song title
            artists: List of artist names

        Returns:
            Dict mapping song titles to URLs
        """
        ...

    @abstractmethod
    async def extract_lyrics(self, url: str) -> str | None:
        """
        Extract lyrics from a URL.

        Args:
            url: URL to extract lyrics from

        Returns:
            Lyrics text or None if extraction failed
        """
        ...

    def _calculate_score(self, result_title: str, name: str, artists: list[str]) -> float:
        """
        Calculate match score for a search result.

        Args:
            result_title: Title from search result
            name: Original song name
            artists: Original artist names

        Returns:
            Score from 0-100
        """
        result_lower = result_title.lower()
        name_lower = name.lower()

        # Check if all artists are in the title
        artists_in_title = sum(1 for artist in artists if artist.lower() in result_lower)
        artist_bonus = (artists_in_title / max(len(artists), 1)) * 20

        # Fuzzy match on song name
        name_score = fuzz.ratio(name_lower, result_lower)

        return min(100.0, name_score + artist_bonus)

    def _find_best_match(
        self, results: dict[str, str], name: str, artists: list[str]
    ) -> tuple[str, str] | None:
        """
        Find the best matching result.

        Args:
            results: Dict of title -> URL
            name: Song name to match
            artists: Artist names

        Returns:
            Tuple of (title, URL) for best match, or None
        """
        if not results:
            return None

        best_score = 0.0
        best_match: tuple[str, str] | None = None

        for title, url in results.items():
            score = self._calculate_score(title, name, artists)
            if score > best_score:
                best_score = score
                best_match = (title, url)

        # Require minimum score
        if best_score < 50:
            return None

        return best_match

    async def get_lyrics(self, name: str, artists: list[str]) -> str | None:
        """
        Get lyrics for a song.

        This is the main entry point that searches and extracts lyrics.

        Args:
            name: Song name
            artists: Artist names

        Returns:
            Lyrics text or None if not found
        """
        try:
            # Search for matches
            results = await self.get_results(name, artists)
            if not results:
                logger.debug(
                    "%s: No results for %s - %s",
                    self.name,
                    name,
                    ", ".join(artists),
                )
                return None

            # Find best match
            match = self._find_best_match(results, name, artists)
            if not match:
                logger.debug(
                    "%s: No good match for %s - %s",
                    self.name,
                    name,
                    ", ".join(artists),
                )
                return None

            title, url = match
            logger.debug("%s: Matched '%s' -> %s", self.name, title, url)

            # Extract lyrics
            lyrics = await self.extract_lyrics(url)
            if not lyrics:
                logger.debug("%s: Failed to extract lyrics from %s", self.name, url)
                return None

            return self._clean_lyrics(lyrics)

        except Exception as exc:
            logger.warning("%s: Error getting lyrics: %s", self.name, exc)
            return None

    def _clean_lyrics(self, lyrics: str) -> str:
        """
        Clean and normalize lyrics text.

        Args:
            lyrics: Raw lyrics text

        Returns:
            Cleaned lyrics
        """
        # Remove multiple blank lines
        lyrics = re.sub(r"\n{3,}", "\n\n", lyrics)

        # Normalize whitespace
        lyrics = lyrics.strip()

        return lyrics
