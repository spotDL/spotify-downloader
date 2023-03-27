"""
Genius Lyrics module.
"""

from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.utils.formatter import ratio, slugify

__all__ = ["Genius"]


class Genius(LyricsProvider):
    """
    Genius lyrics provider class.
    """

    def get_lyrics(self, name: str, artists: List[str], **_) -> Optional[str]:
        """
        Try to get lyrics from genius

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        artists_str = ", ".join(artists)
        title = f"{name} - {artists_str}"

        try:
            headers = {
                "Authorization": "Bearer "
                "alXXDbPZtK1m2RrZ8I4k2Hn8Ahsd0Gh_o076HYvcdlBvmc0ULL1H8Z8xRlew5qaG",
            }

            headers.update(self.headers)

            search_response = requests.get(
                "https://api.genius.com/search",
                params={"q": title},
                headers=headers,
                timeout=10,
            )

            results = {}
            for hit in search_response.json()["response"]["hits"]:
                title_match = ratio(
                    slugify(hit["result"]["full_title"]), slugify(title)
                )
                if title_match > 55:
                    results[title_match] = hit["result"]["id"]

            # Get song id with highest title match
            if not results:
                return None

            song_id = results[max(results.keys())]
            song_response = requests.get(
                f"https://api.genius.com/songs/{song_id}", headers=headers, timeout=10
            )

            song_url = song_response.json()["response"]["song"]["url"]

            counter = 0
            soup = None
            while counter < 4:
                genius_page_response = requests.get(
                    song_url, headers=self.headers, timeout=10
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

            if lyrics_div is not None:
                return lyrics_div.get_text().strip()

            lyrics_containers = soup.select("div[class^=Lyrics__Container]")
            lyrics = "\n".join(con.get_text() for con in lyrics_containers)
            return lyrics.strip()
        except Exception:
            return None
