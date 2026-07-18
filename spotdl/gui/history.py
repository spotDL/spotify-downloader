"""
Persistent download history for the spotDL GUI.

Stored as JSON next to spotDL's config, so it survives between runs (and, in the
Flatpak, lives under the persisted ``~/.config/spotdl`` directory).
"""

import json
import logging
import time
from typing import Any, Dict, List

from spotdl.utils.config import get_spotdl_path

__all__ = ["load_history", "add_entry", "clear_history", "history_file"]

logger = logging.getLogger(__name__)

# Keep the history bounded so the file cannot grow without limit.
_MAX_ENTRIES = 500


def history_file() -> Any:
    """Return the path to the history JSON file."""

    return get_spotdl_path() / "gui_history.json"


def load_history() -> List[Dict[str, Any]]:
    """Return the stored history, newest first."""

    path = history_file()
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read history file: %s", exc)

    return []


def _write(entries: List[Dict[str, Any]]) -> None:
    path = history_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(entries[:_MAX_ENTRIES], handle, indent=2)
    except OSError as exc:
        logger.error("Could not write history file: %s", exc)


def add_entry(
    name: str, path: str, artist: str = "", album: str = ""
) -> Dict[str, Any]:
    """
    Prepend a downloaded song to the history and persist it.

    ### Returns
    - The entry that was stored.
    """

    entry = {
        "name": name,
        "path": path,
        "artist": artist,
        "album": album,
        "timestamp": time.time(),
    }

    entries = load_history()
    entries.insert(0, entry)
    _write(entries)
    return entry


def clear_history() -> None:
    """Remove all stored history."""

    _write([])
