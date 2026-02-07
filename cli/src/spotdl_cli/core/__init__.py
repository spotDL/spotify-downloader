"""Core functionality for SpotDL CLI."""

from spotdl_cli.core.archive import Archive
from spotdl_cli.core.image_service import (
    ImageService,
    get_image_service,
)
from spotdl_cli.core.api_client import (
    APIClient,
    APIError,
    ConnectionError,
    NotFoundError,
    get_api_client,
)
from spotdl_cli.core.downloader import (
    Downloader,
    DownloadError,
    DownloadManager,
    DownloadProgress,
)
from spotdl_cli.core.lrc import generate_lrc
from spotdl_cli.core.m3u import create_m3u_content, gen_m3u_files
from spotdl_cli.core.metadata_reader import (
    find_audio_files,
    read_file_metadata,
    extract_spotify_url,
)
from spotdl_cli.core.offline import (
    OfflineMatcher,
    get_offline_matcher,
)
from spotdl_cli.core.query import (
    QueryType,
    parse_query,
)
from spotdl_cli.core.queue import (
    DownloadQueue,
    QueueEvent,
)
from spotdl_cli.core.sync import (
    PlaylistSyncManager,
    SyncActions,
    SyncFile,
)
from spotdl_cli.core.types import (
    DownloadItem,
    DownloadResult,
    DownloadStatus,
    EntityResult,
    EntityType,
    MatchEntry,
    Platform,
    PlatformInfo,
    SearchResult,
    Song,
    TargetPlatform,
    UniversalSearchResponse,
)

__all__ = [
    "APIClient",
    "APIError",
    "Archive",
    "ConnectionError",
    "DownloadError",
    "DownloadItem",
    "DownloadManager",
    "DownloadProgress",
    "DownloadQueue",
    "DownloadResult",
    "DownloadStatus",
    "Downloader",
    "EntityResult",
    "EntityType",
    "ImageService",
    "MatchEntry",
    "NotFoundError",
    "OfflineMatcher",
    "Platform",
    "PlatformInfo",
    "PlaylistSyncManager",
    "QueryType",
    "QueueEvent",
    "SearchResult",
    "Song",
    "SyncActions",
    "SyncFile",
    "TargetPlatform",
    "UniversalSearchResponse",
    "create_m3u_content",
    "extract_spotify_url",
    "find_audio_files",
    "gen_m3u_files",
    "generate_lrc",
    "get_api_client",
    "get_image_service",
    "get_offline_matcher",
    "parse_query",
    "read_file_metadata",
]
