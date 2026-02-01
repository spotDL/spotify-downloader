"""Download service using yt-dlp for audio extraction."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Allowed schemes for cover URLs
ALLOWED_SCHEMES = {"http", "https"}

# Allowlisted CDN domains for cover art
COVER_URL_ALLOWLIST = {
    # Spotify CDN
    "i.scdn.co",
    "mosaic.scdn.co",
    # YouTube/Google
    "i.ytimg.com",
    "yt3.ggpht.com",
    "lh3.googleusercontent.com",
    # Apple Music
    "is1-ssl.mzstatic.com",
    "is2-ssl.mzstatic.com",
    "is3-ssl.mzstatic.com",
    "is4-ssl.mzstatic.com",
    "is5-ssl.mzstatic.com",
    # Deezer
    "cdns-images.dzcdn.net",
    "e-cdns-images.dzcdn.net",
    # SoundCloud
    "i1.sndcdn.com",
    # Bandcamp
    "f4.bcbits.com",
    # Tidal
    "resources.tidal.com",
}


def is_safe_url(url: str) -> bool:
    """
    Validate that a URL is safe to fetch (not pointing to internal resources).

    Args:
        url: The URL to validate

    Returns:
        True if the URL is safe to fetch, False otherwise
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme.lower() not in ALLOWED_SCHEMES:
            logger.warning(f"Blocked URL with disallowed scheme: {parsed.scheme}")
            return False

        # Check for empty or missing hostname
        hostname = parsed.hostname
        if not hostname:
            logger.warning("Blocked URL with missing hostname")
            return False

        # Check against allowlist
        hostname_lower = hostname.lower()
        if hostname_lower not in COVER_URL_ALLOWLIST:
            # Check if it's a subdomain of an allowlisted domain
            is_allowed = any(
                hostname_lower.endswith(f".{domain}") for domain in COVER_URL_ALLOWLIST
            )
            if not is_allowed:
                logger.warning(f"Blocked URL with non-allowlisted hostname: {hostname}")
                return False

        # Additional safety: resolve hostname and check IP
        # This protects against DNS rebinding attacks
        try:
            resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
            for _, _, _, _, sockaddr in resolved_ips:
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)

                # Block private, loopback, link-local, and reserved addresses
                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_reserved
                    or ip.is_multicast
                ):
                    logger.warning(f"Blocked URL resolving to unsafe IP: {ip_str}")
                    return False

                # Explicitly block AWS/cloud metadata endpoint
                if ip_str == "169.254.169.254":
                    logger.warning("Blocked AWS metadata endpoint")
                    return False

        except (socket.gaierror, socket.herror) as e:
            logger.warning(f"Failed to resolve hostname {hostname}: {e}")
            return False

        return True

    except Exception as e:
        logger.warning(f"URL validation error: {e}")
        return False


class DownloadStatus(str, Enum):
    """Download status enum."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadProgress:
    """Download progress information."""

    download_id: str
    status: DownloadStatus
    progress: float = 0.0  # 0-100
    speed: str | None = None
    eta: str | None = None
    filename: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
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
    """Download request information."""

    download_id: str
    url: str
    title: str
    artist: str
    album: str | None = None
    cover_url: str | None = None
    duration: int | None = None
    output_format: str = "mp3"
    quality: str = "320"  # kbps for mp3


class DownloadManager:
    """Manages download queue and progress tracking."""

    def __init__(self, download_dir: Path | None = None) -> None:
        """Initialize download manager."""
        self.download_dir = download_dir or Path(tempfile.gettempdir()) / "spotdl_downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self._downloads: dict[str, DownloadProgress] = {}
        self._tasks: dict[str, asyncio.Task[Path | None]] = {}
        self._progress_callbacks: dict[str, list[Callable[[DownloadProgress], None]]] = {}
        self._lock = asyncio.Lock()

    def get_progress(self, download_id: str) -> DownloadProgress | None:
        """Get download progress by ID."""
        return self._downloads.get(download_id)

    def get_all_downloads(self) -> list[DownloadProgress]:
        """Get all downloads."""
        return list(self._downloads.values())

    def register_callback(
        self, download_id: str, callback: Callable[[DownloadProgress], None]
    ) -> None:
        """Register a progress callback for a download."""
        if download_id not in self._progress_callbacks:
            self._progress_callbacks[download_id] = []
        self._progress_callbacks[download_id].append(callback)

    def unregister_callback(
        self, download_id: str, callback: Callable[[DownloadProgress], None]
    ) -> None:
        """Unregister a progress callback."""
        if download_id in self._progress_callbacks:
            try:
                self._progress_callbacks[download_id].remove(callback)
            except ValueError:
                logger.debug("Callback not found for download %s", download_id)

    def _notify_progress(self, download_id: str) -> None:
        """Notify all callbacks of progress update."""
        progress = self._downloads.get(download_id)
        if progress and download_id in self._progress_callbacks:
            for callback in self._progress_callbacks[download_id]:
                try:
                    callback(progress)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")

    async def start_download(self, request: DownloadRequest) -> str:
        """Start a new download."""
        async with self._lock:
            # Create progress tracker
            progress = DownloadProgress(
                download_id=request.download_id,
                status=DownloadStatus.PENDING,
                filename=f"{request.artist} - {request.title}.{request.output_format}",
            )
            self._downloads[request.download_id] = progress

            # Start download task
            task = asyncio.create_task(self._download_task(request))
            self._tasks[request.download_id] = task

        return request.download_id

    async def cancel_download(self, download_id: str) -> bool:
        """Cancel a download."""
        async with self._lock:
            if download_id in self._tasks:
                task = self._tasks[download_id]
                task.cancel()

                if download_id in self._downloads:
                    self._downloads[download_id].status = DownloadStatus.CANCELLED
                    self._notify_progress(download_id)

                return True
        return False

    def get_file_path(self, download_id: str) -> Path | None:
        """Get the file path for a completed download."""
        progress = self._downloads.get(download_id)
        if progress and progress.status == DownloadStatus.COMPLETED and progress.filename:
            file_path = self.download_dir / download_id / progress.filename
            if file_path.exists():
                return file_path
        return None

    async def _download_task(self, request: DownloadRequest) -> Path | None:
        """Execute the download task."""
        import yt_dlp

        download_id = request.download_id
        output_dir = self.download_dir / download_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_title = "".join(c for c in request.title if c.isalnum() or c in " -_").strip()
        safe_artist = "".join(c for c in request.artist if c.isalnum() or c in " -_").strip()
        output_filename = f"{safe_artist} - {safe_title}"
        output_path = output_dir / f"{output_filename}.{request.output_format}"

        # Update progress
        self._downloads[download_id].status = DownloadStatus.DOWNLOADING
        self._downloads[download_id].filename = output_path.name
        self._notify_progress(download_id)

        def progress_hook(d: dict[str, Any]) -> None:
            """yt-dlp progress hook."""
            if d["status"] == "downloading":
                # Extract progress info
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)

                if total > 0:
                    percent = (downloaded / total) * 100
                    self._downloads[download_id].progress = min(percent, 99)

                self._downloads[download_id].speed = d.get("_speed_str", "")
                self._downloads[download_id].eta = d.get("_eta_str", "")
                self._notify_progress(download_id)

            elif d["status"] == "finished":
                self._downloads[download_id].progress = 99
                self._downloads[download_id].status = DownloadStatus.PROCESSING
                self._notify_progress(download_id)

        # yt-dlp options
        ydl_opts: dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": str(output_dir / f"{output_filename}.%(ext)s"),
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        # Add format conversion
        if request.output_format == "mp3":
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": request.quality,
                }
            ]
        elif request.output_format == "m4a":
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                    "preferredquality": request.quality,
                }
            ]
        elif request.output_format == "opus":
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "opus",
                    "preferredquality": request.quality,
                }
            ]

        try:
            # Run yt-dlp in executor to not block
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_ytdlp, ydl_opts, request.url)

            # Embed metadata
            if output_path.exists():
                await self._embed_metadata(output_path, request)

            # Mark as completed
            self._downloads[download_id].status = DownloadStatus.COMPLETED
            self._downloads[download_id].progress = 100
            self._downloads[download_id].completed_at = datetime.now()
            self._notify_progress(download_id)

            logger.info(f"Download completed: {output_path}")
            return output_path

        except asyncio.CancelledError:
            self._downloads[download_id].status = DownloadStatus.CANCELLED
            self._notify_progress(download_id)
            raise

        except Exception as e:
            logger.error(f"Download failed: {e}")
            self._downloads[download_id].status = DownloadStatus.FAILED
            self._downloads[download_id].error = str(e)
            self._notify_progress(download_id)
            return None

    def _run_ytdlp(self, opts: dict[str, Any], url: str) -> None:
        """Run yt-dlp synchronously."""
        import yt_dlp

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    async def _embed_metadata(self, file_path: Path, request: DownloadRequest) -> None:
        """Embed metadata into the audio file."""
        import httpx
        from mutagen.easyid3 import EasyID3
        from mutagen.id3 import APIC, ID3
        from mutagen.mp3 import MP3

        try:
            # Load the file
            if file_path.suffix.lower() == ".mp3":
                audio = MP3(file_path, ID3=EasyID3)

                # Add basic metadata
                audio["title"] = request.title
                audio["artist"] = request.artist
                if request.album:
                    audio["album"] = request.album

                audio.save()

                # Add cover art if available
                if request.cover_url and is_safe_url(request.cover_url):
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(request.cover_url)
                            if response.status_code == 200:
                                # Load ID3 tags
                                audio_id3 = ID3(file_path)
                                audio_id3.add(
                                    APIC(
                                        encoding=3,
                                        mime="image/jpeg",
                                        type=3,
                                        desc="Cover",
                                        data=response.content,
                                    )
                                )
                                audio_id3.save()
                    except Exception as e:
                        logger.warning(f"Failed to embed cover art: {e}")

                logger.info(f"Metadata embedded: {file_path}")

        except Exception as e:
            logger.warning(f"Failed to embed metadata: {e}")


# Global download manager instance
_download_manager: DownloadManager | None = None


def get_download_manager() -> DownloadManager:
    """Get the global download manager instance."""
    global _download_manager
    if _download_manager is None:
        _download_manager = DownloadManager()
    return _download_manager


def create_download_id() -> str:
    """Create a unique download ID."""
    return str(uuid.uuid4())
