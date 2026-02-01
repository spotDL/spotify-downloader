"""Base class for metadata providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from spotdl.core.types.song import Song


class MetadataProviderError(Exception):
    """Base exception for metadata provider errors."""


@dataclass
class MetadataResult:
    """
    Result from a metadata lookup.

    Contains enriched metadata that can be merged with existing Song data.
    """

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

    # Audio features (if available)
    duration_ms: int | None = None
    bpm: float | None = None
    key: str | None = None

    # Source info
    source: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for storage.

        Returns a dictionary with only non-None values.
        """
        result: dict[str, Any] = {}
        for field_name in [
            "name", "artists", "album_name", "album_artist",
            "isrc", "upc", "musicbrainz_id", "discogs_id",
            "genres", "year", "date", "track_number", "disc_number",
            "total_tracks", "total_discs", "album_art_url", "label",
            "country", "duration_ms", "bpm", "key", "source", "confidence",
        ]:
            value = getattr(self, field_name, None)
            if value is not None:
                # Include empty lists/dicts but skip None values
                if isinstance(value, (list, dict)) and not value:
                    continue
                result[field_name] = value
        return result


class MetadataProvider(ABC):
    """
    Abstract base class for metadata providers.

    Metadata providers enrich song information by looking up
    additional data from services like MusicBrainz, Discogs, etc.
    """

    name: str = "base"
    display_name: str = "Base Provider"

    # Rate limiting
    requests_per_second: float = 1.0

    def __init__(self) -> None:
        """Initialize the metadata provider."""
        pass

    @abstractmethod
    async def lookup_by_isrc(self, isrc: str) -> MetadataResult | None:
        """
        Look up metadata by ISRC code.

        Args:
            isrc: International Standard Recording Code

        Returns:
            MetadataResult if found, None otherwise
        """
        raise NotImplementedError

    async def lookup_with_raw(
        self,
        isrc: str | None = None,
        name: str | None = None,
        artist: str | None = None,
        album_name: str | None = None,
    ) -> tuple[dict[str, Any] | None, MetadataResult | None]:
        """
        Look up metadata and return both raw API response AND parsed result.

        This preserves ALL data from the source API for future-proofing.
        Subclasses should override this to return the actual raw response.

        Args:
            isrc: ISRC code (preferred if available)
            name: Track name
            artist: Artist name
            album_name: Album name (optional)

        Returns:
            Tuple of (raw_response, MetadataResult) - either may be None
        """
        # Default implementation just calls the existing methods
        result: MetadataResult | None = None

        if isrc:
            result = await self.lookup_by_isrc(isrc)

        if not result and name and artist:
            result = await self.lookup_by_name(name, artist, album_name)

        # Default implementation doesn't have raw response
        return None, result

    @abstractmethod
    async def lookup_by_name(
        self,
        track_name: str,
        artist_name: str,
        album_name: str | None = None,
    ) -> MetadataResult | None:
        """
        Look up metadata by track name and artist.

        Args:
            track_name: Track name
            artist_name: Artist name
            album_name: Optional album name for better matching

        Returns:
            MetadataResult if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[MetadataResult]:
        """
        Search for tracks by query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of MetadataResult objects
        """
        raise NotImplementedError

    async def enrich_song(self, song: Song) -> Song:
        """
        Enrich a song with additional metadata.

        Attempts to find additional metadata and merge it with
        the existing song data.

        Args:
            song: Song to enrich

        Returns:
            Enriched Song object (same instance, modified in place)
        """
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
        """
        Merge metadata result into song.

        Only fills in missing fields, doesn't overwrite existing data.

        Args:
            song: Song to update
            result: Metadata to merge
        """
        # ISRC
        if not song.isrc and result.isrc:
            song.isrc = result.isrc

        # Album (empty string is considered missing)
        if not song.album_name and result.album_name:
            song.album_name = result.album_name

        # Genres (merge, don't replace)
        if result.genres:
            existing = set(song.genres) if song.genres else set()
            song.genres = list(existing.union(result.genres))

        # Year (0 is considered missing)
        if song.year == 0 and result.year:
            song.year = result.year

        # Date (empty string is considered missing)
        if not song.date and result.date:
            song.date = result.date

        # Track number (1 is the default, only update if result has a different value)
        if song.track_number == 1 and result.track_number and result.track_number != 1:
            song.track_number = result.track_number

        # Disc number (1 is the default, only update if result has a different value)
        if song.disc_number == 1 and result.disc_number and result.disc_number != 1:
            song.disc_number = result.disc_number

        # Cover URL
        if not song.cover_url and result.album_art_url:
            song.cover_url = result.album_art_url

    async def close(self) -> None:
        """Close any open connections."""
        pass
