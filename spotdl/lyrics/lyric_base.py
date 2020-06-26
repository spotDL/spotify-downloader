import lyricwikia

from abc import ABC
from abc import abstractmethod


class LyricBase(ABC):
    """
    Defined lyric providers must inherit from this abstract base
    class and implement their own functionality for the below
    defined methods.
    """

    def from_url(self, url, linesep="\n", timeout=None):
        """
        Fetches lyrics given a URL.

        Parameters
        ----------
        url: `str`
            URL to fetch lyrics from.

        linesep: `str`
            Use this separator between every line of the lyrics.

        timeout: `int`, `None`
            Timeout duration such as if the server doesn't return a
            response in an expected time frame.

        Returns
        -------
        lyrics: `str`
        """
        raise NotImplementedError

    def from_artist_and_track(self, artist, track, linesep="\n", timeout=None):
        """
        Fetches lyrics given an artist and the track name.

        Parameters
        ----------
        artist: `str`
            Artist name.

        track: `str`
            Track name.

        linesep: `str`
            Use this separator between every line of the lyrics.

        timeout: `int`, `None`
            Timeout duration such as if the server doesn't return a
            response in an expected time frame.

        Returns
        -------
        lyrics: `str`
        """
        raise NotImplementedError

    def from_query(self, query, linesep="\n", timeout=None):
        """
        Fetches lyrics given a search query.

        Parameters
        ----------
        query: `str`
            A search query.

        linesep: `str`
            Use this separator between every line of the lyrics.

        timeout: `int`, `None`
            Timeout duration such as if the server doesn't return a
            response in an expected time frame.

        Returns
        -------
        lyrics: `str`
        """
        raise NotImplementedError

