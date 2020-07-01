from bs4 import BeautifulSoup
import urllib.request
import json

from spotdl.lyrics.lyric_base import LyricBase
from spotdl.lyrics.exceptions import LyricsNotFoundError

import logging
logger = logging.getLogger(__name__)

BASE_URL = "https://genius.com"
BASE_SEARCH_URL = BASE_URL + "/api/search/multi?per_page=1&q="

# FIXME: Make Genius a metadata provider instead of lyric provider
#        Since, Genius parses additional metadata too (such as track
#        name, artist name, albumart url). For example, fetch this URL:
#        https://genius.com/api/search/multi?per_page=1&q=artist+trackname

class Genius(LyricBase):
    """
    Fetch lyrics from Genius.

    Examples
    --------
    + Fetching lyrics for *"Tobu - Cruel"*:

        >>> from spotdl.lyrics.providers import Genius
        >>> genius = Genius()
        >>> lyrics = genius.from_query("tobu cruel")
        >>> print(lyrics)
    """

    def __init__(self):
        self.base_url = BASE_URL
        self.base_search_url = BASE_SEARCH_URL

    def _guess_lyric_url_from_artist_and_track(self, artist, track):
        """
        Returns the possible lyric URL for the track available on
        Genius. This may not always be a valid URL.

        Parameters
        ----------
        artist: `str`
            Artist name.

        track: `str`
            Track name.
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
                "Could not find Genius lyrics at URL: {}".format(url)
            )
        else:
            return response.read()

    def _get_lyrics_text(self, paragraph):
        """
        Extracts and returns the lyric content from the provided HTML.
        """
        if paragraph:
            return paragraph.get_text()
        else:
            raise LyricsNotFoundError(
                "The lyrics for this track are yet to be released on Genius."
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
                "Genius returned no lyric results for the search URL: {}".format(url)
            )
        return metadata

    def best_matching_lyric_url_from_query(self, query):
        """
        Fetches the best matching lyric track URL for a given query.

        Parameters
        ----------
        query: `str`
            The search query.

        Returns
        -------
        lyric_url: `str`
            The best matching track lyric URL on Genius.
        """
        encoded_query = urllib.request.quote(query.replace(" ", "+"))
        search_url = self.base_search_url + encoded_query
        logger.debug('Fetching Genius search results from "{}".'.format(search_url))
        metadata = self._fetch_search_page(search_url)

        lyric_url = None
        for section in metadata["response"]["sections"]:
            result = section["hits"][0]["result"]
            try:
                lyric_url = result["path"]
                break
            except KeyError:
                pass

        if lyric_url is None:
            raise LyricsNotFoundError(
                "Could not find any valid lyric paths in Genius "
                "lyrics API response for the query {}.".format(query)
            )

        return self.base_url + lyric_url

    def from_query(self, query, linesep="\n", timeout=None):
        logger.debug('Fetching lyrics for the search query on "{}".'.format(query))
        try:
            lyric_url = self.best_matching_lyric_url_from_query(query)
        except LyricsNotFoundError:
            raise LyricsNotFoundError(
                'Genius returned no lyric results for the search query "{}".'.format(query)
            )
        else:
            return self.from_url(lyric_url, linesep, timeout=timeout)

    def from_artist_and_track(self, artist, track, linesep="\n", timeout=None):
        lyric_url = self._guess_lyric_url_from_artist_and_track(artist, track)
        return self.from_url(lyric_url, linesep, timeout=timeout)

    def from_url(self, url, linesep="\n", retries=5, timeout=None):
        logger.debug('Fetching lyric text from "{}".'.format(url))
        lyric_html_page = self._fetch_url_page(url, timeout=timeout)
        soup = BeautifulSoup(lyric_html_page, "html.parser")
        paragraph = soup.find("p")
        # If <p> is not found or
        # if <p> has a class (like <p class="bla">), then we got an invalid
        # response.
        # Retry in such a case.
        invalid_response = paragraph is None or paragraph.get("class") is not None
        to_retry = retries > 0 and invalid_response
        if to_retry:
            logger.debug(
                "Retrying since Genius returned invalid response for search "
                "results. Retries left: {retries}.".format(retries=retries)
            )
            return self.from_url(url, linesep=linesep, retries=retries-1, timeout=timeout)

        if invalid_response:
            raise LyricsNotFoundError(
                'Genius returned invalid response for the search URL "{}".'.format(url)
            )
        lyrics = self._get_lyrics_text(paragraph)
        return lyrics.replace("\n", linesep)

