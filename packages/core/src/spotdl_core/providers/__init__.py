"""spotDL provider layer public API.

Later tasks extend this package (and ``__all__``) with capability Protocols,
``PlatformRef`` and URL parsing, the shared HTTP plumbing, and the
``ProviderRegistry``. For now it re-exports the exception taxonomy so every
downstream layer imports errors from a single place.
"""

from spotdl_core.providers.errors import (
    ConversionFailed,
    DownloadFailed,
    EntityNotFound,
    MetadataEmbedFailed,
    NoMatchFound,
    ProviderAuthError,
    ProviderError,
    ProviderUnavailable,
    RateLimited,
    SpotdlError,
    UnsupportedURL,
)
from spotdl_core.providers.urls import PlatformRef, parse, resolve_shortlink, strip_intl

__all__ = [
    "ConversionFailed",
    "DownloadFailed",
    "EntityNotFound",
    "MetadataEmbedFailed",
    "NoMatchFound",
    "PlatformRef",
    "ProviderAuthError",
    "ProviderError",
    "ProviderUnavailable",
    "RateLimited",
    "SpotdlError",
    "UnsupportedURL",
    "parse",
    "resolve_shortlink",
    "strip_intl",
]
