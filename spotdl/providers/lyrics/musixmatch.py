"""
MusixMatch lyrics provider.
"""

import time
from typing import Dict, List, Optional

import requests

from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.utils.config import GlobalConfig

__all__ = ["MusixMatch"]


class MusixMatch(LyricsProvider):
    """
    MusixMatch lyrics provider class.

    Uses MusixMatch's internal desktop-app API instead of scraping
    musixmatch.com: the public site's search page sits behind a WAF that
    blocks non-browser requests regardless of TLS fingerprint or headers
    (see #2741), but the desktop API used by other unofficial MusixMatch
    clients (e.g. syncedlyrics) is not affected.
    """

    ROOT_URL = "https://apic-desktop.musixmatch.com/ws/1.1/"
    APP_ID = "web-desktop-app-v1.0"

    def __init__(self) -> None:
        super().__init__()
        self._token: Optional[str] = None

    def _call(self, action: str, params: List[tuple]) -> dict:
        query = [*params, ("app_id", self.APP_ID)]
        if self._token is not None:
            query.append(("usertoken", self._token))
        query.append(("t", str(int(time.time() * 1000))))

        response = requests.get(
            self.ROOT_URL + action,
            params=query,
            timeout=10,
            proxies=GlobalConfig.get_parameter("proxies"),
        )
        response.raise_for_status()
        return response.json()["message"]

    def _get_token(self) -> Optional[str]:
        """
        Fetches a fresh usertoken. MusixMatch occasionally answers the
        first attempt or two with a "captcha" hint; retrying after a short
        delay (the same workaround other MusixMatch API clients use)
        resolves it.
        """
        for _ in range(3):
            message = self._call("token.get", [("user_language", "en")])
            header = message["header"]
            if header["status_code"] == 200:
                return message["body"]["user_token"]
            if header.get("hint") != "captcha":
                return None
            time.sleep(10)
        return None

    def _call_authenticated(self, action: str, params: List[tuple]) -> dict:
        """
        Like `_call`, but makes sure a usertoken is set first, and retries
        once with a freshly fetched token if MusixMatch reports that the
        current one needs renewing (tokens appear to be short-lived/
        single-use on this API).
        """
        if self._token is None:
            self._token = self._get_token()
        if self._token is None:
            return {"header": {"status_code": 401}}

        message = self._call(action, params)
        if message["header"]["status_code"] == 401:
            self._token = self._get_token()
            if self._token is None:
                return message
            message = self._call(action, params)

        return message

    def get_results(self, name: str, artists: List[str], **kwargs) -> Dict[str, str]:
        """
        Returns the results for the given song.

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - A dictionary with the results. (The key is the title and the
          value is the MusixMatch track id.)
        """

        artists_str = ", ".join(
            artist for artist in artists if artist.lower() not in name.lower()
        )
        message = self._call_authenticated(
            "track.search",
            [
                ("q", f"{name} {artists_str}".strip()),
                ("page_size", "20"),
                ("page", "1"),
            ],
        )

        if message["header"]["status_code"] != 200:
            return {}

        body = message.get("body")
        track_list = body.get("track_list") if isinstance(body, dict) else None
        if not track_list:
            return {}

        results: Dict[str, str] = {}
        for entry in track_list:
            track = entry["track"]
            # Plenty of user-uploaded remixes/speed-ups show up in search
            # with no lyrics attached; skip those rather than matching on
            # title alone and getting an empty result from extract_lyrics.
            if not track.get("has_lyrics"):
                continue
            title = f"{track['track_name']} - {track['artist_name']}"
            results[title] = str(track["track_id"])

        return results

    def extract_lyrics(self, url: str, **_) -> Optional[str]:
        """
        Extracts the lyrics for the given song.

        ### Arguments
        - url: The MusixMatch track id, as returned by `get_results`.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        message = self._call_authenticated("track.lyrics.get", [("track_id", url)])
        if message["header"]["status_code"] != 200:
            return None

        body = message.get("body")
        if not body:
            return None

        return body["lyrics"]["lyrics_body"]
