"""Base class for target providers that search for audio sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spotdl_core.core.types.result import Result
    from spotdl_core.core.types.song import Song


class TargetProviderError(Exception):
    """Base exception for target provider errors."""


class SearchError(TargetProviderError):
    """Raised when search fails."""


class NoResultsError(TargetProviderError):
    """Raised when no results are found."""


class TargetProvider(ABC):
    """
    Abstract base class for target providers.

    Target providers search for audio sources on platforms
    like YouTube, SoundCloud, Bandcamp, etc. They take song
    metadata and return matching results.
    """

    # Provider identification
    name: str = "base"
    display_name: str = "Base Provider"

    def __init__(self) -> None:
        """Initialize the target provider."""
        pass

    @abstractmethod
    async def search(self, song: Song, limit: int = 10) -> list[Result]:
        """
        Search for matching audio sources for a song.

        Args:
            song: Song to search for
            limit: Maximum number of results to return

        Returns:
            List of Result objects with potential matches

        Raises:
            SearchError: If search fails
        """
        raise NotImplementedError

    async def get_best_match(self, song: Song) -> Result | None:
        """
        Get the best matching result for a song.

        This is a convenience method that searches and returns
        the top result. Override this if you have a more efficient
        way to get a single match.

        Args:
            song: Song to match

        Returns:
            Best matching Result or None if no matches found
        """
        results = await self.search(song, limit=1)
        return results[0] if results else None

    def build_search_query(self, song: Song) -> str:
        """
        Build a search query string from song metadata.

        Args:
            song: Song to build query for

        Returns:
            Search query string
        """
        # Basic query: artist - name
        query = f"{song.artist} - {song.name}"

        # Clean up the query
        # Remove common suffixes that might interfere with search
        query = query.replace("(Official Audio)", "")
        query = query.replace("(Official Video)", "")
        query = query.replace("(Lyrics)", "")
        query = query.strip()

        return query

    async def close(self) -> None:
        """
        Close any open resources.

        Override this if the provider uses resources that need cleanup.
        """
        pass

    async def __aenter__(self) -> "TargetProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object) -> None:
        """Async context manager exit."""
        await self.close()
