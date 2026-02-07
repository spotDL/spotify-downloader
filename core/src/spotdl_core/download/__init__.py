"""Shared download module for SpotDL - used by both CLI and backend."""

from spotdl_core.download.archive import Archive
from spotdl_core.download.downloader import (
    DownloadError,
    DownloadMeta,
    DownloadProgress,
    DownloadSettings,
    Downloader,
)
from spotdl_core.download.lrc import generate_lrc, is_synced

__all__ = [
    "Archive",
    "DownloadError",
    "DownloadMeta",
    "DownloadProgress",
    "DownloadSettings",
    "Downloader",
    "generate_lrc",
    "is_synced",
]
