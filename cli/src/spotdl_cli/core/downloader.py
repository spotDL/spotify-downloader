"""Download manager using yt-dlp and mutagen for metadata embedding."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import yt_dlp

from spotdl_cli.config import Settings, get_settings
from spotdl_cli.core.types import (
    DownloadItem,
    DownloadResult,
    DownloadStatus,
    Song,
)

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Raised when a download fails."""


class DownloadProgress:
    """Progress information for a download."""

    def __init__(self) -> None:
        self.status: str = ""
        self.progress: float = 0.0
        self.speed: str = ""
        self.eta: str = ""
        self.filename: str = ""


class Downloader:
    """
    Async download manager using yt-dlp.

    Features:
    - Download audio from YouTube, SoundCloud, Bandcamp, etc.
    - Progress callbacks for UI updates
    - Metadata embedding with mutagen
    - Cover art embedding
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the downloader.

        Args:
            settings: Settings instance (uses global if not provided)
        """
        self._settings = settings or get_settings()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for cover downloads."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    def _get_output_template(self, song: Song) -> str:
        """Generate output filename from template."""
        template = self._settings.output_template

        # Replace template variables
        replacements = {
            "{artist}": self._sanitize_filename(song.artist),
            "{artists}": self._sanitize_filename(", ".join(song.artists)),
            "{title}": self._sanitize_filename(song.name),
            "{album}": self._sanitize_filename(song.album_name or "Unknown"),
            "{year}": str(song.year) if song.year else "Unknown",
            "{track_number}": str(song.track_number).zfill(2),
            "{disc_number}": str(song.disc_number),
        }

        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)

        return result

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize a string for use as filename."""
        # Remove/replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")

        # Remove leading/trailing dots and spaces
        name = name.strip(". ")

        # Limit length
        if len(name) > 200:
            name = name[:200]

        return name or "Unknown"

    def _get_yt_dlp_options(
        self,
        output_path: Path,
        progress_callback: Callable[[DownloadProgress], None] | None = None,
    ) -> dict[str, Any]:
        """Get yt-dlp options for download."""
        # Format mapping
        format_map = {
            "mp3": "mp3",
            "m4a": "m4a",
            "flac": "flac",
            "opus": "opus",
            "ogg": "vorbis",
            "wav": "wav",
        }

        audio_format = format_map.get(
            self._settings.audio_format,
            "mp3",
        )

        # Quality mapping
        quality_map = {
            "best": "0",
            "320k": "320",
            "256k": "256",
            "192k": "192",
            "128k": "128",
        }

        audio_quality = quality_map.get(
            self._settings.audio_quality,
            "0",
        )

        options: dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": str(output_path),
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": audio_quality,
                }
            ],
        }

        # Add cookies if available
        if self._settings.cookies_path.exists():
            options["cookiefile"] = str(self._settings.cookies_path)

        # Add progress hook
        if progress_callback:
            def hook(d: dict[str, Any]) -> None:
                progress = DownloadProgress()
                progress.status = d.get("status", "")
                progress.filename = d.get("filename", "")

                if d.get("status") == "downloading":
                    # Extract progress percentage
                    if "downloaded_bytes" in d and "total_bytes" in d:
                        progress.progress = (
                            d["downloaded_bytes"] / d["total_bytes"] * 100
                        )
                    elif "downloaded_bytes" in d and "total_bytes_estimate" in d:
                        progress.progress = (
                            d["downloaded_bytes"] / d["total_bytes_estimate"] * 100
                        )
                    elif "_percent_str" in d:
                        # Parse percentage string
                        pct_str = d["_percent_str"].strip().rstrip("%")
                        try:
                            progress.progress = float(pct_str)
                        except ValueError:
                            pass

                    # Speed
                    if "_speed_str" in d:
                        progress.speed = d["_speed_str"].strip()
                    elif d.get("speed"):
                        progress.speed = self._format_speed(d["speed"])

                    # ETA
                    if "_eta_str" in d:
                        progress.eta = d["_eta_str"].strip()
                    elif d.get("eta"):
                        progress.eta = self._format_eta(d["eta"])

                elif d.get("status") == "finished":
                    progress.progress = 100.0

                progress_callback(progress)

            options["progress_hooks"] = [hook]

        return options

    @staticmethod
    def _format_speed(speed: float) -> str:
        """Format speed in bytes/sec to human readable."""
        if speed < 1024:
            return f"{speed:.0f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed / 1024:.1f} KB/s"
        else:
            return f"{speed / (1024 * 1024):.1f} MB/s"

    @staticmethod
    def _format_eta(eta: int) -> str:
        """Format ETA seconds to human readable."""
        if eta < 60:
            return f"{eta}s"
        elif eta < 3600:
            return f"{eta // 60}m {eta % 60}s"
        else:
            hours = eta // 3600
            minutes = (eta % 3600) // 60
            return f"{hours}h {minutes}m"

    async def download(
        self,
        result: DownloadResult,
        song: Song,
        progress_callback: Callable[[DownloadProgress], None] | None = None,
    ) -> Path:
        """
        Download audio from a URL.

        Args:
            result: Download result with URL
            song: Song metadata for filename and embedding
            progress_callback: Optional callback for progress updates

        Returns:
            Path to downloaded file

        Raises:
            DownloadError: If download fails
        """
        # Generate output path
        output_name = self._get_output_template(song)
        output_dir = self._settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Base path without extension (yt-dlp adds extension)
        base_path = output_dir / output_name

        # Check if file exists and overwrite setting
        expected_path = base_path.with_suffix(f".{self._settings.audio_format}")
        if expected_path.exists() and not self._settings.overwrite:
            logger.info(f"File already exists: {expected_path}")
            return expected_path

        # Get yt-dlp options
        options = self._get_yt_dlp_options(
            base_path,
            progress_callback,
        )

        try:
            # Run yt-dlp in thread pool (it's not async)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._run_yt_dlp,
                result.url,
                options,
            )

            # Find the output file (extension might differ)
            output_file = self._find_output_file(base_path)
            if not output_file:
                raise DownloadError(f"Output file not found: {base_path}")

            logger.info(f"Downloaded: {output_file}")
            return output_file

        except yt_dlp.utils.DownloadError as e:
            raise DownloadError(f"Download failed: {e}") from e
        except Exception as e:
            raise DownloadError(f"Unexpected error: {e}") from e

    def _run_yt_dlp(self, url: str, options: dict[str, Any]) -> None:
        """Run yt-dlp download (blocking)."""
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

    def _find_output_file(self, base_path: Path) -> Path | None:
        """Find the output file (may have different extension)."""
        # Common audio extensions
        extensions = [
            self._settings.audio_format,
            "mp3", "m4a", "flac", "opus", "ogg", "wav",
            "webm", "mp4",  # Before conversion
        ]

        for ext in extensions:
            path = base_path.with_suffix(f".{ext}")
            if path.exists():
                return path

        # Check for files with same stem
        for path in base_path.parent.glob(f"{base_path.stem}.*"):
            if path.suffix.lower() in [f".{e}" for e in extensions]:
                return path

        return None

    async def embed_metadata(
        self,
        file_path: Path,
        song: Song,
    ) -> None:
        """
        Embed metadata into audio file using mutagen.

        Args:
            file_path: Path to audio file
            song: Song metadata to embed
        """
        if not self._settings.embed_metadata:
            return

        try:
            # Import mutagen here to handle different formats

            suffix = file_path.suffix.lower()

            if suffix == ".mp3":
                await self._embed_mp3_metadata(file_path, song)
            elif suffix == ".m4a":
                await self._embed_m4a_metadata(file_path, song)
            elif suffix == ".flac":
                await self._embed_flac_metadata(file_path, song)
            elif suffix in (".opus", ".ogg"):
                await self._embed_ogg_metadata(file_path, song)
            else:
                logger.warning(f"Unsupported format for metadata: {suffix}")

        except Exception as e:
            logger.error(f"Failed to embed metadata: {e}")

    async def _embed_mp3_metadata(self, file_path: Path, song: Song) -> None:
        """Embed metadata into MP3 file."""
        from mutagen.easyid3 import EasyID3
        from mutagen.id3 import ID3NoHeaderError

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            try:
                audio = EasyID3(file_path)
            except ID3NoHeaderError:
                audio = EasyID3()
                audio.save(file_path)
                audio = EasyID3(file_path)

            audio["title"] = song.name
            audio["artist"] = song.artists
            audio["albumartist"] = [song.album_artist or song.artist]
            audio["album"] = [song.album_name] if song.album_name else []
            audio["genre"] = song.genres if song.genres else []
            audio["date"] = [song.date] if song.date else (
                [str(song.year)] if song.year else []
            )
            audio["tracknumber"] = [str(song.track_number)]
            audio["discnumber"] = [str(song.disc_number)]

            audio.save()

        await loop.run_in_executor(None, _embed)

        # Embed cover art separately (needs full ID3)
        if self._settings.embed_cover and song.cover_url:
            await self._embed_mp3_cover(file_path, song.cover_url)

    async def _embed_mp3_cover(self, file_path: Path, cover_url: str) -> None:
        """Embed cover art into MP3 file."""
        from mutagen.id3 import APIC, ID3

        cover_data = await self._download_cover(cover_url)
        if not cover_data:
            return

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = ID3(file_path)
            audio.delall("APIC")
            audio.add(
                APIC(
                    encoding=3,  # UTF-8
                    mime="image/jpeg",
                    type=3,  # Cover (front)
                    desc="Cover",
                    data=cover_data,
                )
            )
            audio.save()

        await loop.run_in_executor(None, _embed)

    async def _embed_m4a_metadata(self, file_path: Path, song: Song) -> None:
        """Embed metadata into M4A file."""
        from mutagen.mp4 import MP4

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = MP4(file_path)

            audio["\xa9nam"] = [song.name]  # Title
            audio["\xa9ART"] = song.artists  # Artists
            audio["aART"] = [song.album_artist or song.artist]  # Album artist
            audio["\xa9alb"] = [song.album_name] if song.album_name else []  # Album
            audio["\xa9gen"] = song.genres if song.genres else []  # Genre
            audio["\xa9day"] = [song.date] if song.date else (
                [str(song.year)] if song.year else []
            )
            audio["trkn"] = [(song.track_number, 0)]  # Track number
            audio["disk"] = [(song.disc_number, 0)]  # Disc number

            audio.save()

        await loop.run_in_executor(None, _embed)

        # Embed cover art
        if self._settings.embed_cover and song.cover_url:
            await self._embed_m4a_cover(file_path, song.cover_url)

    async def _embed_m4a_cover(self, file_path: Path, cover_url: str) -> None:
        """Embed cover art into M4A file."""
        from mutagen.mp4 import MP4, MP4Cover

        cover_data = await self._download_cover(cover_url)
        if not cover_data:
            return

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = MP4(file_path)
            audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()

        await loop.run_in_executor(None, _embed)

    async def _embed_flac_metadata(self, file_path: Path, song: Song) -> None:
        """Embed metadata into FLAC file."""
        from mutagen.flac import FLAC

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = FLAC(file_path)

            audio["title"] = [song.name]
            audio["artist"] = song.artists
            audio["albumartist"] = [song.album_artist or song.artist]
            audio["album"] = [song.album_name] if song.album_name else []
            audio["genre"] = song.genres if song.genres else []
            audio["date"] = [song.date] if song.date else (
                [str(song.year)] if song.year else []
            )
            audio["tracknumber"] = [str(song.track_number)]
            audio["discnumber"] = [str(song.disc_number)]

            audio.save()

        await loop.run_in_executor(None, _embed)

        # Embed cover art
        if self._settings.embed_cover and song.cover_url:
            await self._embed_flac_cover(file_path, song.cover_url)

    async def _embed_flac_cover(self, file_path: Path, cover_url: str) -> None:
        """Embed cover art into FLAC file."""
        from mutagen.flac import FLAC, Picture

        cover_data = await self._download_cover(cover_url)
        if not cover_data:
            return

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = FLAC(file_path)
            audio.clear_pictures()

            picture = Picture()
            picture.type = 3  # Cover (front)
            picture.mime = "image/jpeg"
            picture.desc = "Cover"
            picture.data = cover_data

            audio.add_picture(picture)
            audio.save()

        await loop.run_in_executor(None, _embed)

    async def _embed_ogg_metadata(self, file_path: Path, song: Song) -> None:
        """Embed metadata into OGG/Opus file."""
        from mutagen.oggopus import OggOpus
        from mutagen.oggvorbis import OggVorbis

        loop = asyncio.get_event_loop()
        suffix = file_path.suffix.lower()

        def _embed() -> None:
            if suffix == ".opus":
                audio = OggOpus(file_path)
            else:
                audio = OggVorbis(file_path)

            audio["title"] = [song.name]
            audio["artist"] = song.artists
            audio["albumartist"] = [song.album_artist or song.artist]
            audio["album"] = [song.album_name] if song.album_name else []
            audio["genre"] = song.genres if song.genres else []
            audio["date"] = [song.date] if song.date else (
                [str(song.year)] if song.year else []
            )
            audio["tracknumber"] = [str(song.track_number)]
            audio["discnumber"] = [str(song.disc_number)]

            audio.save()

        await loop.run_in_executor(None, _embed)

        # Embed cover art for OGG/Opus
        if self._settings.embed_cover and song.cover_url:
            await self._embed_ogg_cover(file_path, song.cover_url)

    async def _embed_ogg_cover(self, file_path: Path, cover_url: str) -> None:
        """Embed cover art into OGG/Opus file using METADATA_BLOCK_PICTURE."""
        import base64
        import struct

        from mutagen.flac import Picture
        from mutagen.oggopus import OggOpus
        from mutagen.oggvorbis import OggVorbis

        cover_data = await self._download_cover(cover_url)
        if not cover_data:
            return

        loop = asyncio.get_event_loop()
        suffix = file_path.suffix.lower()

        def _embed() -> None:
            # Create a FLAC Picture object
            picture = Picture()
            picture.type = 3  # Cover (front)
            picture.mime = "image/jpeg"
            picture.desc = "Cover"
            picture.data = cover_data

            # For OGG, we need to encode the picture as base64
            # The picture data must be in FLAC format
            picture_data = picture.write()
            encoded_data = base64.b64encode(picture_data).decode("ascii")

            # Load the appropriate OGG format
            if suffix == ".opus":
                audio = OggOpus(file_path)
            else:
                audio = OggVorbis(file_path)

            # Set the METADATA_BLOCK_PICTURE field
            audio["metadata_block_picture"] = [encoded_data]
            audio.save()

        await loop.run_in_executor(None, _embed)

    async def _download_cover(self, cover_url: str) -> bytes | None:
        """Download cover art image."""
        try:
            client = await self._get_http_client()
            response = await client.get(cover_url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.warning(f"Failed to download cover: {e}")
            return None

    async def embed_lyrics(self, file_path: Path, lyrics: str) -> None:
        """
        Embed lyrics into audio file.

        Args:
            file_path: Path to audio file
            lyrics: Lyrics text to embed
        """
        if not self._settings.embed_lyrics or not lyrics:
            return

        suffix = file_path.suffix.lower()

        try:
            if suffix == ".mp3":
                await self._embed_mp3_lyrics(file_path, lyrics)
            elif suffix == ".m4a":
                await self._embed_m4a_lyrics(file_path, lyrics)
            elif suffix == ".flac":
                await self._embed_flac_lyrics(file_path, lyrics)
            # OGG/Opus lyrics support is limited
        except Exception as e:
            logger.warning(f"Failed to embed lyrics: {e}")

    async def _embed_mp3_lyrics(self, file_path: Path, lyrics: str) -> None:
        """Embed lyrics into MP3 file."""
        from mutagen.id3 import ID3, USLT

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = ID3(file_path)
            audio.delall("USLT")
            audio.add(
                USLT(
                    encoding=3,  # UTF-8
                    lang="eng",
                    desc="Lyrics",
                    text=lyrics,
                )
            )
            audio.save()

        await loop.run_in_executor(None, _embed)

    async def _embed_m4a_lyrics(self, file_path: Path, lyrics: str) -> None:
        """Embed lyrics into M4A file."""
        from mutagen.mp4 import MP4

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = MP4(file_path)
            audio["\xa9lyr"] = [lyrics]
            audio.save()

        await loop.run_in_executor(None, _embed)

    async def _embed_flac_lyrics(self, file_path: Path, lyrics: str) -> None:
        """Embed lyrics into FLAC file."""
        from mutagen.flac import FLAC

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = FLAC(file_path)
            audio["lyrics"] = [lyrics]
            audio.save()

        await loop.run_in_executor(None, _embed)


class DownloadManager:
    """
    Manages concurrent downloads with queue integration.

    Coordinates between the download queue and the downloader,
    processing items concurrently up to the configured limit.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        max_concurrent: int | None = None,
    ) -> None:
        """
        Initialize the download manager.

        Args:
            settings: Settings instance
            max_concurrent: Override max concurrent downloads
        """
        self._settings = settings or get_settings()
        self._max_concurrent = max_concurrent or self._settings.threads
        self._downloader = Downloader(self._settings)
        self._active_tasks: dict[str, asyncio.Task[Path | None]] = {}
        self._stop_event = asyncio.Event()

    async def close(self) -> None:
        """Close the download manager."""
        self._stop_event.set()
        await self._downloader.close()

        # Cancel active tasks
        for task in self._active_tasks.values():
            task.cancel()

        if self._active_tasks:
            await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)

    async def download_item(
        self,
        item_id: str,
        item: DownloadItem,
        status_callback: (
            Callable[[str, DownloadStatus, float, str, str, str | None], None] | None
        ) = None,
    ) -> Path | None:
        """
        Download a single item.

        Args:
            item_id: Item ID for tracking
            item: Download item with song and result
            status_callback: Callback for status updates
                (item_id, status, progress, speed, eta, error)

        Returns:
            Path to downloaded file or None if failed
        """
        if not item.result:
            if status_callback:
                status_callback(
                    item_id,
                    DownloadStatus.FAILED,
                    0.0, "", "",
                    "No download result available",
                )
            return None

        def progress_callback(progress: DownloadProgress) -> None:
            if status_callback:
                status = DownloadStatus.DOWNLOADING
                if progress.status == "finished":
                    status = DownloadStatus.CONVERTING

                status_callback(
                    item_id,
                    status,
                    progress.progress,
                    progress.speed,
                    progress.eta,
                    None,
                )

        try:
            # Update status to downloading
            if status_callback:
                status_callback(
                    item_id,
                    DownloadStatus.DOWNLOADING,
                    0.0, "", "", None,
                )

            # Download
            output_path = await self._downloader.download(
                item.result,
                item.song,
                progress_callback,
            )

            # Embed metadata
            if status_callback:
                status_callback(
                    item_id,
                    DownloadStatus.EMBEDDING,
                    100.0, "", "", None,
                )

            await self._downloader.embed_metadata(output_path, item.song)

            # Embed lyrics if available
            if item.song.lyrics:
                await self._downloader.embed_lyrics(output_path, item.song.lyrics)

            # Complete
            if status_callback:
                status_callback(
                    item_id,
                    DownloadStatus.COMPLETED,
                    100.0, "", "", None,
                )

            return output_path

        except DownloadError as e:
            logger.error(f"Download failed for {item.song.display_name}: {e}")
            if status_callback:
                status_callback(
                    item_id,
                    DownloadStatus.FAILED,
                    0.0, "", "",
                    str(e),
                )
            return None

        except Exception as e:
            logger.error(f"Unexpected error downloading {item.song.display_name}: {e}")
            if status_callback:
                status_callback(
                    item_id,
                    DownloadStatus.FAILED,
                    0.0, "", "",
                    f"Unexpected error: {e}",
                )
            return None
