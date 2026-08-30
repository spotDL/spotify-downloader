import json
import logging
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

LRCLIB_GET = "https://lrclib.net/api/get"
LRCLIB_SEARCH = "https://lrclib.net/api/search"
_TIMEOUT = 8.0
_USER_AGENT = "spotdl-tui/1.0 (+https://lrclib.net)"


def fetch_lyrics(song: Any) -> Optional[Dict[str, Any]]:
    artists = getattr(song, "artists", None) or []
    artist = getattr(song, "artist", "") or (", ".join(artists) if artists else "")
    name = getattr(song, "name", "") or ""
    album = getattr(song, "album_name", "") or ""
    duration = getattr(song, "duration", None)

    payload = _try_get(artist, name, album, duration)
    if payload is None:
        payload = _try_search(artist, name)
    if payload is None:
        return None

    synced = _clean(payload.get("syncedLyrics"))
    plain = _clean(payload.get("plainLyrics"))
    if not synced and not plain:
        return None
    return {"synced": synced, "plain": plain, "source": "LRCLIB"}


def _try_get(
    artist: str, name: str, album: str, duration: Any
) -> Optional[Dict[str, Any]]:
    params: Dict[str, str] = {}
    if artist:
        params["artist_name"] = artist
    if name:
        params["track_name"] = name
    if album:
        params["album_name"] = album
    if duration:
        try:
            params["duration"] = str(int(duration))
        except (TypeError, ValueError):
            pass
    return _request_json(LRCLIB_GET, params, list_mode=False)


def _try_search(artist: str, name: str) -> Optional[Dict[str, Any]]:
    query = " ".join(part for part in (artist, name) if part).strip()
    if not query:
        return None
    results = _request_json(LRCLIB_SEARCH, {"q": query}, list_mode=True)
    if isinstance(results, list):
        for entry in results:
            if isinstance(entry, dict) and (
                _clean(entry.get("syncedLyrics")) or _clean(entry.get("plainLyrics"))
            ):
                return entry
    return None


def _request_json(url: str, params: Dict[str, str], list_mode: bool) -> Any:
    query = urlencode({k: v for k, v in params.items() if v})
    if not query:
        return None
    request = Request(f"{url}?{query}", headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(request, timeout=_TIMEOUT) as response:
            raw = response.read()
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        logger.debug("LRCLIB request failed (%s): %s", url, exc)
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.debug("LRCLIB bad json: %s", exc)
        return None
    if list_mode:
        return data if isinstance(data, list) else None
    return data if isinstance(data, dict) else None


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
