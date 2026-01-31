"""Local providers for CLI (sources, targets, metadata)."""

from spotdl_cli.providers.base import (
    InvalidURLError,
    MetadataProvider,
    MetadataProviderError,
    MetadataResult,
    NoResultsError,
    ProviderError,
    SearchError,
    SongList,
    SourceProvider,
    SourceProviderError,
    TargetProvider,
    TargetProviderError,
    TrackNotFoundError,
)
from spotdl_cli.providers.metadata import MusicBrainzProvider
from spotdl_cli.providers.sources import DeezerProvider, YouTubeMusicSourceProvider
from spotdl_cli.providers.targets import (
    BandcampTargetProvider,
    SoundCloudTargetProvider,
    YouTubeMusicTargetProvider,
    YouTubeProvider,
)

__all__ = [
    "BandcampTargetProvider",
    "DeezerProvider",
    "InvalidURLError",
    "MetadataProvider",
    "MetadataProviderError",
    "MetadataResult",
    "MusicBrainzProvider",
    "NoResultsError",
    "ProviderError",
    "SearchError",
    "SongList",
    "SoundCloudTargetProvider",
    "SourceProvider",
    "SourceProviderError",
    "TargetProvider",
    "TargetProviderError",
    "TrackNotFoundError",
    "YouTubeMusicSourceProvider",
    "YouTubeMusicTargetProvider",
    "YouTubeProvider",
]
