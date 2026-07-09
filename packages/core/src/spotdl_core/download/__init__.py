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
from spotdl_core.download.convert import (
    FFMPEG_CODECS,
    ConvertStep,
    build_ffmpeg_command,
    resolve_bitrate,
    should_move,
)
from spotdl_core.download.fetch import (
    Fetcher,
    FetchResult,
    FetchStep,
    YtDlpFetcher,
    ytdl_format_for,
)
from spotdl_core.download.tags import (
    LRC_REGEX,
    M4A_TAG_PRESET,
    MP3_TAG_PRESET,
    CoverDownloader,
    EmbedStep,
    HttpCoverDownloader,
    embed_metadata,
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
    "FFMPEG_CODECS",
    "LRC_REGEX",
    "M4A_TAG_PRESET",
    "MP3_TAG_PRESET",
    "AudioFetchFailed",
    "Bitrate",
    "ConversionFailed",
    "ConvertStep",
    "CoverDownloader",
    "DownloadConfig",
    "DownloadContext",
    "DownloadFailed",
    "DownloadOutcome",
    "DownloadRequest",
    "EmbedStep",
    "FetchResult",
    "FetchStep",
    "Fetcher",
    "HttpCoverDownloader",
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
    "YtDlpFetcher",
    "build_ffmpeg_command",
    "embed_metadata",
    "resolve_bitrate",
    "should_move",
    "ytdl_format_for",
]
