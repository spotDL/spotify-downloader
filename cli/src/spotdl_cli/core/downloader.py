"""Download manager for CLI - thin wrapper around spotdl_core.download."""

from __future__ import annotations

import asyncio
import logging
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

from spotdl_core.download import (
    Archive,
    DownloadError,
    DownloadMeta,
    DownloadProgress,
    DownloadSettings,
    Downloader,
    generate_lrc,
)

from spotdl_cli.config import Settings, get_settings
from spotdl_cli.core.metadata_reader import SUPPORTED_FORMATS, extract_spotify_url
from spotdl_cli.core.types import (
    DownloadItem,
    DownloadResult,
    DownloadStatus,
    Song,
)

logger = logging.getLogger(__name__)

# Re-export for backwards compatibility
__all__ = ["DownloadError", "DownloadManager", "DownloadProgress"]


def _settings_to_download_settings(settings: Settings) -> DownloadSettings:
    """Convert CLI Settings to core DownloadSettings."""
    return DownloadSettings(
        audio_format=settings.audio_format,
        audio_quality=settings.audio_quality,
        bitrate=settings.bitrate,
        output_template=settings.output_template,
        max_filename_length=settings.max_filename_length,
        restrict=settings.restrict,
        overwrite=settings.overwrite,
        embed_metadata=settings.embed_metadata,
        embed_lyrics=settings.embed_lyrics,
        embed_cover=settings.embed_cover,
        id3_separator=settings.id3_separator,
        sponsor_block=settings.sponsor_block,
        sponsor_block_categories=settings.sponsor_block_categories,
        generate_lrc=settings.generate_lrc,
        playlist_numbering=settings.playlist_numbering,
        skip_explicit=settings.skip_explicit,
        ffmpeg_args=settings.ffmpeg_args,
        yt_dlp_args=settings.yt_dlp_args,
        proxy=settings.proxy,
        cookies_path=settings.cookies_path if settings.cookies_path.exists() else None,
        archive=settings.archive,
    )


def _song_to_meta(song: Song) -> DownloadMeta:
    """Convert a Song to a DownloadMeta for the core downloader."""
    return DownloadMeta(
        title=song.name,
        artist=song.artist,
        artists=list(song.artists),
        album=song.album_name or None,
        album_artist=song.album_artist or None,
        cover_url=song.cover_url,
        duration=song.duration,
        genres=list(song.genres) if song.genres else [],
        year=song.year,
        date=song.date,
        track_number=song.track_number,
        disc_number=song.disc_number,
        disc_count=song.disc_count,
        tracks_count=song.tracks_count,
        isrc=song.isrc,
        publisher=song.publisher,
        song_id=song.song_id,
        song_url=song.url,
        lyrics=song.lyrics,
        explicit=song.explicit,
        list_name=song.list_name,
        list_position=song.list_position,
        list_length=song.list_length,
    )


class DownloadManager:
    """
    Manages concurrent downloads with queue integration.

    Coordinates between the download queue and the core Downloader,
    processing items concurrently up to the configured limit.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        max_concurrent: int | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._max_concurrent = max_concurrent or self._settings.threads
        self._dl_settings = _settings_to_download_settings(self._settings)
        self._downloader = Downloader(self._dl_settings)
        self._active_tasks: dict[str, asyncio.Task[Path | None]] = {}
        self._stop_event = asyncio.Event()

        # Archive for URL deduplication
        self._archive = Archive()
        if self._settings.archive:
            self._archive.load(self._settings.archive)

        # Known songs (from scan_for_songs)
        self._known_songs: dict[str, list[Path]] = {}
        if self._settings.scan_for_songs:
            self._scan_existing_songs()

    def _scan_existing_songs(self) -> None:
        """Scan output directory for existing songs by reading Spotify URLs from metadata."""
        output_dir = self._settings.output_dir
        if not output_dir.exists():
            return

        for ext in SUPPORTED_FORMATS:
            for file_path in output_dir.rglob(f"*{ext}"):
                try:
                    url = extract_spotify_url(file_path)
                    if url:
                        self._known_songs.setdefault(url, []).append(file_path)
                except Exception:
                    continue

        if self._known_songs:
            logger.info("Found %d existing songs in %s", len(self._known_songs), output_dir)

    def is_song_archived(self, song: Song) -> bool:
        """Check if a song URL is in the archive."""
        return song.url in self._archive

    def is_song_known(self, song: Song) -> bool:
        """Check if a song exists in the scanned local files."""
        return song.url in self._known_songs

    def filter_songs(self, songs: list[Song]) -> list[Song]:
        """Filter out songs that are already archived or known."""
        filtered = []
        for song in songs:
            if self._settings.skip_explicit and song.explicit:
                logger.info("Skipping explicit track: %s", song.name)
                continue
            if song.url in self._archive:
                logger.debug("Skipping archived: %s", song.display_name)
                continue
            if song.url in self._known_songs and self._settings.overwrite == "skip":
                logger.debug("Skipping known: %s", song.display_name)
                continue
            filtered.append(song)
        return filtered

    async def close(self) -> None:
        """Close the download manager."""
        self._stop_event.set()

        if self._settings.archive:
            self._archive.save(self._settings.archive)

        await self._downloader.close()

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
        """Download a single item."""
        if not item.result:
            if status_callback:
                status_callback(
                    item_id, DownloadStatus.FAILED, 0.0, "", "",
                    "No download result available",
                )
            return None

        # Skip explicit tracks
        if self._settings.skip_explicit and item.song.explicit:
            logger.info("Skipping explicit track: %s", item.song.name)
            if status_callback:
                status_callback(item_id, DownloadStatus.COMPLETED, 100.0, "", "", None)
            return None

        # Skip if archived
        if item.song.url in self._archive:
            logger.debug("Skipping archived: %s", item.song.display_name)
            if status_callback:
                status_callback(item_id, DownloadStatus.COMPLETED, 100.0, "", "", None)
            return None

        meta = _song_to_meta(item.song)
        output_dir = self._settings.output_dir

        # Check .skip file
        output_name = self._downloader.get_output_template(meta)
        expected_path = (output_dir / output_name).with_suffix(f".{self._settings.audio_format}")
        skip_file = expected_path.with_suffix(expected_path.suffix + ".skip")
        if self._settings.respect_skip_file and skip_file.exists():
            logger.info("Skipping (skip file exists): %s", expected_path)
            if status_callback:
                status_callback(item_id, DownloadStatus.COMPLETED, 100.0, "", "", None)
            return expected_path

        def progress_callback(progress: DownloadProgress) -> None:
            if status_callback:
                status = DownloadStatus.DOWNLOADING
                if progress.status == "finished":
                    status = DownloadStatus.CONVERTING
                status_callback(
                    item_id, status,
                    progress.progress, progress.speed, progress.eta, None,
                )

        try:
            if status_callback:
                status_callback(item_id, DownloadStatus.DOWNLOADING, 0.0, "", "", None)

            output_path = await self._downloader.download(
                item.result.url, meta, output_dir, progress_callback,
            )

            # Create skip file if enabled
            if self._settings.create_skip_file:
                try:
                    output_path.with_suffix(output_path.suffix + ".skip").touch()
                except OSError:
                    pass

            # Embed metadata
            if status_callback:
                status_callback(item_id, DownloadStatus.EMBEDDING, 100.0, "", "", None)

            await self._downloader.embed_metadata(output_path, meta)

            # Embed lyrics if available
            if item.song.lyrics:
                await self._downloader.embed_lyrics(output_path, item.song.lyrics)

            # Generate LRC file if enabled
            if self._settings.generate_lrc:
                generate_lrc(
                    item.song.name, list(item.song.artists),
                    output_path, item.song.lyrics,
                )

            # Add to archive
            self._archive.add(item.song.url)

            # Track as known song
            self._known_songs.setdefault(item.song.url, []).append(output_path)

            if status_callback:
                status_callback(item_id, DownloadStatus.COMPLETED, 100.0, "", "", None)

            return output_path

        except DownloadError as e:
            logger.error("Download failed for %s: %s", item.song.display_name, e)
            self._log_error(item.song, e)

            if self._settings.add_unavailable:
                self._archive.add(item.song.url)

            if status_callback:
                status_callback(item_id, DownloadStatus.FAILED, 0.0, "", "", str(e))
            return None

        except Exception as e:
            logger.error("Unexpected error downloading %s: %s", item.song.display_name, e)
            self._log_error(item.song, e)

            if self._settings.add_unavailable:
                self._archive.add(item.song.url)

            if status_callback:
                status_callback(
                    item_id, DownloadStatus.FAILED, 0.0, "", "",
                    f"Unexpected error: {e}",
                )
            return None

    def _log_error(self, song: Song, error: Exception) -> None:
        """Log download errors to file if configured."""
        if self._settings.print_errors:
            traceback.print_exc()

        if self._settings.save_errors:
            try:
                error_path = Path(self._settings.save_errors)
                error_path.parent.mkdir(parents=True, exist_ok=True)
                with open(error_path, "a", encoding="utf-8") as f:
                    f.write(f"{song.display_name} | {song.url} | {error}\n")
                    if self._settings.print_errors:
                        f.write(traceback.format_exc())
                        f.write("\n")
            except OSError:
                pass
