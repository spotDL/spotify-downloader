"""Result type definition for search results from target platforms."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class TargetPlatform(StrEnum):
    """Supported target platforms for audio sources."""

    YOUTUBE = "youtube"
    YOUTUBE_MUSIC = "youtube_music"
    SOUNDCLOUD = "soundcloud"
    BANDCAMP = "bandcamp"
    PIPED = "piped"
    SLIDER_KZ = "slider.kz"


@dataclass(frozen=True)
class Result:
    """
    Represents a search result from a target audio platform.

    This object represents a potential audio source match for a song.
    Field names are consistent with Song for easier comparison.
    """

    # Required fields
    name: str  # Title of the result
    artists: tuple[str, ...] | list[str]  # Artist names
    artist: str  # Primary artist name
    duration: int  # Duration in seconds
    platform: TargetPlatform  # Target platform
    platform_id: str  # Platform-specific ID
    url: str  # URL to the audio

    # Optional metadata
    album_name: str | None = None  # Album name if available
    cover_url: str | None = None  # Cover/thumbnail URL
    views: int | None = None  # View/play count
    explicit: bool = False  # Explicit content flag
    verified: bool = False  # Whether from a verified/official source
    year: int | None = None  # Release year
    track_number: int | None = None  # Track number in album

    # Search metadata
    isrc_search: bool = False  # Whether found via ISRC search
    search_query: str | None = None  # The query used to find this result

    def __post_init__(self) -> None:
        """Convert artists list to tuple if needed."""
        if isinstance(self.artists, list):
            object.__setattr__(self, "artists", tuple(self.artists))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Result:
        """
        Create a Result from a dictionary.

        Args:
            data: Dictionary containing result data

        Returns:
            Result instance
        """
        data = data.copy()

        # Handle platform as string or enum
        if "platform" in data and isinstance(data["platform"], str):
            data["platform"] = TargetPlatform(data["platform"])

        # Handle legacy field names
        if "source" in data and "platform" not in data:
            data["platform"] = data.pop("source")
        if "author" in data and "artist" not in data:
            data["artist"] = data.pop("author")
            data["artists"] = [data["artist"]]
        if "result_id" in data and "platform_id" not in data:
            data["platform_id"] = data.pop("result_id")
        if "album" in data and "album_name" not in data:
            data["album_name"] = data.pop("album")

        # Handle artists as list -> tuple
        if "artists" in data and isinstance(data["artists"], list):
            data["artists"] = tuple(data["artists"])

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> Result:
        """
        Create a Result from a JSON string.

        Args:
            json_str: JSON string containing result data

        Returns:
            Result instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @property
    def json(self) -> dict[str, Any]:
        """Get result data as a dictionary."""
        data = asdict(self)
        # Convert enum to string for JSON serialization
        data["platform"] = self.platform.value
        # Convert tuple to list for JSON serialization
        if data["artists"] is not None:
            data["artists"] = list(data["artists"])
        return data

    def to_json(self) -> str:
        """Serialize result to JSON string."""
        return json.dumps(self.json)

    @property
    def display_name(self) -> str:
        """Get a human-readable display name for the result."""
        return f"{self.artist} - {self.name}"
