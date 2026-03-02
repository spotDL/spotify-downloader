"""Type definitions for SpotDL CLI.

Imports shared types from spotdl_core and defines CLI-specific types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

# Re-export shared types from spotdl_core
from spotdl_core import Platform, Result, Song, SongList, TargetPlatform


@dataclass
class DownloadResult:
    """
    CLI-specific result type with score tracking.

    Wraps the core Result type and adds a mutable score field
    for ranking during matching.
    """

    name: str
    artists: list[str]
    artist: str
    duration: int

    platform: TargetPlatform
    platform_id: str
    url: str

    # Match info
    verified: bool = False
    score: float = 0.0

    # Optional
    album_name: str | None = None
    cover_url: str | None = None
    views: int | None = None

    # Search metadata (for matching engine compatibility)
    isrc_search: bool = False
    search_query: str | None = None

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return f"{self.artist} - {self.name}"

    def __hash__(self) -> int:
        """Make DownloadResult hashable for use in dict keys."""
        return hash((self.platform, self.platform_id, self.url))

    def __eq__(self, other: object) -> bool:
        """Check equality based on platform and ID."""
        if not isinstance(other, DownloadResult):
            return NotImplemented
        return (
            self.platform == other.platform
            and self.platform_id == other.platform_id
            and self.url == other.url
        )

    @classmethod
    def from_result(cls, result: Result, score: float = 0.0) -> DownloadResult:
        """Create DownloadResult from a core Result."""
        return cls(
            name=result.name,
            artists=list(result.artists),
            artist=result.artist,
            duration=result.duration,
            platform=result.platform,
            platform_id=result.platform_id,
            url=result.url,
            verified=result.verified,
            score=score,
            album_name=result.album_name,
            cover_url=result.cover_url,
            views=result.views,
            isrc_search=result.isrc_search,
            search_query=result.search_query,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DownloadResult:
        """Create DownloadResult from dictionary."""
        if "platform" in data and isinstance(data["platform"], str):
            data = data.copy()
            data["platform"] = TargetPlatform(data["platform"])
        return cls(**data)


@dataclass
class MatchEntry:
    """Match entry with metadata for UI."""

    id: str | None
    source_url: str
    target_url: str
    target_platform: str
    score: float
    confidence: float
    match_type: str
    status: str | None
    result: DownloadResult
    upvotes: int = 0
    downvotes: int = 0

    @property
    def net_votes(self) -> int:
        """Net vote score."""
        return self.upvotes - self.downvotes


class DownloadStatus(StrEnum):
    """Download status for CLI queue."""

    PENDING = "pending"
    SEARCHING = "searching"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadItem:
    """Item in the download queue."""

    song: Song
    result: Result | None = None

    # Status
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0  # 0-100
    speed: str = ""  # e.g., "1.5 MB/s"
    eta: str = ""  # e.g., "00:30"
    error: str | None = None

    # Output
    output_path: Path | None = None
    download_id: str | None = None
    remote: bool = False

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def display_name(self) -> str:
        """Display name for the queue."""
        return self.song.display_name

    @property
    def status_display(self) -> str:
        """Human-readable status."""
        if self.status == DownloadStatus.DOWNLOADING and self.progress > 0:
            return f"Downloading {self.progress:.0f}%"
        if self.status == DownloadStatus.FAILED and self.error:
            return f"Failed: {self.error[:30]}"
        return self.status.value.title()


@dataclass
class SearchResult:
    """Result from a search operation."""

    songs: list[Song]
    total: int
    query: str
    platform: Platform


class EntityType(StrEnum):
    """Entity types for universal search."""

    TRACK = "track"
    ALBUM = "album"
    ARTIST = "artist"
    PLAYLIST = "playlist"


@dataclass
class PlatformInfo:
    """Platform availability info for an entity."""

    platform: str
    platform_id: str
    url: str
    followers: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlatformInfo:
        """Create from dictionary."""
        return cls(
            platform=data.get("platform", ""),
            platform_id=data.get("platform_id", ""),
            url=data.get("url", ""),
            followers=data.get("followers"),
        )


@dataclass
class EntityResult:
    """A single entity from universal search."""

    id: str
    entity_type: EntityType
    name: str
    subtitle: str | None = None
    image_url: str | None = None
    platforms: list[PlatformInfo] = field(default_factory=list)
    duration: int | None = None  # For tracks only, in seconds

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityResult:
        """Create from dictionary (supports both legacy and EntityResponse format)."""
        # Backend returns "type" not "entity_type" in EntityResponse
        raw_type = data.get("type") or data.get("entity_type", "track")
        # Canonical contains most metadata in the new entity model
        canonical = data.get("canonical", {})

        platforms = [
            PlatformInfo.from_dict(p) for p in data.get("platforms", [])
        ]
        return cls(
            id=data.get("id", ""),
            entity_type=EntityType(raw_type),
            name=data.get("name") or canonical.get("name", ""),
            subtitle=data.get("subtitle") or canonical.get("artist"),
            image_url=data.get("image_url") or canonical.get("cover_url"),
            platforms=platforms,
            duration=data.get("duration") or canonical.get("duration"),
        )

    @property
    def primary_platform(self) -> PlatformInfo | None:
        """Get the primary platform info."""
        return self.platforms[0] if self.platforms else None

    @property
    def duration_str(self) -> str:
        """Get formatted duration string."""
        if self.duration:
            return f"{self.duration // 60}:{self.duration % 60:02d}"
        return ""


@dataclass
class UniversalSearchResponse:
    """Response from universal search."""

    query: str
    query_type: str  # "url" or "text"
    results: list[EntityResult]
    entities_created: int
    total: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UniversalSearchResponse:
        """Create from dictionary (supports both legacy and DiscoverResponse format)."""
        # Backend returns "entities" not "results" in DiscoverResponse
        raw_results = data.get("entities") or data.get("results", [])
        results = [EntityResult.from_dict(r) for r in raw_results]
        return cls(
            query=data.get("query", ""),
            query_type=data.get("query_type", "text"),
            results=results,
            entities_created=data.get("entities_created", 0),
            total=data.get("total", len(results)),
        )

    def filter_by_type(self, entity_type: EntityType) -> list[EntityResult]:
        """Get results filtered by entity type."""
        return [r for r in self.results if r.entity_type == entity_type]

    @property
    def artists(self) -> list[EntityResult]:
        """Get artist results."""
        return self.filter_by_type(EntityType.ARTIST)

    @property
    def albums(self) -> list[EntityResult]:
        """Get album results."""
        return self.filter_by_type(EntityType.ALBUM)

    @property
    def tracks(self) -> list[EntityResult]:
        """Get track results."""
        return self.filter_by_type(EntityType.TRACK)

    @property
    def playlists(self) -> list[EntityResult]:
        """Get playlist results."""
        return self.filter_by_type(EntityType.PLAYLIST)


__all__ = [
    "DownloadItem",
    "DownloadResult",
    "DownloadStatus",
    "EntityResult",
    "EntityType",
    "Platform",
    "PlatformInfo",
    "Result",
    "SearchResult",
    "Song",
    "SongList",
    "TargetPlatform",
    "UniversalSearchResponse",
]
