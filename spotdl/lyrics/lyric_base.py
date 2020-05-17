import lyricwikia

from abc import ABC
from abc import abstractmethod


class LyricBase(ABC):
    """
    Defined lyric providers must inherit from this abstract base
    class and implement their own functionality for the below
    defined methods.
    """

    @abstractmethod
    def from_url(self, url, linesep="\n", timeout=None):
        """
        This method must return the lyrics string for the
        given track.
        """
        pass

    @abstractmethod
    def from_artist_and_track(self, artist, track, linesep="\n", timeout=None):
        """
        This method must return the lyrics string for the
        given track.
        """
        pass

    @abstractmethod
    def from_query(self, query, linesep="\n", timeout=None):
        """
        This method must return the lyrics string for the
        given track.
        """
        pass
