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
from spotdl_core.download.engine import DownloadEngine, build_default_engine
from spotdl_core.download.fetch import (
    Fetcher,
    FetchResult,
    FetchStep,
    YtDlpFetcher,
    ytdl_format_for,
)
from spotdl_core.download.post import (
    SPONSOR_BLOCK_CATEGORIES,
    M3uEntry,
    SponsorBlock,
    SponsorBlockStep,
    SyncedLyricsLibrary,
    SyncedLyricsSearch,
    YtDlpSponsorBlock,
    archive_update,
    create_m3u_content,
    gen_m3u_files,
    generate_lrc,
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
    "AudioFetchFailed",
    "BITRATE_AUTO",
    "BITRATE_DISABLE",
    "Bitrate",
    "ConversionFailed",
    "ConvertStep",
    "CoverDownloader",
    "DownloadConfig",
    "DownloadContext",
    "DownloadEngine",
    "DownloadFailed",
    "DownloadOutcome",
    "DownloadRequest",
    "EmbedStep",
    "FFMPEG_CODECS",
    "FetchResult",
    "FetchStep",
    "Fetcher",
    "HttpCoverDownloader",
    "LRC_REGEX",
    "M3uEntry",
    "M4A_TAG_PRESET",
    "MP3_TAG_PRESET",
    "MetadataEmbedFailed",
    "OutcomeStatus",
    "OutputFormat",
    "OverwriteMode",
    "PostProcessingFailed",
    "ProgressCallback",
    "ProgressEvent",
    "ProgressPhase",
    "RestrictMode",
    "SPONSOR_BLOCK_CATEGORIES",
    "SkipReason",
    "SponsorBlock",
    "SponsorBlockStep",
    "Step",
    "SyncedLyricsLibrary",
    "SyncedLyricsSearch",
    "YtDlpFetcher",
    "YtDlpSponsorBlock",
    "archive_update",
    "build_default_engine",
    "build_ffmpeg_command",
    "create_m3u_content",
    "embed_metadata",
    "gen_m3u_files",
    "generate_lrc",
    "resolve_bitrate",
    "should_move",
    "ytdl_format_for",
]
