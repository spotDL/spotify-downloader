"""Type definitions for SpotDL CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class Platform(StrEnum):
    """Supported source platforms."""

    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    DEEZER = "deezer"
    TIDAL = "tidal"
    YOUTUBE_MUSIC = "youtube_music"
    SOUNDCLOUD = "soundcloud"
    BANDCAMP = "bandcamp"


class TargetPlatform(StrEnum):
    """Supported target platforms for downloading."""

    YOUTUBE = "youtube"
    YOUTUBE_MUSIC = "youtube_music"
    SOUNDCLOUD = "soundcloud"
    BANDCAMP = "bandcamp"
    PIPED = "piped"
    SLIDER_KZ = "slider.kz"


class DownloadStatus(StrEnum):
    """Download status."""

    PENDING = "pending"
    SEARCHING = "searching"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Song:
    """Song metadata."""

    name: str
    artists: list[str]
    artist: str
    duration: int  # seconds

    # Platform info
    platform: Platform
    platform_id: str
    url: str

    # Optional metadata
    album_name: str = ""
    album_artist: str = ""
    genres: list[str] = field(default_factory=list)
    year: int = 0
    date: str = ""
    track_number: int = 1
    disc_number: int = 1
    isrc: str | None = None
    cover_url: str | None = None
    explicit: bool = False
    lyrics: str | None = None

    # Internal ID
    song_id: str = ""

    def __post_init__(self) -> None:
        """Generate song_id if not provided."""
        if not self.song_id:
            self.song_id = f"{self.platform}:{self.platform_id}"

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return f"{self.artist} - {self.name}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Song:
        """Create Song from dictionary."""
        if "platform" in data and isinstance(data["platform"], str):
            data = data.copy()
            data["platform"] = Platform(data["platform"])
        return cls(**data)


@dataclass
class DownloadResult:
    """Result from a download target search."""

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
    def from_dict(cls, data: dict[str, Any]) -> DownloadResult:
        """Create DownloadResult from dictionary."""
        if "platform" in data and isinstance(data["platform"], str):
            data = data.copy()
            data["platform"] = TargetPlatform(data["platform"])
        return cls(**data)


@dataclass
class DownloadItem:
    """Item in the download queue."""

    song: Song
    result: DownloadResult | None = None

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
