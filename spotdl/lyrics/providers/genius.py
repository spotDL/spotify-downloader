from bs4 import BeautifulSoup
import urllib.request
import json

from spotdl.lyrics.lyric_base import LyricBase
from spotdl.lyrics.exceptions import LyricsNotFoundError

BASE_URL = "https://genius.com"
BASE_SEARCH_URL = BASE_URL + "/api/search/multi?per_page=1&q="

# FIXME: Make Genius a metadata provider instead of lyric provider
#        Since, Genius parses additional metadata too (such as track
#        name, artist name, albumart url). For example, fetch this URL:
#        https://genius.com/api/search/multi?per_page=1&q=artist+trackname

class Genius(LyricBase):
    def __init__(self):
        self.base_url = BASE_URL
        self.base_search_url = BASE_SEARCH_URL

    def guess_lyric_url_from_artist_and_track(self, artist, track):
        """
        Returns the possible lyric URL for the track available on
        Genius. This may not always be a valid URL.
        """
        query = "/{} {} lyrics".format(artist, track)
        query = query.replace(" ", "-")
        encoded_query = urllib.request.quote(query)
        lyric_url = self.base_url + encoded_query
        return lyric_url

    def _fetch_url_page(self, url, timeout=None):
        """
        Makes a GET request to the given lyrics page URL and returns
        the HTML content in the case of a valid response.
        """
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "urllib")
        try:
            response = urllib.request.urlopen(request, timeout=timeout)
        except urllib.request.HTTPError:
            raise LyricsNotFoundError(
                "Could not find lyrics at URL: {}".format(url)
            )
        else:
            return response.read()

    def _get_lyrics_text(self, html):
        """
        Extracts and returns the lyric content from the provided HTML.
        """
        soup = BeautifulSoup(html, "html.parser")
        lyrics_paragraph = soup.find("p")
        if lyrics_paragraph:
            return lyrics_paragraph.get_text()
        else:
            raise LyricsNotFoundError(
                "The lyrics for this track are yet to be released."
            )

    def _fetch_search_page(self, url, timeout=None):
        """
        Returns search results from a given URL in JSON.
        """
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "urllib")
        response = urllib.request.urlopen(request, timeout=timeout)
        metadata = json.loads(response.read())
        if len(metadata["response"]["sections"][0]["hits"]) == 0:
            raise LyricsNotFoundError(
                "Could not find any search results for URL: {}".format(url)
            )
        return metadata

    def best_matching_lyric_url_from_query(self, query):
        """
        Returns the best matching track's URL from a given query.
        """
        encoded_query = urllib.request.quote(query.replace(" ", "+"))
        search_url = self.base_search_url + encoded_query
        metadata = self._fetch_search_page(search_url)
        lyric_url = metadata["response"]["sections"][0]["hits"][0]["result"]["path"]
        return self.base_url + lyric_url

    def from_query(self, query, linesep="\n", timeout=None):
        """
        Returns the lyric string for the track best matching the
        given query.
        """
        lyric_url = self.best_matching_lyric_url_from_query(query)
        return self.from_url(lyric_url, linesep, timeout=timeout)

    def from_artist_and_track(self, artist, track, linesep="\n", timeout=None):
        """
        Returns the lyric string for the given artist and track
        by making scraping search results and fetching the first
        result.
        """
        lyric_url = self.guess_lyric_url_from_artist_and_track(artist, track)
        return self.from_url(lyric_url, linesep, timeout)

    def from_url(self, url, linesep="\n", timeout=None):
        """
        Returns the lyric string for the given URL.
        """
        lyric_html_page = self._fetch_url_page(url, timeout=timeout)
        lyrics = self._get_lyrics_text(lyric_html_page)
        return lyrics.replace("\n", linesep)

