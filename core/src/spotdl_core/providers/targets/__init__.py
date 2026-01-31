"""Target providers for searching audio sources."""

from spotdl_core.providers.targets.bandcamp import BandcampProvider
from spotdl_core.providers.targets.base import (
    NoResultsError,
    SearchError,
    TargetProvider,
    TargetProviderError,
)
from spotdl_core.providers.targets.piped import PipedProvider
from spotdl_core.providers.targets.soundcloud import SoundCloudProvider
from spotdl_core.providers.targets.youtube import YouTubeProvider
from spotdl_core.providers.targets.ytmusic import YouTubeMusicProvider

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
