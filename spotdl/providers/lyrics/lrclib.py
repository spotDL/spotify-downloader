"""
LRCLib lyrics provider.
"""

from typing import Dict, List, Optional

import requests

from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.utils.config import GlobalConfig

__all__ = ["Lrclib"]

BASE_URL = "https://lrclib.net/api"
SEARCH_URL = f"{BASE_URL}/search"
GET_URL = f"{BASE_URL}/get"

INSTRUMENTAL_MARKER = "[Instrumental]"


class Lrclib(LyricsProvider):
    """
    LRCLib lyrics provider class.
    """

    def get_results(self, name: str, artists: List[str], **_) -> Dict[str, str]:
        """
        Returns the results for the given song.

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.

        ### Returns
        - A dictionary with the results.
        """

        artist = artists[0] if artists else ""

        params = {
            "artist_name": artist,
            "track_name": name,
        }

        try:
            search_resp = requests.get(
                SEARCH_URL,
                params=params,
                timeout=10,
                proxies=GlobalConfig.get_parameter("proxies"),
            )
        except Exception:
            return {}

        if not search_resp.ok:
            return {}

        results: Dict[str, str] = {}
        for item in search_resp.json():
            track = item.get("trackName") or item.get("name") or name
            results[f"{item.get('artistName', artist)} - {track}"] = str(item.get("id"))

        return results

    def extract_lyrics(self, url: str, **_) -> Optional[str]:
        """
        Extracts the lyrics for a song id.

        ### Arguments
        - url: The song id returned by get_results.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        try:
            int(url)
        except (TypeError, ValueError):
            return None

        try:
            song_resp = requests.get(
                f"{GET_URL}/{url}",
                timeout=10,
                proxies=GlobalConfig.get_parameter("proxies"),
            )
        except Exception:
            return None

        if not song_resp.ok:
            return None

        data = song_resp.json()
        if data.get("instrumental"):
            return INSTRUMENTAL_MARKER

        return data.get("plainLyrics") or data.get("syncedLyrics")
