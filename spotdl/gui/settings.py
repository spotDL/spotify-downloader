"""
Persistence for the spotDL GUI.

Settings are stored in spotDL's own ``config.json`` (see
``spotdl.utils.config``) using the same keys the CLI understands, so the GUI
and the command line share a single configuration. A couple of GUI-only keys
(``output_dir`` and ``folder_structure``) are also stored there; the CLI simply
ignores keys it does not recognise.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from spotdl.utils.config import DOWNLOADER_OPTIONS, get_config_file

__all__ = [
    "FORMATS",
    "BITRATES",
    "FOLDER_STRUCTURES",
    "DEFAULT_STRUCTURE",
    "default_output_dir",
    "load_settings",
    "save_settings",
    "build_downloader_settings",
]

logger = logging.getLogger(__name__)

FORMATS = ["mp3", "flac", "opus", "m4a", "ogg", "wav"]
BITRATES = ["auto", "128k", "192k", "256k", "320k", "disable"]

# Folder-organisation presets. The value is the path template that is appended
# to the chosen output directory. Keeping songs grouped avoids one giant folder.
FOLDER_STRUCTURES: Dict[str, str] = {
    "album-artist": "{album-artist}/{album}/{artists} - {title}.{output-ext}",
    "artist": "{artist}/{album}/{artists} - {title}.{output-ext}",
    "playlist": "{list-name}/{artists} - {title}.{output-ext}",
    "flat": "{artists} - {title}.{output-ext}",
}

# Human-readable labels, in display order.
FOLDER_STRUCTURE_LABELS = [
    ("album-artist", "Album artist / Album"),
    ("artist", "Artist / Album"),
    ("playlist", "Playlist or album name"),
    ("flat", "All in one folder"),
]

DEFAULT_STRUCTURE = "album-artist"


def default_output_dir() -> str:
    """Return the default download directory (the user's Music folder)."""

    return str(Path.home() / "Music")


def _read_config() -> Dict[str, Any]:
    """Read the raw config file, returning an empty dict when absent/invalid."""

    path = get_config_file()
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as config_file:
            return json.load(config_file)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read spotDL config file: %s", exc)
        return {}


def _write_config(values: Dict[str, Any]) -> None:
    """Merge ``values`` into the existing config file and write it back."""

    path = get_config_file()
    data = _read_config()
    data.update(values)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as config_file:
            json.dump(data, config_file, indent=4)
    except OSError as exc:
        logger.error("Could not save spotDL config file: %s", exc)


def _output_template(output_dir: str, structure: str) -> str:
    """Join the base output directory with the folder-structure template."""

    template = FOLDER_STRUCTURES.get(structure, FOLDER_STRUCTURES[DEFAULT_STRUCTURE])
    return str(Path(output_dir) / template)


def load_settings() -> Dict[str, Any]:
    """
    Load GUI-friendly settings, derived from the shared config file.

    ### Returns
    - A dict with ``output_dir``, ``folder_structure``, ``format``,
      ``bitrate``, ``threads`` and ``generate_lrc`` keys.
    """

    config = _read_config()

    output_dir = config.get("output_dir") or default_output_dir()

    structure = config.get("folder_structure", DEFAULT_STRUCTURE)
    if structure not in FOLDER_STRUCTURES:
        structure = DEFAULT_STRUCTURE

    fmt = config.get("format", DOWNLOADER_OPTIONS["format"])
    if fmt not in FORMATS:
        fmt = DOWNLOADER_OPTIONS["format"]

    bitrate = config.get("bitrate", DOWNLOADER_OPTIONS["bitrate"])
    if bitrate not in BITRATES:
        bitrate = "auto"

    return {
        "output_dir": output_dir,
        "folder_structure": structure,
        "format": fmt,
        "bitrate": bitrate,
        "threads": int(config.get("threads", DOWNLOADER_OPTIONS["threads"])),
        "generate_lrc": bool(
            config.get("generate_lrc", DOWNLOADER_OPTIONS["generate_lrc"])
        ),
        # GUI-only: retry failed songs from alternative sources.
        "fallback": bool(config.get("gui_fallback", True)),
    }


def save_settings(values: Dict[str, Any]) -> None:
    """
    Persist GUI settings back to the shared config file using CLI-compatible
    keys (plus the GUI-only ``output_dir``/``folder_structure`` helpers).

    ### Arguments
    - values: A dict as returned by :func:`load_settings`.
    """

    output_dir = values.get("output_dir") or default_output_dir()
    structure = values.get("folder_structure", DEFAULT_STRUCTURE)

    _write_config(
        {
            "output_dir": output_dir,
            "folder_structure": structure,
            "output": _output_template(output_dir, structure),
            "format": values.get("format", DOWNLOADER_OPTIONS["format"]),
            "bitrate": values.get("bitrate", DOWNLOADER_OPTIONS["bitrate"]),
            "threads": int(values.get("threads", DOWNLOADER_OPTIONS["threads"])),
            "generate_lrc": bool(
                values.get("generate_lrc", DOWNLOADER_OPTIONS["generate_lrc"])
            ),
            "gui_fallback": bool(values.get("fallback", True)),
        }
    )


def build_downloader_settings(values: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert GUI settings into a ``DownloaderOptions``-compatible dict.

    ### Arguments
    - values: A dict as returned by :func:`load_settings`.

    ### Returns
    - A dict suitable for passing to ``Downloader(settings=...)``.
    """

    output_dir = values.get("output_dir") or default_output_dir()
    structure = values.get("folder_structure", DEFAULT_STRUCTURE)

    return {
        "output": _output_template(output_dir, structure),
        "format": values.get("format", DOWNLOADER_OPTIONS["format"]),
        "bitrate": values.get("bitrate", DOWNLOADER_OPTIONS["bitrate"]),
        "threads": int(values.get("threads", DOWNLOADER_OPTIONS["threads"])),
        "generate_lrc": bool(
            values.get("generate_lrc", DOWNLOADER_OPTIONS["generate_lrc"])
        ),
        # Never render the Rich terminal UI from within the GUI.
        "simple_tui": True,
    }
