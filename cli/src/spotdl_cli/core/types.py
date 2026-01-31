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


__all__ = [
    "DownloadItem",
    "DownloadResult",
    "DownloadStatus",
    "Platform",
    "Result",
    "SearchResult",
    "Song",
    "SongList",
    "TargetPlatform",
]
