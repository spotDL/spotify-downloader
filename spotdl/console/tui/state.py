import threading
from typing import Any, Dict, Optional, cast

from spotdl.console.tui.settings import (
    build_downloader_settings,
    build_spotify_settings,
)
from spotdl.download.downloader import Downloader
from spotdl.types.options import DownloaderOptions
from spotdl.utils.spotify import SpotifyClient

RUNTIME_SETTINGS_KEYS = {
    "m3u",
    "save_file",
    "archive",
    "fetch_albums",
    "output",
    "format",
    "bitrate",
    "overwrite",
    "preload",
    "restrict",
    "add_unavailable",
    "max_filename_length",
    "id3_separator",
    "generate_lrc",
    "playlist_numbering",
    "playlist_retain_track_cover",
    "ytm_data",
    "force_update_metadata",
    "skip_album_art",
    "ignore_albums",
    "skip_explicit",
    "create_skip_file",
    "respect_skip_file",
    "print_errors",
    "save_errors",
    "log_level",
    "log_format",
    "search_query",
    "filter_results",
    "only_verified_results",
    "album_type",
    "cookie_file",
    "sponsor_block",
    "proxy",
    "yt_dlp_args",
    "genius_token",
    "user_auth",
    "client_id",
    "client_secret",
}

STRUCTURAL_SETTINGS_KEYS = {
    "threads",
    "audio_providers",
    "lyrics_providers",
    "ffmpeg",
    "detect_formats",
    "scan_for_songs",
    "simple_tui",
}


class AppState:
    def __init__(self) -> None:
        self.downloader: Optional[Downloader] = None
        self.spotify_lock = threading.Lock()
        self.downloader_lock = threading.Lock()

    def ensure_spotify(self, user_auth: bool = False) -> None:
        with self.spotify_lock:
            if SpotifyClient._instance is None:
                SpotifyClient.init(**build_spotify_settings(user_auth))

    def ensure_downloader(self, options: Dict[str, Any]) -> Downloader:
        with self.downloader_lock:
            new_settings = build_downloader_settings(options)
            if self.downloader is None:
                self.downloader = Downloader(cast(DownloaderOptions, new_settings))
            else:
                structural_changed = any(
                    self.downloader.settings.get(key) != new_settings.get(key)
                    for key in STRUCTURAL_SETTINGS_KEYS
                )
                if structural_changed:
                    self.downloader = Downloader(cast(DownloaderOptions, new_settings))
                else:
                    settings = cast(Any, self.downloader.settings)
                    for key in RUNTIME_SETTINGS_KEYS:
                        if key in new_settings and new_settings[key] is not None:
                            settings[key] = new_settings[key]
            return self.downloader
