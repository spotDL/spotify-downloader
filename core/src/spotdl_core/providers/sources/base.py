"""Base class for source providers that fetch song metadata."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spotdl_core.types.song import Song, SongList


class SourceProviderError(Exception):
    """Base exception for source provider errors."""


class InvalidURLError(SourceProviderError):
    """Raised when a URL is invalid for a provider."""


class TrackNotFoundError(SourceProviderError):
    """Raised when a track cannot be found."""


class SourceProvider(ABC):
    """
    Abstract base class for source providers.

    Source providers fetch song metadata from streaming platforms
    like Spotify, Deezer, Apple Music, etc.
    """

    # Provider identification
    name: str = "base"
    display_name: str = "Base Provider"

    # URL patterns this provider handles
    url_patterns: list[re.Pattern[str]] = []

    def __init__(self) -> None:
        """Initialize the source provider."""
        pass

    @classmethod
    def matches_url(cls, url: str) -> bool:
        """
        Check if this provider can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if this provider can handle the URL
        """
        return any(pattern.search(url) for pattern in cls.url_patterns)

    @classmethod
    def extract_id(cls, url: str) -> str | None:
        """
        Extract the resource ID from a URL.

        Args:
            url: URL to extract ID from

        Returns:
            Resource ID or None if not found
        """
        for pattern in cls.url_patterns:
            match = pattern.search(url)
            if match and match.groups():
                return match.group(1)
        return None

    @classmethod
    def get_url_type(cls, url: str) -> str | None:
        """
        Determine the type of resource from URL (track, album, playlist, artist).

        Args:
            url: URL to analyze

        Returns:
            Resource type or None
        """
        url_lower = url.lower()
        if "track" in url_lower or "song" in url_lower:
            return "track"
        if "album" in url_lower:
            return "album"
        if "playlist" in url_lower:
            return "playlist"
        if "artist" in url_lower:
            return "artist"
        return None

    @abstractmethod
    async def get_track(self, url: str) -> Song:
        """
        Fetch a single track by URL.

        Args:
            url: Track URL

        Returns:
            Song object with metadata

        Raises:
            InvalidURLError: If URL is invalid
            TrackNotFoundError: If track cannot be found
        """
        raise NotImplementedError

    @abstractmethod
    async def get_album(self, url: str) -> SongList:
        """
        Fetch an album by URL.

        Args:
            url: Album URL

        Returns:
            SongList containing album tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If album cannot be found
        """
        raise NotImplementedError

    @abstractmethod
    async def get_playlist(self, url: str) -> SongList:
        """
        Fetch a playlist by URL.

        Args:
            url: Playlist URL

        Returns:
            SongList containing playlist tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If playlist cannot be found
        """
        raise NotImplementedError

    @abstractmethod
    async def get_artist(self, url: str) -> SongList:
        """
        Fetch all tracks from an artist by URL.

        Args:
            url: Artist URL

        Returns:
            SongList containing artist's tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If artist cannot be found
        """
        raise NotImplementedError

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[Song]:
        """
        Search for tracks by query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching Song objects
        """
        raise NotImplementedError

    async def get_songs_from_url(self, url: str) -> list[Song]:
        """
        Get songs from any supported URL type.

        Automatically detects the URL type and calls the appropriate method.

        Args:
            url: URL to fetch songs from

        Returns:
            List of Song objects
        """
        url_type = self.get_url_type(url)

        if url_type == "track":
            song = await self.get_track(url)
            return [song]
        elif url_type == "album":
            album = await self.get_album(url)
            return list(album.songs)
        elif url_type == "playlist":
            playlist = await self.get_playlist(url)
            return list(playlist.songs)
        elif url_type == "artist":
            artist = await self.get_artist(url)
            return list(artist.songs)
        else:
            # Try as track by default
            song = await self.get_track(url)
            return [song]
