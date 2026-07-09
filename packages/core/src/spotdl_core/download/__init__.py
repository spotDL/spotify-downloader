"""spotDL core download pipeline (spec §5.4).

Single-track download engine: plan output path -> fetch audio -> convert ->
embed metadata -> post-process. All external I/O is reached through injected
collaborators so the default test suite is fully offline.

This module re-exports the download-relevant exception taxonomy from
``spotdl_core.providers.errors``. Later tasks extend ``__all__`` with the
public models and the ``DownloadEngine`` entry point.
"""

from spotdl_core.providers.errors import (
    AudioFetchFailed,
    ConversionFailed,
    DownloadFailed,
    MetadataEmbedFailed,
    PostProcessingFailed,
)

__all__ = [
    "AudioFetchFailed",
    "ConversionFailed",
    "DownloadFailed",
    "MetadataEmbedFailed",
    "PostProcessingFailed",
]
