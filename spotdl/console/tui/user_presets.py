"""
User-customizable presets management and persistence for the TUI.
"""

import json
import logging
from typing import Any, Dict

from spotdl.utils.config import get_spotdl_path

logger = logging.getLogger(__name__)

PRESETS_FILE = get_spotdl_path() / "tui_presets.json"

DEFAULT_PRESETS: Dict[str, Dict[str, Any]] = {
    "light": {
        "format": "opus",
        "bitrate": "96k",
        "threads": "8",
        "dont_filter_results": False,
        "only_verified_results": False,
        "preload": True,
        "generate_lrc": False,
        "sponsor_block": False,
    },
    "efficient": {
        "format": "mp3",
        "bitrate": "auto",
        "threads": "8",
        "dont_filter_results": False,
        "only_verified_results": False,
        "preload": True,
        "generate_lrc": False,
        "sponsor_block": False,
    },
    "balanced": {
        "format": "mp3",
        "bitrate": "320k",
        "threads": "4",
        "dont_filter_results": False,
        "only_verified_results": False,
        "preload": False,
        "generate_lrc": False,
        "sponsor_block": False,
    },
    "studio": {
        "format": "opus",
        "bitrate": "disable",
        "threads": "2",
        "dont_filter_results": False,
        "only_verified_results": True,
        "preload": False,
        "generate_lrc": False,
        "sponsor_block": False,
    },
}


def load_presets() -> Dict[str, Dict[str, Any]]:
    """
    Load presets from disk, merged with built-in default presets.

    ### Returns
    - Dictionary mapping preset identifiers to their options.
    """

    presets: Dict[str, Dict[str, Any]] = {
        name: dict(vals) for name, vals in DEFAULT_PRESETS.items()
    }

    if not PRESETS_FILE.is_file():
        return presets

    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for name, options in data.items():
                if isinstance(options, dict):
                    if name in presets:
                        presets[name].update(options)
                    else:
                        presets[name] = dict(options)
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Could not read presets file: %s", exc)

    return presets


def save_presets(presets: Dict[str, Dict[str, Any]]) -> None:
    """
    Save the given presets dictionary to disk.

    ### Arguments
    - presets: Presets dictionary to persist.
    """

    try:
        PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.debug("Could not save presets file: %s", exc)


def save_single_preset(name: str, options: Dict[str, Any]) -> None:
    """
    Save or update a single preset.

    ### Arguments
    - name: Preset identifier.
    - options: Preset options dictionary.
    """

    current = load_presets()
    current[name] = dict(options)
    save_presets(current)


def delete_custom_preset(name: str) -> bool:
    """
    Delete a custom preset, or reset a default preset to its factory values.

    ### Arguments
    - name: Preset identifier to delete or reset.

    ### Returns
    - True if deleted or reset, False otherwise.
    """

    current = load_presets()
    if name not in current:
        return False

    if name in DEFAULT_PRESETS:
        current[name] = dict(DEFAULT_PRESETS[name])
    else:
        del current[name]

    save_presets(current)
    return True


def reset_presets_to_default() -> None:
    """
    Reset all presets back to the factory defaults.
    """

    save_presets({name: dict(vals) for name, vals in DEFAULT_PRESETS.items()})
