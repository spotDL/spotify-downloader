import json
import re
import time
from typing import List, Optional, Tuple

import requests

from spotdl.utils.config import get_spotdl_path

UPSTREAM_RELEASES_URL = (
    "https://api.github.com/repos/spotDL/spotify-downloader/releases/latest"
)
_UPSTREAM_CACHE_FILE = get_spotdl_path() / "tui_upstream_version_cache.json"
_UPSTREAM_CACHE_TTL = 86400


def parse_version(value: str) -> Tuple[int, ...]:
    numbers: List[int] = []
    for part in re.split(r"[.\-]", value):
        if re.match(r"^\d+$", part):
            numbers.append(int(part))
        else:
            break
    return tuple(numbers) or (0,)


def fetch_upstream_latest_version() -> Optional[str]:
    try:
        response = requests.get(UPSTREAM_RELEASES_URL, timeout=5)
        response.raise_for_status()
        tag = response.json().get("tag_name", "")
        return tag.lstrip("v") or None
    except Exception:
        return None


def get_cached_upstream_latest_version() -> Optional[str]:
    try:
        with open(_UPSTREAM_CACHE_FILE, "r", encoding="utf-8") as cache_file:
            data = json.load(cache_file)
        if time.time() - data.get("time", 0) < _UPSTREAM_CACHE_TTL:
            return data.get("version")
    except Exception:
        pass
    return None


def set_cached_upstream_latest_version(version: str) -> None:
    try:
        _UPSTREAM_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_UPSTREAM_CACHE_FILE, "w", encoding="utf-8") as cache_file:
            json.dump({"version": version, "time": time.time()}, cache_file)
    except Exception:
        pass
