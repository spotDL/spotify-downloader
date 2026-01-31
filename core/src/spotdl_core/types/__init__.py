"""Core types for spotdl."""

from spotdl_core.types.result import Result, TargetPlatform
from spotdl_core.types.song import Platform, Song, SongError, SongList

__all__ = [
    "Platform",
    "Result",
    "Song",
    "SongError",
    "SongList",
    "TargetPlatform",
]
