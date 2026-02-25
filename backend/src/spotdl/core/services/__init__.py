"""Business logic services."""

from spotdl.core.services.lyrics import (
    LyricsResult,
    LyricsService,
    LyricsServiceError,
    get_lyrics_service,
)

from spotdl.core.services.download import (
    DownloadService,
    DownloadServiceError,
    get_download_service,
)
from spotdl.core.services.entity_unified import (
    UnifiedEntityService,
    UnifiedEntityError,
    EntityNotFoundError,
    CapabilityUnsupportedError,
)

__all__ = [

    # Lyrics Service
    "LyricsService",
    "LyricsServiceError",
    "LyricsResult",
    "get_lyrics_service",
    # Download Service
    "DownloadService",
    "DownloadServiceError",
    "get_download_service",
    # Unified Entity Service
    "UnifiedEntityService",
    "UnifiedEntityError",
    "EntityNotFoundError",
    "CapabilityUnsupportedError",
]
