"""Target providers for searching audio sources."""

from spotdl_cli.providers.targets.bandcamp import BandcampTargetProvider
from spotdl_cli.providers.targets.soundcloud import SoundCloudTargetProvider
from spotdl_cli.providers.targets.youtube import YouTubeProvider
from spotdl_cli.providers.targets.ytmusic import YouTubeMusicTargetProvider

__all__ = [
    "BandcampTargetProvider",
    "SoundCloudTargetProvider",
    "YouTubeMusicTargetProvider",
    "YouTubeProvider",
]
