"""Result type definition for search results from target platforms."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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


@dataclass(frozen=True, eq=True)
class Result:
    """
    Represents a search result from a target audio platform.

    This is an immutable, hashable object representing a potential
    audio source match for a song.
    """

    # Required fields
    source: TargetPlatform  # Source platform of this result
    url: str  # URL to the audio
    verified: bool  # Whether from a verified/official source
    name: str  # Title of the result
    duration: float  # Duration in seconds
    author: str  # Channel/artist name
    result_id: str  # Platform-specific ID

    # Search metadata
    isrc_search: bool | None = None  # Whether found via ISRC search
    search_query: str | None = None  # The query used to find this result

    # Optional metadata
    artists: tuple[str, ...] | None = None  # Parsed artist names
    views: int | None = None  # View/play count
    explicit: bool | None = None  # Explicit content flag
    album: str | None = None  # Album name if available
    year: int | None = None  # Release year
    track_number: int | None = None  # Track number in album
    genre: str | None = None  # Genre if available
    lyrics: str | None = None  # Lyrics if available

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

        # Handle source as string or enum
        if "source" in data and isinstance(data["source"], str):
            data["source"] = TargetPlatform(data["source"])

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
        data["source"] = self.source.value
        # Convert tuple to list for JSON serialization
        if data["artists"] is not None:
            data["artists"] = list(data["artists"])
        return data

    def to_json(self) -> str:
        """Serialize result to JSON string."""
        return json.dumps(self.json)
