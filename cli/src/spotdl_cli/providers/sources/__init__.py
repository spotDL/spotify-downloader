"""Source providers for fetching song metadata from streaming platforms."""

from spotdl_cli.providers.sources.deezer import DeezerProvider
from spotdl_cli.providers.sources.ytmusic import YouTubeMusicSourceProvider

__all__ = [
    "DeezerProvider",
    "YouTubeMusicSourceProvider",
]
