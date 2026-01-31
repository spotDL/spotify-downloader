"""Provider modules for source and target platforms."""

from spotdl.providers.sources import (
    AppleMusicProvider,
    BandcampProvider,
    DeezerProvider,
    InvalidURLError,
    SoundCloudProvider,
    SourceProvider,
    SourceProviderError,
    SpotifyProvider,
    TidalProvider,
    TrackNotFoundError,
    URLResolver,
    URLResolverError,
    UnsupportedPlatformError,
    YouTubeMusicProvider,
    detect_platform,
    extract_url_info,
    get_resolver,
    is_valid_url,
)

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
    # Source Providers
    "SpotifyProvider",
    "YouTubeMusicProvider",
    "DeezerProvider",
    "AppleMusicProvider",
    "TidalProvider",
    "SoundCloudProvider",
    "BandcampProvider",
]
