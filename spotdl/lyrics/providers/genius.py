from bs4 import BeautifulSoup
import urllib.request

from spotdl.lyrics.lyric_base import LyricBase
from spotdl.lyrics.exceptions import LyricsNotFoundError

BASE_URL = "https://genius.com"


class Genius(LyricBase):
    def __init__(self, artist, track):
        self.artist = artist
        self.track = track
        self.base_url = BASE_URL

    def _guess_lyric_url(self):
        """
        Returns the possible lyric URL for the track available
        on Genius. This may not always be a valid URL, but this
        is apparently the best we can do at the moment?
        """
        query = "/{} {} lyrics".format(self.artist, self.track)
        query = query.replace(" ", "-")
        encoded_query = urllib.request.quote(query)
        lyric_url = self.base_url + encoded_query
        return lyric_url

    def _fetch_page(self, url, timeout=None):
        """
        Makes a GET request to the given URL and returns the
        HTML content in the case of a valid response.
        """
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "urllib")
        try:
            response = urllib.request.urlopen(request, timeout=timeout)
        except urllib.request.HTTPError:
            raise LyricsNotFoundError(
                "Could not find lyrics for {} - {} at URL: {}".format(
                    self.artist, self.track, url
                )
            )
        else:
            return response.read()

    def _get_lyrics_text(self, html):
        """
        Extracts and returns the lyric content from the
        provided HTML.
        """
        soup = BeautifulSoup(html, "html.parser")
        lyrics_paragraph = soup.find("p")
        if lyrics_paragraph:
            return lyrics_paragraph.get_text()
        else:
            raise LyricsNotFoundError(
                "The lyrics for this track are yet to be released."
            )

    def get_lyrics(self, linesep="\n", timeout=None):
        """
        Returns the lyric string for the given artist and track.
        """
        url = self._guess_lyric_url()
        html_page = self._fetch_page(url, timeout=timeout)
        lyrics = self._get_lyrics_text(html_page)
        return lyrics.replace("\n", linesep)
