"""Metadata providers for enriching song information."""

from spotdl.providers.metadata.base import MetadataProvider, MetadataProviderError
from spotdl.providers.metadata.discogs import DiscogsProvider
from spotdl.providers.metadata.musicbrainz import MusicBrainzProvider

__all__ = [
    "DiscogsProvider",
    "MetadataProvider",
    "MetadataProviderError",
    "MusicBrainzProvider",
]
