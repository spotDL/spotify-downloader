"""
Module related to managing reading and writing to the config file.

Default config - spotdl.utils.config.DEFAULT_CONFIG
"""

import json
import os
import platform
from argparse import Namespace
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import platformdirs

from spotdl.types.options import (
    DownloaderOptions,
    SpotDLOptions,
    SpotifyOptions,
    WebOptions,
)

__all__ = [
    "ConfigError",
    "get_spotdl_path",
    "get_config_file",
    "get_cache_path",
    "get_temp_path",
    "get_errors_path",
    "get_config",
    "create_settings_type",
    "create_settings",
    "SPOTIFY_OPTIONS",
    "DOWNLOADER_OPTIONS",
    "WEB_OPTIONS",
    "DEFAULT_CONFIG",
]


class ConfigError(Exception):
    """
    Base class for all exceptions related to config.
    """


def get_spotdl_path() -> Path:
    """
    Get the path to the spotdl folder.

    ### Returns
    - The path to the spotdl folder.

    ### Notes
    - If the spotdl directory does not exist, it will be created.
    """

    # Check if os is linux
    if platform.system() == "Linux":
        # if platform is linux, and XDG DATA HOME spotdl folder exists, use it
        user_data_dir = Path(platformdirs.user_data_dir("spotdl", "spotDL"))
        if user_data_dir.exists():
            return user_data_dir

    spotdl_path = Path(os.path.expanduser("~"), ".spotdl")
    if not spotdl_path.exists():
        os.mkdir(spotdl_path)

    return spotdl_path


def get_config_file() -> Path:
    """
    Get config file path

    ### Returns
    - The path to the config file.
    """

    return get_spotdl_path() / "config.json"


def get_cache_path() -> Path:
    """
    Get the path to the cache folder.

    ### Returns
    - The path to the spotipy cache file.
    """

    return get_spotdl_path() / ".spotipy"


def get_spotify_cache_path() -> Path:
    """
    Get the path to the spotify cache folder.

    ### Returns
    - The path to the spotipy cache file.
    """

    return get_spotdl_path() / ".spotify_cache"


def get_temp_path() -> Path:
    """
    Get the path to the temp folder.

    ### Returns
    - The path to the temp folder.
    """

    temp_path = get_spotdl_path() / "temp"
    if not temp_path.exists():
        os.mkdir(temp_path)

    return temp_path


def get_errors_path() -> Path:
    """
    Get the path to the errors folder.

    ### Returns
    - The path to the errors folder.

    ### Notes
    - If the errors directory does not exist, it will be created.
    """

    errors_path = get_spotdl_path() / "errors"

    if not errors_path.exists():
        os.mkdir(errors_path)

    return errors_path


def get_config() -> Dict[str, Any]:
    """
    Get the config.

    ### Returns
    - The dictionary with the config.

    ### Errors
    - ConfigError: If the config file does not exist.
    """

    config_path = get_config_file()

    if not config_path.exists():
        raise ConfigError(
            "Config file not found."
            "Please run `spotdl --generate-config` to create a config file."
        )

    with open(config_path, "r", encoding="utf-8") as config_file:
        return json.load(config_file)


def create_settings_type(
    arguments: Namespace,
    config: Dict[str, Any],
    default: Union[SpotifyOptions, DownloaderOptions, WebOptions],
) -> Dict[str, Any]:
    """
    Create settings dict
    Argument value has always the priority, then the config file
    value, and if neither are set, use default value

    ### Arguments
    - arguments: Namespace from argparse
    - default: dict

    ### Returns
    - settings: dict
    """

    settings = {}
    for key, default_value in default.items():
        argument_val = arguments.__dict__.get(key)
        config_val = config.get(key)

        if argument_val is not None:
            settings[key] = argument_val
        elif config_val is not None:
            settings[key] = config_val
        else:
            settings[key] = default_value

    return settings


def create_settings(
    arguments: Namespace,
) -> Tuple[SpotifyOptions, DownloaderOptions, WebOptions]:
    """
    Create settings dicts for Spotify, Downloader and Web
    based on the arguments and config file (if enabled)

    ### Arguments
    - arguments: Namespace from argparse

    ### Returns
    - spotify_options: SpotifyOptions
    - downloader_options: DownloaderOptions
    - web_options: WebOptions
    """

    # Get the config file
    # It will automatically load if the `load_config` is set to True
    # in the config file
    config = {}
    if arguments.config or (
        get_config_file().exists() and get_config().get("load_config")
    ):
        config = get_config()

    # Type: ignore because of the issues below
    # https://github.com/python/mypy/issues/8890
    # https://github.com/python/mypy/issues/5382
    spotify_options = SpotifyOptions(
        **create_settings_type(arguments, config, SPOTIFY_OPTIONS)  # type: ignore
    )
    downloader_options = DownloaderOptions(
        **create_settings_type(arguments, config, DOWNLOADER_OPTIONS)  # type: ignore
    )
    web_options = WebOptions(**create_settings_type(arguments, config, WEB_OPTIONS))  # type: ignore

    return spotify_options, downloader_options, web_options


SPOTIFY_OPTIONS: SpotifyOptions = {
    "client_id": "5f573c9620494bae87890c0f08a60293",
    "client_secret": "212476d9b0f3472eaa762d90b19b0ba8",
    "auth_token": None,
    "user_auth": False,
    "headless": False,
    "cache_path": str(get_cache_path()),
    "no_cache": False,
    "max_retries": 3,
    "use_cache_file": False,
}

DOWNLOADER_OPTIONS: DownloaderOptions = {
    "audio_providers": ["youtube-music"],
    "lyrics_providers": ["genius", "azlyrics", "musixmatch"],
    "playlist_numbering": False,
    "scan_for_songs": False,
    "m3u": None,
    "output": "{artists} - {title}.{output-ext}",
    "overwrite": "skip",
    "search_query": None,
    "ffmpeg": "ffmpeg",
    "bitrate": None,
    "ffmpeg_args": None,
    "format": "mp3",
    "save_file": None,
    "filter_results": True,
    "threads": 4,
    "cookie_file": None,
    "restrict": False,
    "print_errors": False,
    "sponsor_block": False,
    "preload": False,
    "archive": None,
    "load_config": True,
    "log_level": "INFO",
    "simple_tui": False,
    "fetch_albums": False,
    "id3_separator": "/",
    "ytm_data": False,
    "add_unavailable": False,
    "generate_lrc": False,
    "force_update_metadata": False,
    "only_verified_results": False,
    "sync_without_deleting": False,
    "max_filename_length": None,
}

WEB_OPTIONS: WebOptions = {
    "web_use_output_dir": False,
    "port": 8800,
    "host": "localhost",
    "keep_alive": False,
    "allowed_origins": None,
    "keep_sessions": False,
}

# Type: ignore because of the issues above
DEFAULT_CONFIG: SpotDLOptions = {
    **SPOTIFY_OPTIONS,  # type: ignore
    **DOWNLOADER_OPTIONS,  # type: ignore
    **WEB_OPTIONS,  # type: ignore
}
