from pathlib import Path
from typing import Any, Dict

import os
import json


class ConfigError(Exception):
    """
    Base class for all exceptions related to config.
    """


def get_spotdl_path() -> Path:
    """
    Returns the path to the spotdl folder.
    If the spotdl directory does not exist, it will be created.
    """
    spotdl_path = Path(os.path.expanduser("~"), ".spotdl")
    if not spotdl_path.exists():
        os.mkdir(spotdl_path)

    return spotdl_path


def get_config_file() -> Path:
    """
    Returns the path to the config file.
    """
    return get_spotdl_path() / "config.json"


def get_cache_path() -> Path:
    """
    Returns the path to the spotipy cache file
    """
    return get_spotdl_path() / ".spotipy"


def get_temp_path() -> Path:
    """
    Returns the path to the spotdl temp folder.
    """
    temp_path = get_spotdl_path() / "temp"
    if not temp_path.exists():
        os.mkdir(temp_path)

    return temp_path


def get_errors_path() -> Path:
    """
    Returns the path to the spotdl errors folder.
    """
    errors_path = get_spotdl_path() / "errors"

    if not errors_path.exists():
        os.mkdir(errors_path)

    return errors_path


def get_config() -> Dict[str, Any]:
    """
    Returns the config object.
    """

    config_path = get_config_file()

    if not config_path.exists():
        raise ConfigError(
            "Config file not found."
            "Please run `spotdl --generate-config` to create a config file."
        )

    with open(config_path, "r", encoding="utf-8") as config_file:
        return json.load(config_file)


DEFAULT_CONFIG = {
    "log_level": "INFO",
    "simple_tui": False,
    "cache_path": str(get_cache_path()),
    "audio_provider": "youtube-music",
    "lyrics_provider": "musixmatch",
    "ffmpeg": "ffmpeg",
    "variable_bitrate": None,
    "constant_bitrate": None,
    "ffmpeg_args": None,
    "format": "mp3",
    "save_file": None,
    "m3u": None,
    "output": "{artists} - {title}.{output-ext}",
    "overwrite": "skip",
    "client_id": "5f573c9620494bae87890c0f08a60293",
    "client_secret": "212476d9b0f3472eaa762d90b19b0ba8",
    "user_auth": False,
    "search_query": "{artists} - {title}",
    "threads": 4,
    "no_cache": False,
    "cookie_file": None,
    "headless": False,
}
