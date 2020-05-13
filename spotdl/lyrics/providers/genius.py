from bs4 import BeautifulSoup
import urllib.request

from spotdl.lyrics.lyric_base import LyricBase
from spotdl.lyrics.exceptions import LyricsNotFound

BASE_URL = "https://genius.com"


class Genius(LyricBase):
    def __init__(self, artist, song):
        self.artist = artist
        self.song = song
        self.base_url = BASE_URL

    def _guess_lyric_url(self):
        query = "/{} {} lyrics".format(self.artist, self.song)
        query = query.replace(" ", "-")
        encoded_query = urllib.request.quote(query)
        lyric_url = self.base_url + encoded_query
        return lyric_url

    def _fetch_page(self, url, timeout=None):
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "urllib")
        try:
            response = urllib.request.urlopen(request, timeout=timeout)
        except urllib.request.HTTPError:
            raise LyricsNotFound(
                "Could not find lyrics for {} - {} at URL: {}".format(
                    self.artist, self.song, url
                )
            )
        else:
            return response.read()

    def _get_lyrics_text(self, html):
        soup = BeautifulSoup(html, "html.parser")
        lyrics_paragraph = soup.find("p")
        if lyrics_paragraph:
            return lyrics_paragraph.get_text()
        else:
            raise LyricsNotFound("The lyrics for this track are yet to be released.")

    def get_lyrics(self, linesep="\n", timeout=None):
        url = self._guess_lyric_url()
        html_page = self._fetch_page(url, timeout=timeout)
        lyrics = self._get_lyrics_text(html_page)
        return lyrics.replace("\n", linesep)
