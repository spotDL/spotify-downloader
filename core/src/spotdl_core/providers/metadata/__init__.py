"""Metadata providers for enriching song information."""

from spotdl_core.providers.metadata.base import (
    MetadataProvider,
    MetadataProviderError,
    MetadataResult,
)
from spotdl_core.providers.metadata.musicbrainz import MusicBrainzProvider
from spotdl_core.providers.metadata.discogs import DiscogsProvider

__all__ = [
    "DiscogsProvider",
    "MetadataProvider",
    "MetadataProviderError",
    "MetadataResult",
    "MusicBrainzProvider",
]
