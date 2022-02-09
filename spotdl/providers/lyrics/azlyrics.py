from typing import List, Optional
from bs4 import BeautifulSoup
import requests
from spotdl.providers.lyrics.base import LyricsProvider


def search_song(song_name: str, artists: str) -> Optional[str]:
    '''
    Returns a string of the URL of the lyric of the song.

    Parameters
    ----------

    song_name : str
        Name of the song.

    artists : str
        Names of the artists, separated by commas.
    '''

    song_name = song_name.replace(' ', '+').lower()
    artists = artists.replace(' ', '+').lower()
    artists = artists.replace(',', '%2C')

    url = f"https://search.azlyrics.com/search.php?q={song_name}+{artists}"

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    td_tags = soup.find_all('td')

    if len(td_tags) == 0:
        return ""

    result = td_tags[0]

    a_tags = result.find_all('a', href=True)

    if len(a_tags) != 0:
        return a_tags[0]['href']

    return ""


class AzLyrics(LyricsProvider):
    def get_lyrics(self, name: str, artists: List[str], **kwargs) -> Optional[str]:
        """
        Try to get lyrics from azlyrics
        """

        # Join every artist by comma in artists
        artist_str = ", ".join(artist for artist in artists if artist.lower())

        self.lyrics_url = search_song(name, artist_str)

        if self.lyrics_url is None:
            return ""

        response = requests.get(self.lyrics_url)

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all divs that don't have a class

        div_tags = soup.find_all('div', class_=False, id_=False)

        lyrics = div_tags[1].get_text()

        # Remove the 3 first new lines

        lyrics = lyrics[3:]

        return lyrics
