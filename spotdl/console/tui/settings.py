import os
from typing import Any, Dict

from spotdl.console.tui.constants import DOWNLOADER_OPTIONS_DEFAULTS
from spotdl.utils.config import SPOTIFY_OPTIONS


def format_duration(seconds: float) -> str:
    total = int(seconds or 0)
    minutes, secs = divmod(total, 60)
    return f"{minutes}:{secs:02d}"


def build_spotify_settings(user_auth: bool = False) -> Dict[str, Any]:
    settings = dict(SPOTIFY_OPTIONS)
    if os.environ.get("SPOTIPY_CLIENT_ID"):
        settings["client_id"] = os.environ["SPOTIPY_CLIENT_ID"]
    if os.environ.get("SPOTIPY_CLIENT_SECRET"):
        settings["client_secret"] = os.environ["SPOTIPY_CLIENT_SECRET"]
    settings["user_auth"] = user_auth
    settings["headless"] = True
    return settings


def build_downloader_settings(options: Dict[str, Any]) -> Dict[str, Any]:
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

    settings["output"] = settings["output"]
    return settings
