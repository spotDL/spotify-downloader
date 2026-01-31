"""Provider modules for source and target platforms."""

from spotdl.providers.sources import (
    AppleMusicProvider,
    InvalidURLError,
    SourceProvider,
    SourceProviderError,
    SpotifyProvider,
    TidalProvider,
    TrackNotFoundError,
    URLResolver,
    URLResolverError,
    UnsupportedPlatformError,
    detect_platform,
    extract_url_info,
    get_resolver,
    is_valid_url,
)
from spotdl.providers.sources import BandcampProvider as BandcampSourceProvider
from spotdl.providers.sources import DeezerProvider as DeezerSourceProvider
from spotdl.providers.sources import SoundCloudProvider as SoundCloudSourceProvider
from spotdl.providers.sources import YouTubeMusicProvider as YouTubeMusicSourceProvider
from spotdl.providers.targets import (
    NoResultsError,
    PipedProvider,
    SearchError,
    TargetProvider,
    TargetProviderError,
    YouTubeProvider,
)
from spotdl.providers.targets import BandcampProvider as BandcampTargetProvider
from spotdl.providers.targets import SoundCloudProvider as SoundCloudTargetProvider
from spotdl.providers.targets import YouTubeMusicProvider as YouTubeMusicTargetProvider

__all__ = [
    # Source Base
    "SourceProvider",
    "SourceProviderError",
    "InvalidURLError",
    "TrackNotFoundError",
    # Target Base
    "TargetProvider",
    "TargetProviderError",
    "SearchError",
    "NoResultsError",
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
    "YouTubeMusicSourceProvider",
    "DeezerSourceProvider",
    "AppleMusicProvider",
    "TidalProvider",
    "SoundCloudSourceProvider",
    "BandcampSourceProvider",
    # Target Providers
    "YouTubeProvider",
    "YouTubeMusicTargetProvider",
    "SoundCloudTargetProvider",
    "BandcampTargetProvider",
    "PipedProvider",
]
