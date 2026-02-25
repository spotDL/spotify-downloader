"""Source providers for fetching song metadata from various platforms."""

from spotdl.providers.sources.apple_music import AppleMusicProvider
from spotdl.providers.sources.bandcamp import BandcampProvider
from spotdl.providers.sources.base import (
    InvalidURLError,
    SourceProvider,
    SourceProviderError,
    TrackNotFoundError,
)
from spotdl.providers.sources.deezer import DeezerProvider
from spotdl.providers.sources.resolver import (
    UnsupportedPlatformError,
    URLResolver,
    URLResolverError,
    detect_platform,
    extract_url_info,
    get_resolver,
    is_valid_url,
)
from spotdl.providers.sources.soundcloud import SoundCloudProvider
from spotdl.providers.sources.spotify import SpotifyProvider
from spotdl.providers.sources.tidal import TidalProvider
from spotdl.providers.sources.ytmusic import YouTubeMusicProvider

__all__ = [
    # Base
    "SourceProvider",
    "SourceProviderError",
    "InvalidURLError",
    "TrackNotFoundError",
    # Resolver
    "URLResolver",
    "URLResolverError",
    "UnsupportedPlatformError",
    "detect_platform",
    "extract_url_info",
    "is_valid_url",
    "get_resolver",
    # Providers
    "SpotifyProvider",
    "YouTubeMusicProvider",
    "DeezerProvider",
    "AppleMusicProvider",
    "TidalProvider",
    "SoundCloudProvider",
    "BandcampProvider",
]
