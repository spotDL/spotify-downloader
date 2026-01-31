"""Providers for fetching song metadata and searching for audio sources."""

from spotdl_core.providers.metadata import (
    DiscogsProvider,
    MetadataProvider,
    MetadataProviderError,
    MetadataResult,
    MusicBrainzProvider,
)
from spotdl_core.providers.sources import (
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
from spotdl_core.providers.targets import (
    NoResultsError,
    PipedProvider,
    SearchError,
    TargetProvider,
    TargetProviderError,
    YouTubeProvider,
)
from spotdl_core.providers.targets import (
    BandcampProvider as BandcampTargetProvider,
)
from spotdl_core.providers.targets import (
    SoundCloudProvider as SoundCloudTargetProvider,
)
from spotdl_core.providers.targets import (
    YouTubeMusicProvider as YouTubeMusicTargetProvider,
)

__all__ = [
    # Source Providers
    "AppleMusicProvider",
    "BandcampProvider",
    "DeezerProvider",
    "InvalidURLError",
    "SoundCloudProvider",
    "SourceProvider",
    "SourceProviderError",
    "SpotifyProvider",
    "TidalProvider",
    "TrackNotFoundError",
    "URLResolver",
    "URLResolverError",
    "UnsupportedPlatformError",
    "YouTubeMusicProvider",
    "detect_platform",
    "extract_url_info",
    "get_resolver",
    "is_valid_url",
    # Target Providers
    "BandcampTargetProvider",
    "NoResultsError",
    "PipedProvider",
    "SearchError",
    "SoundCloudTargetProvider",
    "TargetProvider",
    "TargetProviderError",
    "YouTubeMusicTargetProvider",
    "YouTubeProvider",
    # Metadata Providers
    "DiscogsProvider",
    "MetadataProvider",
    "MetadataProviderError",
    "MetadataResult",
    "MusicBrainzProvider",
]
