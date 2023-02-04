"""
Audio providers for spotdl.
"""

from spotdl.providers.audio.base import (
    ISRC_REGEX,
    AudioProvider,
    AudioProviderError,
    YTDLLogger,
)
from spotdl.providers.audio.youtube import YouTube
from spotdl.providers.audio.ytmusic import YouTubeMusic

__all__ = [
    "YouTube",
    "YouTubeMusic",
    "AudioProvider",
    "AudioProviderError",
    "YTDLLogger",
    "ISRC_REGEX",
]
