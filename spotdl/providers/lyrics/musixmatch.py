"""
MusixMatch lyrics provider.
"""

from typing import Dict, List, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.utils.config import GlobalConfig

__all__ = ["MusixMatch"]


class MusixMatch(LyricsProvider):
    """
    MusixMatch lyrics provider class.
    """

    def extract_lyrics(self, url: str, **_) -> Optional[str]:
        """
        Extracts the lyrics from the given url.

        ### Arguments
        - url: The url to extract the lyrics from.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        lyrics_resp = requests.get(
            url,
            headers=self.headers,
            timeout=10,
            proxies=GlobalConfig.get_parameter("proxies"),
        )

        lyrics_soup = BeautifulSoup(lyrics_resp.text, "html.parser")
        lyrics_paragraphs = lyrics_soup.select("p.mxm-lyrics__content")
        lyrics = "\n".join(i.get_text() for i in lyrics_paragraphs)

        return lyrics

    def get_results(self, name: str, artists: List[str], **kwargs) -> Dict[str, str]:
        """
        Returns the results for the given song.

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - A dictionary with the results. (The key is the title and the value is the url.)
        """

        track_search = kwargs.get("track_search", False)
        artists_str = ", ".join(
            artist for artist in artists if artist.lower() not in name.lower()
        )

        # quote the query so that it's safe to use in a url
        # e.g "Au/Ra" -> "Au%2FRa"
        query = quote(f"{name} - {artists_str}", safe="")

        # search the `tracks page` if track_search is True
        if track_search:
            query += "/tracks"

        search_url = f"https://www.musixmatch.com/search/{query}"
        search_resp = requests.get(
            search_url,
            headers=self.headers,
            timeout=10,
            proxies=GlobalConfig.get_parameter("proxies"),
        )
        search_soup = BeautifulSoup(search_resp.text, "html.parser")
        song_url_tag = search_soup.select("a[href^='/lyrics/']")

        if not song_url_tag:
            # song_url_tag being None means no results were found on the
            # All Results page, therefore, we use `track_search` to
            # search the tracks page.

            # track_serach being True means we are already searching the tracks page.
            if track_search:
                return {}

            return self.get_results(name, artists, track_search=True)

        results: Dict[str, str] = {}
        for tag in song_url_tag:
            results[tag.get_text()] = "https://www.musixmatch.com" + str(
                tag.get("href", "")
            )

        return results
