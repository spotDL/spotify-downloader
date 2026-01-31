"""Metadata providers for enriching song information."""

from spotdl.providers.metadata.base import MetadataProvider, MetadataProviderError
from spotdl.providers.metadata.musicbrainz import MusicBrainzProvider
from spotdl.providers.metadata.discogs import DiscogsProvider

__all__ = [
    "MetadataProvider",
    "MetadataProviderError",
    "MusicBrainzProvider",
    "DiscogsProvider",
]
