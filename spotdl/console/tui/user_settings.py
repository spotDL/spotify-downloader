"""
Global user settings management and persistence for the TUI.
"""

import json
import logging
from typing import Any, Dict

from spotdl.utils.config import get_spotdl_path

logger = logging.getLogger(__name__)

SETTINGS_FILE = get_spotdl_path() / "tui_settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "threads": "4",
    "format": "mp3",
    "bitrate": "128k",
    "audio_provider": "youtube-music",
    "fallback_audio_provider": "youtube",
    "lyrics_provider": "genius",
    "output_dir": "",
    "output_template": "{artists} - {title}.{output-ext}",
    "overwrite": "skip",
    "restrict": "none",
    "preload": False,
    "sponsor_block": False,
    "generate_lrc": False,
    "only_verified_results": False,
    "dont_filter_results": False,
    "skip_explicit": False,
    "skip_album_art": False,
    "force_update_metadata": False,
    "m3u": False,
    "playlist_folder": False,
    "playlist_numbering": False,
    "playlist_retain_track_cover": False,
    "fetch_albums": False,
    "ytm_data": False,
    "simple_tui": True,
    "log_level": "INFO",
}


def load_user_settings() -> Dict[str, Any]:
    """
    Load user settings from disk, merged with defaults.

    ### Returns
    - Dictionary with all user settings.
    """

    settings = dict(DEFAULT_SETTINGS)

    if not SETTINGS_FILE.is_file():
        return settings

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            settings.update(data)
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Could not read user settings file: %s", exc)

    return settings


def save_user_settings(settings: Dict[str, Any]) -> None:
    """
    Save the given user settings dictionary to disk.

    ### Arguments
    - settings: Settings dictionary to persist.
    """

    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.debug("Could not save user settings file: %s", exc)


def reset_user_settings() -> None:
    """
    Reset user settings back to the defaults.
    """

    save_user_settings(dict(DEFAULT_SETTINGS))
