"""
Genius Lyrics module.
"""

from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from spotdl.providers.lyrics.base import LyricsProvider

__all__ = ["Genius"]


class Genius(LyricsProvider):
    """
    Genius lyrics provider class.
    """

    def __init__(self):
        """
        Init the lyrics provider search and set headers.
        """

        super().__init__()

        self.headers.update(
            {
                "Authorization": "Bearer "
                "alXXDbPZtK1m2RrZ8I4k2Hn8Ahsd0Gh_o076HYvcdlBvmc0ULL1H8Z8xRlew5qaG",
            }
        )

    def get_results(self, name: str, artists: List[str], **_) -> Dict[str, str]:
        """
        Returns the results for the given song.

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - A dictionary with the results. (The key is the title and the value is the url.)
        """

        artists_str = ", ".join(artists)
        title = f"{name} - {artists_str}"

        search_response = requests.get(
            "https://api.genius.com/search",
            params={"q": title},
            headers=self.headers,
            timeout=10,
        )

        results: Dict[str, str] = {}
        for hit in search_response.json()["response"]["hits"]:
            results[hit["result"]["full_title"]] = hit["result"]["id"]

        return results

    def extract_lyrics(self, url: str, **_) -> Optional[str]:
        """
        Extracts the lyrics from the given url.

        ### Arguments
        - url: The url to extract the lyrics from.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        url = f"https://api.genius.com/songs/{url}"
        song_response = requests.get(url, headers=self.headers, timeout=10)
        url = song_response.json()["response"]["song"]["url"]

        soup = None
        counter = 0
        while counter < 4:
            genius_page_response = requests.get(url, headers=self.headers, timeout=10)

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
        lyrics_containers = soup.select("div[class^=Lyrics__Container]")

        # Get lyrics
        if lyrics_div:
            lyrics = lyrics_div.get_text()
        elif lyrics_containers:
            lyrics = "\n".join(con.get_text() for con in lyrics_containers)
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
