"""
AZLyrics lyrics module.
"""

from typing import List, Optional

from bs4 import BeautifulSoup

import requests

from spotdl.providers.lyrics.base import LyricsProvider


class AzLyrics(LyricsProvider):
    """
    AZLyrics lyrics provider class.
    """

    def __init__(self):
        super().__init__()

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Not sure if this is needed
        # but it doesn't hurt
        self.session.get("https://www.azlyrics.com/")

        resp = self.session.get("https://www.azlyrics.com/geo.js")

        # extract value from js code
        js_code = resp.text
        start_index = js_code.find('value"') + 9
        end_index = js_code[start_index:].find('");')

        self.x_code = js_code[start_index : start_index + end_index]

    def get_lyrics(self, name: str, artists: List[str], **_) -> Optional[str]:
        """
        Try to get lyrics from azlyrics

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        # Join every artist by comma in artists
        artist_str = ", ".join(artist for artist in artists if artist)

        params = {
            "q": f"{artist_str} - {name}",
            "x": self.x_code,
        }

        response = self.session.get(
            "https://search.azlyrics.com/search.php", params=params
        )
        soup = BeautifulSoup(response.content, "html.parser")

        td_tags = soup.find_all("td")
        if len(td_tags) == 0:
            return None

        result = td_tags[0]

        a_tags = result.find_all("a", href=True)
        if len(a_tags) != 0:
            lyrics_url = a_tags[0]["href"]
        else:
            return None

        if lyrics_url.strip() == "":
            return None

        response = self.session.get(lyrics_url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all divs that don't have a class
        div_tags = soup.find_all("div", class_=False, id_=False)

        # Find the div with the longest text
        lyrics_div = sorted(div_tags, key=lambda x: len(x.text))[-1]

        # extract lyrics from div and clean it up
        lyrics = lyrics_div.get_text().strip()

        return lyrics
