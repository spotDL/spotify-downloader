"""Target providers for searching audio sources."""

from spotdl.providers.targets.bandcamp import BandcampProvider
from spotdl.providers.targets.base import (
    NoResultsError,
    SearchError,
    TargetProvider,
    TargetProviderError,
)
from spotdl.providers.targets.piped import PipedProvider
from spotdl.providers.targets.soundcloud import SoundCloudProvider
from spotdl.providers.targets.youtube import YouTubeProvider
from spotdl.providers.targets.ytmusic import YouTubeMusicProvider

__all__ = [
    # Base
    "TargetProvider",
    "TargetProviderError",
    "SearchError",
    "NoResultsError",
    # Providers
    "YouTubeProvider",
    "YouTubeMusicProvider",
    "SoundCloudProvider",
    "BandcampProvider",
    "PipedProvider",
]
