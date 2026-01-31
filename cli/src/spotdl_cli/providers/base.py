"""Base classes for source and target providers."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from spotdl_cli.core.types import DownloadResult, Song


# ============== Exceptions ==============


class ProviderError(Exception):
    """Base exception for provider errors."""


class SourceProviderError(ProviderError):
    """Base exception for source provider errors."""


class InvalidURLError(SourceProviderError):
    """Raised when a URL is invalid for a provider."""


class TrackNotFoundError(SourceProviderError):
    """Raised when a track cannot be found."""


class TargetProviderError(ProviderError):
    """Base exception for target provider errors."""


class SearchError(TargetProviderError):
    """Raised when search fails."""


class NoResultsError(TargetProviderError):
    """Raised when no results are found."""


class MetadataProviderError(ProviderError):
    """Base exception for metadata provider errors."""


# ============== Data Classes ==============


@dataclass
class SongList:
    """List of songs from a source (album, playlist, artist)."""

    name: str
    url: str
    platform: str
    urls: tuple[str, ...]
    songs: tuple[Any, ...]  # tuple[Song, ...]


@dataclass
class MetadataResult:
    """Result from a metadata lookup."""

    # Basic info
    name: str | None = None
    artists: list[str] | None = None
    album_name: str | None = None
    album_artist: str | None = None

    # Identifiers
    isrc: str | None = None
    upc: str | None = None
    musicbrainz_id: str | None = None
    discogs_id: str | None = None

    # Additional metadata
    genres: list[str] = field(default_factory=list)
    year: int | None = None
    date: str | None = None
    track_number: int | None = None
    disc_number: int | None = None
    total_tracks: int | None = None
    total_discs: int | None = None

    # Album info
    album_art_url: str | None = None
    label: str | None = None
    country: str | None = None

    # Audio features
    duration_ms: int | None = None
    bpm: float | None = None
    key: str | None = None

    # Source info
    source: str = ""
    confidence: float = 1.0


# ============== Base Classes ==============


class SourceProvider(ABC):
    """
    Abstract base class for source providers.

    Source providers fetch song metadata from streaming platforms
    like Spotify, Deezer, Apple Music, etc.
    """

    name: str = "base"
    display_name: str = "Base Provider"
    url_patterns: ClassVar[list[re.Pattern[str]]] = []

    def __init__(self) -> None:  # noqa: B027
        """Initialize the source provider."""

    @classmethod
    def matches_url(cls, url: str) -> bool:
        """Check if this provider can handle the given URL."""
        return any(pattern.search(url) for pattern in cls.url_patterns)

    @classmethod
    def extract_id(cls, url: str) -> str | None:
        """Extract the resource ID from a URL."""
        for pattern in cls.url_patterns:
            match = pattern.search(url)
            if match and match.groups():
                return match.group(1)
        return None

    @classmethod
    def get_url_type(cls, url: str) -> str | None:
        """Determine the type of resource from URL (track, album, playlist, artist)."""
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
        """Fetch a single track by URL."""
        raise NotImplementedError

    @abstractmethod
    async def get_album(self, url: str) -> SongList:
        """Fetch an album by URL."""
        raise NotImplementedError

    @abstractmethod
    async def get_playlist(self, url: str) -> SongList:
        """Fetch a playlist by URL."""
        raise NotImplementedError

    @abstractmethod
    async def get_artist(self, url: str) -> SongList:
        """Fetch all tracks from an artist by URL."""
        raise NotImplementedError

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[Song]:
        """Search for tracks by query."""
        raise NotImplementedError

    async def get_songs_from_url(self, url: str) -> list[Song]:
        """Get songs from any supported URL type."""
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

    async def close(self) -> None:  # noqa: B027
        """Close any open resources."""

    async def __aenter__(self) -> SourceProvider:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.close()


class TargetProvider(ABC):
    """
    Abstract base class for target providers.

    Target providers search for audio sources on platforms
    like YouTube, SoundCloud, Bandcamp, etc.
    """

    name: str = "base"
    display_name: str = "Base Provider"

    def __init__(self) -> None:  # noqa: B027
        """Initialize the target provider."""

    @abstractmethod
    async def search(self, song: Song, limit: int = 10) -> list[DownloadResult]:
        """Search for matching audio sources for a song."""
        raise NotImplementedError

    async def get_best_match(self, song: Song) -> DownloadResult | None:
        """Get the best matching result for a song."""
        results = await self.search(song, limit=1)
        return results[0] if results else None

    def build_search_query(self, song: Song) -> str:
        """Build a search query string from song metadata."""
        query = f"{song.artist} - {song.name}"
        # Clean up the query
        query = query.replace("(Official Audio)", "")
        query = query.replace("(Official Video)", "")
        query = query.replace("(Lyrics)", "")
        return query.strip()

    async def close(self) -> None:  # noqa: B027
        """Close any open resources."""

    async def __aenter__(self) -> TargetProvider:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.close()


class MetadataProvider(ABC):
    """
    Abstract base class for metadata providers.

    Metadata providers enrich song information by looking up
    additional data from services like MusicBrainz, Discogs, etc.
    """

    name: str = "base"
    display_name: str = "Base Provider"
    requests_per_second: float = 1.0

    def __init__(self) -> None:  # noqa: B027
        """Initialize the metadata provider."""

    @abstractmethod
    async def lookup_by_isrc(self, isrc: str) -> MetadataResult | None:
        """Look up metadata by ISRC code."""
        raise NotImplementedError

    @abstractmethod
    async def lookup_by_name(
        self,
        track_name: str,
        artist_name: str,
        album_name: str | None = None,
    ) -> MetadataResult | None:
        """Look up metadata by track name and artist."""
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[MetadataResult]:
        """Search for tracks by query."""
        raise NotImplementedError

    async def enrich_song(self, song: Song) -> Song:
        """Enrich a song with additional metadata."""
        result: MetadataResult | None = None

        # Try ISRC first (most accurate)
        if song.isrc:
            result = await self.lookup_by_isrc(song.isrc)

        # Fall back to name/artist lookup
        if not result:
            result = await self.lookup_by_name(
                track_name=song.name,
                artist_name=song.artist,
                album_name=song.album_name,
            )

        if result:
            self._merge_metadata(song, result)

        return song

    def _merge_metadata(self, song: Song, result: MetadataResult) -> None:
        """Merge metadata result into song (only fills missing fields)."""
        if not song.isrc and result.isrc:
            song.isrc = result.isrc

        if not song.album_name and result.album_name:
            song.album_name = result.album_name

        if result.genres:
            existing = set(song.genres) if song.genres else set()
            song.genres = list(existing.union(result.genres))

        if song.year == 0 and result.year:
            song.year = result.year

        if not song.date and result.date:
            song.date = result.date

        if not song.cover_url and result.album_art_url:
            song.cover_url = result.album_art_url

    async def close(self) -> None:  # noqa: B027
        """Close any open connections."""
