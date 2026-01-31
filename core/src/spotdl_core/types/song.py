"""Song type definition for multi-platform support."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Platform(StrEnum):
    """Supported source platforms for song metadata."""

    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    DEEZER = "deezer"
    TIDAL = "tidal"
    YOUTUBE_MUSIC = "youtube_music"
    SOUNDCLOUD = "soundcloud"
    BANDCAMP = "bandcamp"


class SongError(Exception):
    """Base exception for song-related errors."""


@dataclass
class Song:
    """
    Platform-agnostic song representation.

    Contains all metadata needed for matching and downloading.
    Extended from the original Spotify-only version to support
    any source platform.
    """

    # Required fields
    name: str
    artists: list[str]
    artist: str  # Primary artist (convenience field)
    duration: int  # Duration in seconds

    # Platform identification
    platform: Platform
    platform_id: str  # ID on the source platform
    url: str  # Original platform URL

    # Album information
    album_name: str = ""
    album_artist: str = ""
    album_id: str | None = None
    album_type: str | None = None

    # Track metadata
    genres: list[str] = field(default_factory=list)
    disc_number: int = 1
    disc_count: int = 1
    track_number: int = 1
    tracks_count: int = 1
    year: int = 0
    date: str = ""

    # Identification
    song_id: str = ""  # Internal ID (UUID when stored in DB)
    isrc: str | None = None  # International Standard Recording Code

    # Additional metadata
    explicit: bool = False
    publisher: str = ""
    cover_url: str | None = None
    copyright_text: str | None = None

    # Optional fields
    lyrics: str | None = None
    popularity: int | None = None
    download_url: str | None = None

    # List context (when song is part of a playlist/album)
    list_name: str | None = None
    list_url: str | None = None
    list_position: int | None = None
    list_length: int | None = None

    # Artist metadata
    artist_id: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize song data after initialization."""
        if not self.song_id:
            self.song_id = f"{self.platform}:{self.platform_id}"

        if not self.artist and self.artists:
            self.artist = self.artists[0]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Song:
        """
        Create a Song from a dictionary.

        Args:
            data: Dictionary containing song data

        Returns:
            Song instance
        """
        # Handle platform as string or enum
        if "platform" in data and isinstance(data["platform"], str):
            data = data.copy()
            data["platform"] = Platform(data["platform"])

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> Song:
        """
        Create a Song from a JSON string.

        Args:
            json_str: JSON string containing song data

        Returns:
            Song instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @property
    def display_name(self) -> str:
        """Get a human-readable display name for the song."""
        return f"{self.artist} - {self.name}"

    @property
    def json(self) -> dict[str, Any]:
        """Get song data as a dictionary."""
        data = asdict(self)
        # Convert enum to string for JSON serialization
        data["platform"] = self.platform.value
        return data

    def to_json(self) -> str:
        """Serialize song to JSON string."""
        return json.dumps(self.json)


@dataclass(frozen=True)
class SongList:
    """
    Base class for collections of songs.

    Used for albums, playlists, and other song groupings.
    """

    name: str
    url: str
    platform: Platform
    urls: tuple[str, ...]
    songs: tuple[Song, ...]

    @property
    def length(self) -> int:
        """Get the number of songs in the list."""
        return max(len(self.urls), len(self.songs))

    @property
    def json(self) -> dict[str, Any]:
        """Get song list data as a dictionary."""
        return {
            "name": self.name,
            "url": self.url,
            "platform": self.platform.value,
            "urls": list(self.urls),
            "songs": [song.json for song in self.songs],
        }
