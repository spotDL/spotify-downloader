"""Download service - thin wrapper around spotdl_core.download for the backend."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from spotdl_core.download import (  # type: ignore[import-untyped]
    Downloader,
    DownloadMeta,
    generate_lrc,
)
from spotdl_core.download import (
    DownloadProgress as CoreDownloadProgress,
)
from spotdl_core.download import (
    DownloadSettings as CoreDownloadSettings,
)

logger = logging.getLogger(__name__)


# ── SSRF-safe cover URL validation ────────────────────────────────

ALLOWED_SCHEMES = {"http", "https"}

COVER_URL_ALLOWLIST = {
    "i.scdn.co", "mosaic.scdn.co",
    "i.ytimg.com", "yt3.ggpht.com", "lh3.googleusercontent.com",
    "is1-ssl.mzstatic.com", "is2-ssl.mzstatic.com", "is3-ssl.mzstatic.com",
    "is4-ssl.mzstatic.com", "is5-ssl.mzstatic.com",
    "cdns-images.dzcdn.net", "e-cdns-images.dzcdn.net",
    "i1.sndcdn.com", "f4.bcbits.com", "resources.tidal.com",
}


def is_safe_url(url: str) -> bool:
    """Validate that a URL is safe to fetch (not pointing to internal resources)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ALLOWED_SCHEMES:
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        hostname_lower = hostname.lower()
        if hostname_lower not in COVER_URL_ALLOWLIST:
            if not any(hostname_lower.endswith(f".{d}") for d in COVER_URL_ALLOWLIST):
                return False
        try:
            for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None, socket.AF_UNSPEC):
                ip = ipaddress.ip_address(sockaddr[0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                    return False
                if str(ip) == "169.254.169.254":
                    return False
        except (socket.gaierror, socket.herror):
            return False
        return True
    except Exception:
        return False


# ── Backend-specific types ────────────────────────────────────────

class DownloadServiceError(Exception):
    """Base exception for download service."""


class DownloadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadSettings:
    """Download settings loaded from user settings or defaults."""

    audio_format: str = "mp3"
    audio_quality: str = "best"
    bitrate: str | None = None
    output_template: str = "{artist} - {title}"
    max_filename_length: int = 255
    restrict: str | None = None
    overwrite: str = "skip"
    embed_metadata: bool = True
    embed_lyrics: bool = True
    embed_cover: bool = True
    id3_separator: str = "/"
    sponsor_block: bool = False
    generate_lrc: bool = False
    playlist_numbering: bool = False
    skip_explicit: bool = False
    ffmpeg_args: str | None = None
    yt_dlp_args: str | None = None
    proxy: str | None = None
    cookie_file: str | None = None
    archive: str | None = None

    @classmethod
    def from_user_settings(cls, settings: Any) -> DownloadSettings:
        """Create DownloadSettings from a UserSettings DB model."""
        return cls(
            audio_format=settings.audio_format or "mp3",
            audio_quality=settings.audio_quality or "best",
            bitrate=settings.bitrate,
            output_template=settings.output_template or "{artist} - {title}",
            max_filename_length=settings.max_filename_length or 255,
            restrict=settings.restrict,
            overwrite=settings.overwrite or "skip",
            embed_metadata=settings.embed_metadata if settings.embed_metadata is not None else True,
            embed_lyrics=settings.embed_lyrics if settings.embed_lyrics is not None else True,
            embed_cover=settings.embed_cover if settings.embed_cover is not None else True,
            id3_separator=settings.id3_separator or "/",
            sponsor_block=settings.sponsor_block or False,
            generate_lrc=settings.generate_lrc or False,
            playlist_numbering=settings.playlist_numbering or False,
            skip_explicit=settings.skip_explicit or False,
            ffmpeg_args=settings.ffmpeg_args,
            yt_dlp_args=settings.yt_dlp_args,
            proxy=settings.proxy,
            cookie_file=settings.cookie_file,
            archive=settings.archive,
        )

    @classmethod
    def from_defaults(cls) -> DownloadSettings:
        return cls()

    def to_core_settings(self) -> CoreDownloadSettings:
        """Convert to core DownloadSettings for the shared Downloader."""
        cookies_path = Path(self.cookie_file) if self.cookie_file else None
        if cookies_path and not cookies_path.exists():
            cookies_path = None
        return CoreDownloadSettings(
            audio_format=self.audio_format,
            audio_quality=self.audio_quality,
            bitrate=self.bitrate,
            output_template=self.output_template,
            max_filename_length=self.max_filename_length,
            restrict=self.restrict,
            overwrite=self.overwrite,
            embed_metadata=self.embed_metadata,
            embed_lyrics=self.embed_lyrics,
            embed_cover=self.embed_cover,
            id3_separator=self.id3_separator,
            sponsor_block=self.sponsor_block,
            generate_lrc=self.generate_lrc,
            playlist_numbering=self.playlist_numbering,
            skip_explicit=self.skip_explicit,
            ffmpeg_args=self.ffmpeg_args,
            yt_dlp_args=self.yt_dlp_args,
            proxy=self.proxy,
            cookies_path=cookies_path,
            archive=self.archive,
        )


@dataclass
class DownloadProgress:
    """Download progress information."""

    download_id: str
    status: DownloadStatus
    progress: float = 0.0
    speed: str | None = None
    eta: str | None = None
    filename: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "download_id": self.download_id,
            "status": self.status.value,
            "progress": self.progress,
            "speed": self.speed,
            "eta": self.eta,
            "filename": self.filename,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class DownloadRequest:
    """Download request with full song metadata."""

    download_id: str
    url: str
    title: str
    artist: str
    album: str | None = None
    cover_url: str | None = None
    duration: int | None = None
    output_format: str | None = None
    quality: str | None = None
    # Full metadata
    artists: list[str] = field(default_factory=list)
    album_artist: str | None = None
    genres: list[str] = field(default_factory=list)
    year: int | None = None
    date: str | None = None
    track_number: int | None = None
    disc_number: int | None = None
    disc_count: int | None = None
    tracks_count: int | None = None
    isrc: str | None = None
    publisher: str | None = None
    song_id: str | None = None
    song_url: str | None = None
    lyrics: str | None = None
    explicit: bool | None = None
    # List context
    list_name: str | None = None
    list_position: int | None = None
    list_length: int | None = None

    def to_meta(self) -> DownloadMeta:
        """Convert to core DownloadMeta for the shared Downloader."""
        return DownloadMeta(
            title=self.title,
            artist=self.artist,
            artists=self.artists or [self.artist],
            album=self.album,
            album_artist=self.album_artist,
            cover_url=self.cover_url if self.cover_url and is_safe_url(self.cover_url) else None,
            duration=self.duration,
            genres=self.genres,
            year=self.year,
            date=self.date,
            track_number=self.track_number,
            disc_number=self.disc_number,
            disc_count=self.disc_count,
            tracks_count=self.tracks_count,
            isrc=self.isrc,
            publisher=self.publisher,
            song_id=self.song_id,
            song_url=self.song_url,
            lyrics=self.lyrics,
            explicit=self.explicit,
            list_name=self.list_name,
            list_position=self.list_position,
            list_length=self.list_length,
        )


# ── Download Manager ──────────────────────────────────────────────

class DownloadService:
    """Manages download queue and progress tracking."""

    def __init__(self, download_dir: Path | None = None) -> None:
        self.download_dir = download_dir or Path(tempfile.gettempdir()) / "spotdl_downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self._downloads: dict[str, DownloadProgress] = {}
        self._tasks: dict[str, asyncio.Task[Path | None]] = {}
        self._progress_callbacks: dict[str, list[Callable[[DownloadProgress], None]]] = {}
        self._lock = asyncio.Lock()

    def get_progress(self, download_id: str) -> DownloadProgress | None:
        return self._downloads.get(download_id)

    def get_all_downloads(self) -> list[DownloadProgress]:
        return list(self._downloads.values())

    def register_callback(
        self, download_id: str, callback: Callable[[DownloadProgress], None]
    ) -> None:
        if download_id not in self._progress_callbacks:
            self._progress_callbacks[download_id] = []
        self._progress_callbacks[download_id].append(callback)

    def unregister_callback(
        self, download_id: str, callback: Callable[[DownloadProgress], None]
    ) -> None:
        if download_id in self._progress_callbacks:
            try:
                self._progress_callbacks[download_id].remove(callback)
            except ValueError:
                pass

    def _notify_progress(self, download_id: str) -> None:
        progress = self._downloads.get(download_id)
        if progress and download_id in self._progress_callbacks:
            for callback in self._progress_callbacks[download_id]:
                try:
                    callback(progress)
                except Exception as e:
                    logger.warning("Progress callback error: %s", e)

    async def start_download(
        self,
        request: DownloadRequest,
        settings: DownloadSettings | None = None,
    ) -> str:
        async with self._lock:
            audio_format = request.output_format or (settings.audio_format if settings else "mp3")

            progress = DownloadProgress(
                download_id=request.download_id,
                status=DownloadStatus.PENDING,
                filename=f"{request.artist} - {request.title}.{audio_format}",
            )
            self._downloads[request.download_id] = progress

            task = asyncio.create_task(self._download_task(request, settings))
            self._tasks[request.download_id] = task

        return request.download_id

    async def cancel_download(self, download_id: str) -> bool:
        async with self._lock:
            if download_id in self._tasks:
                self._tasks[download_id].cancel()
                if download_id in self._downloads:
                    self._downloads[download_id].status = DownloadStatus.CANCELLED
                    self._notify_progress(download_id)
                return True
        return False

    def get_file_path(self, download_id: str) -> Path | None:
        progress = self._downloads.get(download_id)
        if progress and progress.status == DownloadStatus.COMPLETED and progress.filename:
            file_path = self.download_dir / download_id / progress.filename
            if file_path.exists():
                return file_path
            download_dir = self.download_dir / download_id
            if download_dir.exists():
                for f in download_dir.iterdir():
                    if f.is_file() and f.suffix.lower() in {
                        ".mp3", ".m4a", ".flac", ".opus", ".ogg", ".wav",
                    }:
                        return f
        return None

    async def _download_task(
        self,
        request: DownloadRequest,
        settings: DownloadSettings | None = None,
    ) -> Path | None:
        download_id = request.download_id
        output_dir = self.download_dir / download_id
        output_dir.mkdir(parents=True, exist_ok=True)

        dl_settings = settings or DownloadSettings.from_defaults()

        # Apply per-request format/quality overrides
        if request.output_format:
            dl_settings.audio_format = request.output_format
        if request.quality:
            dl_settings.audio_quality = request.quality

        core_settings = dl_settings.to_core_settings()
        downloader = Downloader(core_settings)
        meta = request.to_meta()

        # Update progress
        self._downloads[download_id].status = DownloadStatus.DOWNLOADING
        self._notify_progress(download_id)

        def progress_hook(d: dict[str, Any]) -> None:
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    self._downloads[download_id].progress = min((downloaded / total) * 100, 99)
                self._downloads[download_id].speed = d.get("_speed_str", "")
                self._downloads[download_id].eta = d.get("_eta_str", "")
                self._notify_progress(download_id)
            elif d["status"] == "finished":
                self._downloads[download_id].progress = 99
                self._downloads[download_id].status = DownloadStatus.PROCESSING
                self._notify_progress(download_id)

        # Wrap raw yt-dlp hook into core's DownloadProgress callback
        def core_progress_callback(p: CoreDownloadProgress) -> None:
            if p.status == "downloading":
                self._downloads[download_id].progress = min(p.progress, 99)
                self._downloads[download_id].speed = p.speed or None
                self._downloads[download_id].eta = p.eta or None
                self._notify_progress(download_id)
            elif p.status == "finished":
                self._downloads[download_id].progress = 99
                self._downloads[download_id].status = DownloadStatus.PROCESSING
                self._notify_progress(download_id)

        try:
            output_path = await downloader.download(
                request.url, meta, output_dir, core_progress_callback,
            )

            # Embed metadata
            self._downloads[download_id].status = DownloadStatus.EMBEDDING
            self._downloads[download_id].progress = 99
            self._notify_progress(download_id)

            await downloader.embed_metadata(output_path, meta)

            # Embed lyrics
            if request.lyrics:
                await downloader.embed_lyrics(output_path, request.lyrics)
            else:
                lyrics = await self._fetch_lyrics(request.title, request.artist)
                if lyrics:
                    await downloader.embed_lyrics(output_path, lyrics)

            # Generate LRC file if enabled
            if dl_settings.generate_lrc:
                artists = request.artists if request.artists else [request.artist]
                generate_lrc(request.title, artists, output_path, request.lyrics)

            # Update filename in progress to match actual output
            self._downloads[download_id].filename = output_path.name

            # Mark as completed
            self._downloads[download_id].status = DownloadStatus.COMPLETED
            self._downloads[download_id].progress = 100
            self._downloads[download_id].completed_at = datetime.now()
            self._notify_progress(download_id)

            await downloader.close()
            logger.info("Download completed: %s", output_path)
            return output_path  # type: ignore[no-any-return]

        except asyncio.CancelledError:
            self._downloads[download_id].status = DownloadStatus.CANCELLED
            self._notify_progress(download_id)
            await downloader.close()
            raise

        except Exception as e:
            # Log the full exception with traceback for debugging
            logger.error(
                "Download %s failed for '%s' by %s",
                download_id,
                request.title,
                request.artist,
                exc_info=True,  # This includes the full traceback
            )
            self._downloads[download_id].status = DownloadStatus.FAILED
            self._downloads[download_id].error = str(e)
            self._notify_progress(download_id)
            await downloader.close()
            return None

    async def _fetch_lyrics(self, title: str, artist: str) -> str | None:
        import httpx

        try:
            from spotdl.providers.lyrics.genius import GeniusWebProvider

            async with httpx.AsyncClient(timeout=10.0) as client:
                provider = GeniusWebProvider(client)
                return await provider.get_lyrics(title, [artist])
        except ImportError:
            logger.debug("Lyrics provider not available")
        except Exception as e:
            logger.debug("Failed to fetch lyrics: %s", e)
        return None


# ── Global instance ───────────────────────────────────────────────

_download_service: DownloadService | None = None


def get_download_service() -> DownloadService:
    global _download_service
    if _download_service is None:
        _download_service = DownloadService()
    return _download_service


def create_download_id() -> str:
    return str(uuid.uuid4())
