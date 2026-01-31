"""Source providers for fetching song metadata from various platforms."""

from spotdl_core.providers.sources.apple_music import AppleMusicProvider
from spotdl_core.providers.sources.bandcamp import BandcampProvider
from spotdl_core.providers.sources.base import (
    InvalidURLError,
    SourceProvider,
    SourceProviderError,
    TrackNotFoundError,
)
from spotdl_core.providers.sources.deezer import DeezerProvider
from spotdl_core.providers.sources.resolver import (
    URLResolver,
    URLResolverError,
    UnsupportedPlatformError,
    detect_platform,
    extract_url_info,
    get_resolver,
    is_valid_url,
)
from spotdl_core.providers.sources.soundcloud import SoundCloudProvider
from spotdl_core.providers.sources.spotify import SpotifyProvider
from spotdl_core.providers.sources.tidal import TidalProvider
from spotdl_core.providers.sources.ytmusic import YouTubeMusicProvider

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
