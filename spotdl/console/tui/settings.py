"""
Build spotDL settings from the options chosen in the TUI.
"""

import os
from typing import Any, Dict

from spotdl.console.tui.constants import DOWNLOADER_OPTIONS_DEFAULTS
from spotdl.utils.config import SPOTIFY_OPTIONS


def format_duration(seconds: float) -> str:
    """
    Format a duration as minutes and seconds.

    ### Arguments
    - seconds: Duration in seconds.

    ### Returns
    - Text such as "3:07".
    """

    total = int(seconds or 0)
    minutes, secs = divmod(total, 60)
    return f"{minutes}:{secs:02d}"


def build_spotify_settings(user_auth: bool = False) -> Dict[str, Any]:
    """
    Build the Spotify client settings.

    ### Arguments
    - user_auth: Whether to log in with the user account.

    ### Returns
    - The default settings with the credentials found in the environment.
    """

    settings = dict(SPOTIFY_OPTIONS)
    if os.environ.get("SPOTIPY_CLIENT_ID"):
        settings["client_id"] = os.environ["SPOTIPY_CLIENT_ID"]
    if os.environ.get("SPOTIPY_CLIENT_SECRET"):
        settings["client_secret"] = os.environ["SPOTIPY_CLIENT_SECRET"]
    settings["user_auth"] = user_auth
    settings["headless"] = True
    return settings


def build_downloader_settings(options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the downloader settings from the TUI options.

    ### Arguments
    - options: Options chosen in the TUI.

    ### Returns
    - The TUI defaults updated with every option that is set.
    """

    settings = dict(DOWNLOADER_OPTIONS_DEFAULTS)
    output_dir = options.get("output_dir")
    if output_dir:
        settings["output"] = os.path.join(
            str(output_dir),
            options.get("output_template", "{artists} - {title}.{output-ext}"),
        )
    else:
        settings["output"] = options.get(
            "output_template", "{artists} - {title}.{output-ext}"
        )

    for key, value in options.items():
        if key in settings and value is not None:
            settings[key] = value

    return settings
