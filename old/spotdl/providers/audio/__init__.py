"""
Audio providers for spotdl.
"""

from spotdl.providers.audio.bandcamp import BandCamp
from spotdl.providers.audio.base import (
    ISRC_REGEX,
    AudioProvider,
    AudioProviderError,
    YTDLLogger,
)
from spotdl.providers.audio.piped import Piped
from spotdl.providers.audio.soundcloud import SoundCloud
from spotdl.providers.audio.youtube import YouTube
from spotdl.providers.audio.ytmusic import YouTubeMusic

__all__ = [
    "YouTube",
    "YouTubeMusic",
    "SoundCloud",
    "BandCamp",
    "Piped",
    "AudioProvider",
    "AudioProviderError",
    "YTDLLogger",
    "ISRC_REGEX",
]
