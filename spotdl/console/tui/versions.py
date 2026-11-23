"""
Helpers to compare the installed version with the latest release.
"""

import json
import logging
import re
import time
from typing import List, Optional, Tuple

import requests

from spotdl.utils.config import get_spotdl_path

logger = logging.getLogger(__name__)

UPSTREAM_RELEASES_URL = (
    "https://api.github.com/repos/spotDL/spotify-downloader/releases/latest"
)
_UPSTREAM_CACHE_FILE = get_spotdl_path() / "tui_upstream_version_cache.json"
_UPSTREAM_CACHE_TTL = 86400


def parse_version(value: str) -> Tuple[int, ...]:
    """
    Turn a version string into a tuple that can be compared.

    ### Arguments
    - value: Version such as "4.5.2" or "4.5.2-beta".

    ### Returns
    - The leading numeric parts, `(0,)` when there are none.
    """

    numbers: List[int] = []
    for part in re.split(r"[.\-]", value):
        if re.match(r"^\d+$", part):
            numbers.append(int(part))
        else:
            break
    return tuple(numbers) or (0,)


def fetch_upstream_latest_version() -> Optional[str]:
    """
    Get the latest released version from GitHub.

    ### Returns
    - The version without the "v" prefix, or None if it could not be fetched.
    """

    try:
        response = requests.get(UPSTREAM_RELEASES_URL, timeout=5)
        response.raise_for_status()
        tag = response.json().get("tag_name", "")
    except (requests.RequestException, ValueError) as exc:
        logger.debug("Could not fetch the latest release: %s", exc)
        return None
    return tag.lstrip("v") or None


def get_cached_upstream_latest_version() -> Optional[str]:
    """
    Get the latest released version stored during the last day.

    ### Returns
    - The cached version, or None if there is no recent value.
    """

    try:
        with open(_UPSTREAM_CACHE_FILE, "r", encoding="utf-8") as cache_file:
            data = json.load(cache_file)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    if time.time() - data.get("time", 0) < _UPSTREAM_CACHE_TTL:
        return data.get("version")
    return None


def set_cached_upstream_latest_version(version: str) -> None:
    """
    Store the latest released version with the current time.

    ### Arguments
    - version: Version to store.
    """

    try:
        _UPSTREAM_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_UPSTREAM_CACHE_FILE, "w", encoding="utf-8") as cache_file:
            json.dump({"version": version, "time": time.time()}, cache_file)
    except OSError as exc:
        logger.debug("Could not cache the latest release: %s", exc)
