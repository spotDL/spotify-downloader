"""spotDL provider layer public API.

Later tasks extend this package (and ``__all__``) with capability Protocols,
``PlatformRef`` and URL parsing, the shared HTTP plumbing, and the
``ProviderRegistry``. For now it re-exports the exception taxonomy so every
downstream layer imports errors from a single place.
"""

from spotdl_core.providers.base import (
    ALL_SEARCH_ENTITY_TYPES,
    Enriches,
    HttpProvider,
    Provider,
    ProvidesAudio,
    ProvidesLyrics,
    ResolvedEntity,
    Resolves,
    Searches,
    SearchesEntities,
)
from spotdl_core.providers.errors import (
    AudioFetchFailed,
    ConversionFailed,
    DownloadFailed,
    EntityNotFound,
    MetadataEmbedFailed,
    NoMatchFound,
    PostProcessingFailed,
    ProviderAuthError,
    ProviderError,
    ProviderUnavailable,
    RateLimited,
    SpotdlError,
    UnsupportedURL,
)
from spotdl_core.providers.http import (
    DEFAULT_USER_AGENT,
    create_client,
    request_json,
)
from spotdl_core.providers.registry import (
    PROVIDER_ORDER,
    LastfmConfig,
    ProviderContext,
    ProviderRegistry,
    ProviderSpec,
    SpotifyConfig,
    build_default_registry,
)
from spotdl_core.providers.urls import PlatformRef, parse, resolve_shortlink, strip_intl

__all__ = [
    "ALL_SEARCH_ENTITY_TYPES",
    "DEFAULT_USER_AGENT",
    "PROVIDER_ORDER",
    "AudioFetchFailed",
    "LastfmConfig",
    "ConversionFailed",
    "DownloadFailed",
    "Enriches",
    "EntityNotFound",
    "HttpProvider",
    "MetadataEmbedFailed",
    "NoMatchFound",
    "PlatformRef",
    "PostProcessingFailed",
    "Provider",
    "ProviderAuthError",
    "ProviderContext",
    "ProviderError",
    "ProviderRegistry",
    "ProviderSpec",
    "ProviderUnavailable",
    "ProvidesAudio",
    "ProvidesLyrics",
    "RateLimited",
    "ResolvedEntity",
    "Resolves",
    "Searches",
    "SearchesEntities",
    "SpotdlError",
    "SpotifyConfig",
    "UnsupportedURL",
    "build_default_registry",
    "create_client",
    "parse",
    "request_json",
    "resolve_shortlink",
    "strip_intl",
]
