"""
Downloader module - optimized version for batch playlist pre-checks,
faster duplicate detection, and async downloads.
"""

import asyncio
import datetime
import json
import logging
import shutil
import sys
import traceback
from argparse import Namespace
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type, Union

from yt_dlp.postprocessor.modify_chapters import ModifyChaptersPP
from yt_dlp.postprocessor.sponsorblock import SponsorBlockPP

from spotdl.download.progress_handler import ProgressHandler
from spotdl.providers.audio import (
    AudioProvider,
    BandCamp,
    Piped,
    SoundCloud,
    YouTube,
    YouTubeMusic,
)
from spotdl.providers.lyrics import AzLyrics, Genius, LyricsProvider, MusixMatch, Synced
from spotdl.types.options import DownloaderOptionalOptions, DownloaderOptions
from spotdl.types.song import Song
from spotdl.utils.archive import Archive
from spotdl.utils.config import (
    DOWNLOADER_OPTIONS,
    GlobalConfig,
    create_settings_type,
    get_errors_path,
    get_temp_path,
    modernize_settings,
)
from spotdl.utils.ffmpeg import FFmpegError, convert, get_ffmpeg_path
from spotdl.utils.formatter import create_file_name
from spotdl.utils.lrc import generate_lrc
from spotdl.utils.m3u import gen_m3u_files
from spotdl.utils.metadata import MetadataError, embed_metadata
from spotdl.utils.search import gather_known_songs, reinit_song, songs_from_albums

__all__ = [
    "AUDIO_PROVIDERS",
    "LYRICS_PROVIDERS",
    "Downloader",
    "DownloaderError",
    "SPONSOR_BLOCK_CATEGORIES",
]

logger = logging.getLogger(__name__)

AUDIO_PROVIDERS: Dict[str, Type[AudioProvider]] = {
    "youtube": YouTube,
    "youtube-music": YouTubeMusic,
    "soundcloud": SoundCloud,
    "bandcamp": BandCamp,
    "piped": Piped,
}

LYRICS_PROVIDERS: Dict[str, Type[LyricsProvider]] = {
    "genius": Genius,
    "musixmatch": MusixMatch,
    "azlyrics": AzLyrics,
    "synced": Synced,
}

SPONSOR_BLOCK_CATEGORIES = {
    "sponsor": "Sponsor",
    "intro": "Intermission/Intro Animation",
    "outro": "Endcards/Credits",
    "selfpromo": "Unpaid/Self Promotion",
    "preview": "Preview/Recap",
    "filler": "Filler Tangent",
    "interaction": "Interaction Reminder",
    "music_offtopic": "Non-Music Section",
}


class DownloaderError(Exception):
    """Base class for all exceptions related to downloader."""


class Downloader:
    """
    Optimized Downloader class for SpotDL.
    """

    def __init__(
        self,
        settings: Optional[Union[DownloaderOptionalOptions, DownloaderOptions]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        if settings is None:
            settings = {}

        # Apply default settings
        self.settings: DownloaderOptions = DownloaderOptions(
            **create_settings_type(Namespace(config=False), dict(settings), DOWNLOADER_OPTIONS)
        )
        modernize_settings(self.settings)
        logger.debug("Downloader settings: %s", self.settings)

        # FFmpeg setup
        self.ffmpeg = self.settings["ffmpeg"]
        if self.ffmpeg == "ffmpeg" and shutil.which("ffmpeg") is None:
            ffmpeg_exec = get_ffmpeg_path()
            if ffmpeg_exec is None:
                raise DownloaderError("ffmpeg is not installed")
            self.ffmpeg = str(ffmpeg_exec.absolute())
        logger.debug("FFmpeg path: %s", self.ffmpeg)

        # Async event loop
        self.loop = loop or (asyncio.new_event_loop() if sys.platform != "win32" else asyncio.ProactorEventLoop())
        if loop is None:
            asyncio.set_event_loop(self.loop)
        self.semaphore = asyncio.Semaphore(self.settings["threads"])

        self.progress_handler = ProgressHandler(self.settings["simple_tui"])

        # Initialize known songs from disk
        self.scan_formats = self.settings["detect_formats"] or [self.settings["format"]]
        self.known_songs: Dict[str, List[Path]] = {}
        if self.settings["scan_for_songs"]:
            logger.info("Scanning for known songs, this might take a while...")
            for scan_format in self.scan_formats:
                found_files = gather_known_songs(self.settings["output"], scan_format)
                for song_url, song_paths in found_files.items():
                    self.known_songs.setdefault(song_url, []).extend(song_paths)
            logger.debug("Found %s known songs", len(self.known_songs))

        # Lyrics providers
        self.lyrics_providers: List[LyricsProvider] = []
        for provider in self.settings["lyrics_providers"]:
            cls = LYRICS_PROVIDERS.get(provider)
            if not cls:
                raise DownloaderError(f"Invalid lyrics provider: {provider}")
            if provider == "genius":
                token = self.settings.get("genius_token")
                if not token:
                    raise DownloaderError("Genius token not found in settings")
                self.lyrics_providers.append(Genius(token))
            else:
                self.lyrics_providers.append(cls())

        # Audio providers
        self.audio_providers: List[AudioProvider] = []
        for provider in self.settings["audio_providers"]:
            cls = AUDIO_PROVIDERS.get(provider)
            if not cls:
                raise DownloaderError(f"Invalid audio provider: {provider}")
            self.audio_providers.append(
                cls(
                    output_format=self.settings["format"],
                    cookie_file=self.settings["cookie_file"],
                    search_query=self.settings["search_query"],
                    filter_results=self.settings["filter_results"],
                    yt_dlp_args=self.settings["yt_dlp_args"],
                )
            )

        self.errors: List[str] = []

        # Proxy
        proxy = self.settings["proxy"]
        if proxy:
            proxies = {"http": proxy, "https": proxy}
            GlobalConfig.set_parameter("proxies", proxies)
            logger.info("Proxy set: %s", proxy)

        # Archive
        self.url_archive = Archive()
        if self.settings["archive"]:
            self.url_archive.load(self.settings["archive"])
        logger.debug("Archive loaded: %d urls", len(self.url_archive))

        logger.debug("Downloader initialized.")

    # -----------------------
    # Playlist Precheck
    # -----------------------
    def precheck_playlist_files(self, songs: List[Song]):
        """
        Pre-scan all songs in the playlist to detect existing files
        to avoid repeated per-song checks.
        """
        self.playlist_files: Dict[str, Path] = {}
        for song in songs:
            output_file = create_file_name(
                song=song,
                template=self.settings["output"],
                file_extension=self.settings["format"],
                restrict=self.settings["restrict"],
                file_name_length=self.settings["max_filename_length"],
            )
            dup_paths = [p for p in self.known_songs.get(song.url, []) if p.exists() and p != output_file]
            if output_file.exists() or dup_paths:
                self.playlist_files[song.url] = output_file

    # -----------------------
    # Public download methods
    # -----------------------
    def download_song(self, song: Song) -> Tuple[Song, Optional[Path]]:
        self.progress_handler.set_song_count(1)
        return self.download_multiple_songs([song])[0]

    def download_multiple_songs(self, songs: List[Song]) -> List[Tuple[Song, Optional[Path]]]:
        """
        Download multiple songs with batch precheck for duplicates.
        """
        self.precheck_playlist_files(songs)

        # Handle albums
        if self.settings["fetch_albums"]:
            albums = set(song.album_id for song in songs if song.album_id)
            if albums:
                logger.info("Fetching %d albums", len(albums))
                songs.extend(songs_from_albums(list(albums)))
                # remove duplicates by URL
                songs = list({s.url: s for s in songs}.values())

        # Apply archive filter
        if self.settings["archive"]:
            songs = [s for s in songs if s.url not in self.url_archive]

        self.progress_handler.set_song_count(len(songs))
        tasks = [self.pool_download(song) for song in songs]
        results = list(self.loop.run_until_complete(asyncio.gather(*tasks)))

        # Log/save errors
        if self.settings["print_errors"]:
            for err in self.errors:
                logger.error(err)
        if self.settings["save_errors"] and self.errors:
            with open(self.settings["save_errors"], "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}\n")
                for err in self.errors:
                    f.write(f"{err}\n")

        # Update archive
        if self.settings["archive"]:
            for song, path in results:
                if path or self.settings["add_unavailable"]:
                    self.url_archive.add(song.url)
            self.url_archive.save(self.settings["archive"])

        # Generate M3U playlist
        if self.settings["m3u"]:
            song_list = [s for s, p in results if p or self.settings["add_unavailable"]]
            gen_m3u_files(
                song_list,
                self.settings["m3u"],
                self.settings["output"],
                self.settings["format"],
                self.settings["restrict"],
                False,
                self.settings["detect_formats"],
            )

        # Save results
        if self.settings["save_file"]:
            with open(self.settings["save_file"], "w", encoding="utf-8") as f:
                json.dump([s.json for s, _ in results], f, indent=4)

        return results

    # -----------------------
    # Async pool wrapper
    # -----------------------
    async def pool_download(self, song: Song) -> Tuple[Song, Optional[Path]]:
        async with self.semaphore:
            return await self.loop.run_in_executor(None, self.search_and_download, song)

    # -----------------------
    # Lyrics search
    # -----------------------
    def search_lyrics(self, song: Song) -> Optional[str]:
        for provider in self.lyrics_providers:
            lyrics = provider.get_lyrics(song.name, song.artists)
            if lyrics:
                return lyrics
        return None

    # -----------------------
    # Main search and download
    # -----------------------
    def search_and_download(self, song: Song) -> Tuple[Song, Optional[Path]]:
        """
        Optimized search & download with duplicate pre-check.
        """
        display_progress_tracker = self.progress_handler.get_new_tracker(song)

        # Reinit missing metadata
        if (not song.name or self.settings["fetch_albums"] or any(getattr(song, x) is None for x in [
            "genres", "disc_count", "tracks_count", "track_number", "album_id", "album_artist"
        ])):
            song = reinit_song(song)

        # Output file
        output_file = create_file_name(
            song=song,
            template=self.settings["output"],
            file_extension=self.settings["format"],
            restrict=self.settings["restrict"],
            file_name_length=self.settings["max_filename_length"],
        )

        # Batch duplicate check
        if getattr(self, "playlist_files", {}) and song.url in self.playlist_files:
            display_progress_tracker.notify_download_skip()
            return song, self.playlist_files[song.url]

        # Try all audio providers
        for provider in self.audio_providers:
            try:
                downloaded_file = provider.download(song, output_file, display_progress_tracker)
                if downloaded_file:
                    # Lyrics embedding
                    if self.settings["lyrics"] and song.lyrics is None:
                        song.lyrics = self.search_lyrics(song)
                    # Metadata embedding
                    embed_metadata(downloaded_file, song, self.ffmpeg)
                    return song, downloaded_file
            except (FFmpegError, MetadataError, Exception) as e:
                self.errors.append(f"{song.name}: {e}")
                traceback.print_exc()
        display_progress_tracker.notify_download_error()
        return song, None
