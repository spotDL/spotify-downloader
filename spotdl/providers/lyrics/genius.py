"""
Genius Lyrics module.
"""

from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.utils.config import GlobalConfig

__all__ = ["Genius"]

_DOCS_SEARCH_URL = "https://api.genius.com/search"
_PUBLIC_SEARCH_URL = "https://genius.com/api/search/song"
_SONG_HIT_TYPES = {None, "song", "lyric"}


def _json_body(response: requests.Response) -> Any:
    """
    Decode a response body, or return None when it is not JSON.

    ### Arguments
    - response: The HTTP response to decode.

    ### Returns
    - The decoded JSON value, or None.
    """

    try:
        return response.json()
    except ValueError:
        return None


def _meta_message(payload: Any, fallback: str) -> str:
    """
    Read the error text from a Genius JSON body.

    ### Arguments
    - payload: Decoded JSON, or anything else.
    - fallback: Text used when the body has no meta message.

    ### Returns
    - The meta message, or the fallback.
    """

    if not isinstance(payload, dict):
        return fallback

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return fallback

    message = meta.get("message")
    if isinstance(message, str) and message:
        return message

    return fallback


def _iter_search_hits(payload: Any) -> Iterable[Dict[str, Any]]:
    """
    Yield search hits from either Genius response shape.

    The docs API returns `response.hits`. A typed search, including the
    public song search, returns `response.sections[].hits` instead.

    ### Arguments
    - payload: Decoded Genius search JSON.

    ### Returns
    - Hit objects from the search body.
    """

    if not isinstance(payload, dict):
        return

    response = payload.get("response")
    if not isinstance(response, dict):
        return

    hits = response.get("hits")
    if not isinstance(hits, list):
        hits = []
        sections = response.get("sections")
        if isinstance(sections, list):
            for section in sections:
                if not isinstance(section, dict):
                    continue

                section_hits = section.get("hits")
                if isinstance(section_hits, list):
                    hits.extend(section_hits)

    for hit in hits:
        if isinstance(hit, dict):
            yield hit


def _results_from_hits(
    hits: Iterable[Dict[str, Any]], *, prefer_url: bool
) -> Dict[str, str]:
    """
    Map Genius hits to a title and the value used to open the song.

    ### Arguments
    - hits: Search hits. Artist and album hits are ignored.
    - prefer_url: Use the public song page instead of the docs song id.
      The docs song endpoint shares the rate limit that makes search fail.

    ### Returns
    - Titles mapped to a song id, or to a song page URL.
    """

    results: Dict[str, str] = {}
    for hit in hits:
        if hit.get("type") not in _SONG_HIT_TYPES:
            continue

        result = hit.get("result")
        if not isinstance(result, dict):
            continue

        title = result.get("full_title")
        if not isinstance(title, str) or not title:
            continue

        page_url = result.get("url")
        song_id = result.get("id")
        if isinstance(page_url, str) and urlsplit(page_url).scheme in {"http", "https"}:
            page = page_url
        else:
            page = None

        if prefer_url and page is not None:
            results[title] = page
            continue

        if song_id is not None:
            results[title] = song_id
            continue

        if page is not None:
            results[title] = page

    return results


def _is_http_url(value: object) -> bool:
    """
    Return whether a search result already points at a page.

    ### Arguments
    - value: Song id or URL stored by the search. Docs hits store the id
      as a number.

    ### Returns
    - True when the value is an http or https URL.
    """

    if not isinstance(value, str):
        return False

    return urlsplit(value).scheme in {"http", "https"}


class Genius(LyricsProvider):
    """
    Genius lyrics provider class.
    """

    def __init__(self, access_token: str):
        """
        Init the lyrics provider search and set headers.
        """

        super().__init__()

        self.access_token = access_token
        self._docs_search_blocked = False

        self.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
            }
        )

        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_results(self, name: str, artists: List[str], **_) -> Dict[str, str]:
        """
        Returns the results for the given song.

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - A dictionary with the results. (The key is the title and the value is the url.)

        ### Notes
        - The bundled docs API client returns HTTP 429, with a `meta` object and
          no `response`, once its hourly quota is spent. Search then uses the
          public song endpoint, which returns `response.sections`.
        """

        artists_str = ", ".join(artists)
        title = f"{name} - {artists_str}"

        if not self._docs_search_blocked:
            payload, blocked = self._docs_search(title)
            if blocked:
                self._docs_search_blocked = True

            results = _results_from_hits(_iter_search_hits(payload), prefer_url=False)
            if results:
                return results

        return _results_from_hits(
            _iter_search_hits(self._public_search(title)), prefer_url=True
        )

    def _docs_search(self, title: str) -> tuple[Any, bool]:
        """
        Search the Genius docs API.

        ### Arguments
        - title: Song and artist query.

        ### Returns
        - The JSON body when it contains a response, otherwise None, and whether
          the docs client is rate limited.
        """

        search_response = self.session.get(
            _DOCS_SEARCH_URL,
            params={"q": title},
            headers=self.headers,
            timeout=10,
            proxies=GlobalConfig.get_parameter("proxies"),
        )
        payload = _json_body(search_response)
        blocked = search_response.status_code == 429

        if not search_response.ok or not isinstance(payload, dict):
            return None, blocked

        if "response" not in payload:
            return None, blocked

        meta = payload.get("meta")
        status = meta.get("status") if isinstance(meta, dict) else None
        if isinstance(status, int) and status >= 400:
            return None, blocked or status == 429

        return payload, False

    def _public_search(self, title: str) -> Any:
        """
        Search the public Genius song endpoint.

        The docs bearer token is omitted. Sending it spends the same quota
        that made the docs search fail.

        ### Arguments
        - title: Song and artist query.

        ### Returns
        - The decoded search JSON.

        ### Errors
        - RuntimeError: The public search did not return a response body.
        """

        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() != "authorization"
        }
        authorization = self.session.headers.pop("Authorization", None)
        try:
            search_response = self.session.get(
                _PUBLIC_SEARCH_URL,
                params={"q": title},
                headers=headers,
                timeout=10,
                proxies=GlobalConfig.get_parameter("proxies"),
            )
        finally:
            if authorization is not None:
                self.session.headers["Authorization"] = authorization

        payload = _json_body(search_response)
        if not search_response.ok or not isinstance(payload, dict):
            raise RuntimeError(
                _meta_message(
                    payload,
                    f"Received HTTP {search_response.status_code} from {search_response.url}",
                )
            )

        if "response" not in payload:
            raise RuntimeError(_meta_message(payload, "Unknown API error"))

        return payload

    def extract_lyrics(self, url: str, **_) -> Optional[str]:
        """
        Extracts the lyrics from the given url.

        ### Arguments
        - url: The url to extract the lyrics from. A docs song id is resolved
          through the songs API first.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        if not _is_http_url(url):
            song_response = self.session.get(
                f"https://api.genius.com/songs/{url}",
                headers=self.headers,
                timeout=10,
                proxies=GlobalConfig.get_parameter("proxies"),
            )
            url = song_response.json()["response"]["song"]["url"]

        soup = None
        counter = 0
        while counter < 4:
            genius_page_response = self.session.get(
                url,
                headers=self.headers,
                timeout=10,
                proxies=GlobalConfig.get_parameter("proxies"),
            )

            if not genius_page_response.ok:
                counter += 1
                continue

            soup = BeautifulSoup(
                genius_page_response.text.replace("<br/>", "\n"), "html.parser"
            )

            break

        if soup is None:
            return None

        lyrics_div = soup.select_one("div.lyrics")
        lyrics_container = soup.select("div[class^=Lyrics__Container]")

        # As of Aug 2025, Genius has added a lyrics header div. Remove it if present.
        # <div data-exclude-from-selection="true"
        # class="LyricsHeader__Container-sc-5e4b7146-1 hFsUgC">
        lyrics_header = soup.select_one("div[class^=LyricsHeader__Container]")

        if lyrics_header:
            lyrics_header.decompose()

        # Get lyrics
        if lyrics_div:
            lyrics = lyrics_div.get_text()
        elif lyrics_container:
            lyrics = "\n".join(con.get_text() for con in lyrics_container)
        else:
            return None

        if not lyrics:
            return None

        # Clean lyrics
        lyrics = lyrics.strip()

        # Remove desc at the beginning if it exists
        for to_remove in ["desc", "Desc"]:
            lyrics.replace(to_remove, "", 1)

        return lyrics
