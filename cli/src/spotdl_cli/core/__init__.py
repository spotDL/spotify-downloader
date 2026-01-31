"""Core functionality for SpotDL CLI."""

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
from spotdl_cli.core.offline import (
    OfflineMatcher,
    get_offline_matcher,
)
from spotdl_cli.core.queue import (
    DownloadQueue,
    QueueEvent,
)
from spotdl_cli.core.types import (
    DownloadItem,
    DownloadResult,
    DownloadStatus,
    Platform,
    SearchResult,
    Song,
    TargetPlatform,
)

__all__ = [
    "APIClient",
    "APIError",
    "ConnectionError",
    "DownloadError",
    "DownloadItem",
    "DownloadManager",
    "DownloadProgress",
    "DownloadQueue",
    "DownloadResult",
    "DownloadStatus",
    "Downloader",
    "NotFoundError",
    "OfflineMatcher",
    "Platform",
    "QueueEvent",
    "SearchResult",
    "Song",
    "TargetPlatform",
    "get_api_client",
    "get_offline_matcher",
]
