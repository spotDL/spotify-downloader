"""spotDL core download pipeline (spec §5.4).

Single-track download engine: plan output path -> fetch audio -> convert ->
embed metadata -> post-process. All external I/O is reached through injected
collaborators so the default test suite is fully offline.

This module re-exports the download-relevant exception taxonomy from
``spotdl_core.providers.errors`` alongside the pipeline spine models, enums,
progress seam, and the ``Step`` type. Later tasks extend ``__all__`` with the
concrete steps and the ``DownloadEngine`` entry point.
"""

from spotdl_core.download.context import (
    BITRATE_AUTO,
    BITRATE_DISABLE,
    Bitrate,
    DownloadConfig,
    DownloadContext,
    DownloadOutcome,
    DownloadRequest,
    OutcomeStatus,
    OutputFormat,
    OverwriteMode,
    ProgressCallback,
    ProgressEvent,
    ProgressPhase,
    RestrictMode,
    SkipReason,
    Step,
)
from spotdl_core.providers.errors import (
    AudioFetchFailed,
    ConversionFailed,
    DownloadFailed,
    MetadataEmbedFailed,
    PostProcessingFailed,
)

__all__ = [
    "BITRATE_AUTO",
    "BITRATE_DISABLE",
    "AudioFetchFailed",
    "Bitrate",
    "ConversionFailed",
    "DownloadConfig",
    "DownloadContext",
    "DownloadFailed",
    "DownloadOutcome",
    "DownloadRequest",
    "MetadataEmbedFailed",
    "OutcomeStatus",
    "OutputFormat",
    "OverwriteMode",
    "PostProcessingFailed",
    "ProgressCallback",
    "ProgressEvent",
    "ProgressPhase",
    "RestrictMode",
    "SkipReason",
    "Step",
]
