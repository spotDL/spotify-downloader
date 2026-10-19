"""
Objects shared by every screen of the running interface.
"""

import threading
from typing import Any, Dict, Optional, cast

from spotdl.console.tui.settings import (
    build_downloader_settings,
    build_spotify_settings,
)
from spotdl.download.downloader import Downloader
from spotdl.types.options import DownloaderOptions
from spotdl.utils.spotify import SpotifyClient, SpotifyError

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
    """
    Holds the downloader and makes sure the Spotify client exists.

    ### Attributes
    - downloader: Downloader reused between operations, if created.
    """

    def __init__(self) -> None:
        self.downloader: Optional[Downloader] = None
        self.spotify_lock = threading.Lock()
        self.downloader_lock = threading.Lock()

    def ensure_spotify(self, user_auth: bool = False) -> None:
        """
        Create the Spotify client if it was not created yet.

        ### Arguments
        - user_auth: Whether to log in with the user account.
        """

        with self.spotify_lock:
            try:
                SpotifyClient()
            except SpotifyError:
                SpotifyClient.init(**build_spotify_settings(user_auth))

    def ensure_downloader(self, options: Dict[str, Any]) -> Downloader:
        """
        Get a downloader configured with `options`.

        The current downloader is reused when only runtime settings changed,
        and created again when a structural setting changed.

        ### Arguments
        - options: Options chosen in the interface.

        ### Returns
        - The downloader to use.
        """

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
