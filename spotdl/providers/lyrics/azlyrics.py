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

        song_name = name.replace(" ", "+").lower()
        song_artists = artist_str.replace(" ", "+").lower()
        song_artists = song_artists.replace(",", "%2C")

        url = f"https://search.azlyrics.com/search.php?q={song_name}+{artists}"

        response = requests.get(url, headers=self.headers)
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

        response = requests.get(lyrics_url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all divs that don't have a class
        div_tags = soup.find_all("div", class_=False, id_=False)

        # Find the div with the longest text
        lyrics_div = sorted(div_tags, key=lambda x: len(x.text))[-1]

        lyrics = lyrics_div.get_text()

        # Remove the 3 first new lines
        lyrics = lyrics[3:]

        return lyrics
