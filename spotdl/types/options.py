"""
This file contains types for spotdl/downloader/web modules.
Options types have all the fields marked as required.
Settings types have all the fields marked as optional.
"""

from typing import List, Optional, Union

from typing_extensions import TypedDict

__all__ = [
    "SpotifyOptions",
    "DownloaderOptions",
    "WebOptions",
    "SpotDLOptions",
    "SpotifyOptionalOptions",
    "DownloaderOptionalOptions",
    "WebOptionalOptions",
    "SpotDLOptionalOptions",
]


class SpotifyOptions(TypedDict):
    """
    Options used for initializing the Spotify client.
    """

    client_id: str
    client_secret: str
    auth_token: Optional[str]
    user_auth: bool
    headless: bool
    cache_path: str
    no_cache: bool
    max_retries: int
    use_cache_file: bool


class DownloaderOptions(TypedDict):
    """
    Options used for initializing the Downloader.
    """

    audio_providers: List[str]
    lyrics_providers: List[str]
    genius_token: str
    playlist_numbering: bool
    playlist_retain_track_cover: bool
    scan_for_songs: bool
    m3u: Optional[str]
    output: str
    m3u_output: str
    overwrite: str
    search_query: Optional[str]
    ffmpeg: str
    bitrate: Optional[Union[str, int]]
    ffmpeg_args: Optional[str]
    format: str
    save_file: Optional[str]
    filter_results: bool
    album_type: Optional[str]
    threads: int
    cookie_file: Optional[str]
    restrict: Optional[str]
    print_errors: bool
    sponsor_block: bool
    preload: bool
    archive: Optional[str]
    load_config: bool
    log_level: str
    simple_tui: bool
    fetch_albums: bool
    id3_separator: str
    ytm_data: bool
    add_unavailable: bool
    generate_lrc: bool
    force_update_metadata: bool
    only_verified_results: bool
    sync_without_deleting: bool
    max_filename_length: Optional[int]
    yt_dlp_args: Optional[str]
    detect_formats: Optional[List[str]]
    save_errors: Optional[str]
    ignore_albums: Optional[List[str]]
    proxy: Optional[str]
    skip_explicit: Optional[bool]
    log_format: Optional[str]
    redownload: Optional[bool]
    skip_album_art: Optional[bool]
    create_skip_file: Optional[bool]
    respect_skip_file: Optional[bool]
    sync_remove_lrc: Optional[bool]


class WebOptions(TypedDict):
    """
    Options used for initializing the Web server.
    """

    web_use_output_dir: bool
    port: int
    host: str
    keep_alive: bool
    enable_tls: bool
    key_file: Optional[str]
    cert_file: Optional[str]
    ca_file: Optional[str]
    allowed_origins: Optional[List[str]]
    keep_sessions: bool
    force_update_gui: bool
    web_gui_repo: Optional[str]
    web_gui_location: Optional[str]


class SpotDLOptions(SpotifyOptions, DownloaderOptions, WebOptions):
    """
    Options used for initializing the SpotDL client.
    """


class SpotifyOptionalOptions(TypedDict, total=False):
    """
    Options used for initializing the Spotify client.
    """

    client_id: str
    client_secret: str
    auth_token: Optional[str]
    user_auth: bool
    headless: bool
    cache_path: str
    no_cache: bool
    max_retries: int
    use_cache_file: bool


class DownloaderOptionalOptions(TypedDict, total=False):
    """
    Options used for initializing the Downloader.
    """

    audio_providers: List[str]
    lyrics_providers: List[str]
    genius_token: str
    playlist_numbering: bool
    playlist_retain_track_cover: bool
    scan_for_songs: bool
    m3u: Optional[str]
    output: str
    overwrite: str
    search_query: Optional[str]
    ffmpeg: str
    bitrate: Optional[Union[str, int]]
    ffmpeg_args: Optional[str]
    format: str
    save_file: Optional[str]
    filter_results: bool
    album_type: Optional[str]
    threads: int
    cookie_file: Optional[str]
    restrict: Optional[str]
    print_errors: bool
    sponsor_block: bool
    preload: bool
    archive: Optional[str]
    load_config: bool
    log_level: str
    simple_tui: bool
    fetch_albums: bool
    id3_separator: str
    ytm_data: bool
    add_unavailable: bool
    generate_lrc: bool
    force_update_metadata: bool
    only_verified_results: bool
    sync_without_deleting: bool
    max_filename_length: Optional[int]
    yt_dlp_args: Optional[str]
    detect_formats: Optional[List[str]]
    save_errors: Optional[str]
    proxy: Optional[str]
    skip_explicit: Optional[bool]
    log_format: Optional[str]
    redownload: Optional[bool]
    skip_album_art: Optional[bool]
    create_skip_file: Optional[bool]
    respect_skip_file: Optional[bool]
    sync_remove_lrc: Optional[bool]


class WebOptionalOptions(TypedDict, total=False):
    """
    Options used for initializing the Web server.
    """

    web_use_output_dir: bool
    port: int
    host: str
    keep_alive: bool
    enable_tls: bool
    key_file: Optional[str]
    cert_file: Optional[str]
    ca_file: Optional[str]
    allowed_origins: Optional[str]
    keep_sessions: bool
    force_update_gui: bool
    web_gui_repo: Optional[str]
    web_gui_location: Optional[str]


class SpotDLOptionalOptions(
    SpotifyOptionalOptions, DownloaderOptionalOptions, WebOptionalOptions
):
    """
    Options used for initializing the SpotDL client.
    This type is modified to not require all the fields.
    """
