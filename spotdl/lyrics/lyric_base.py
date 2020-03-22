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
    def __init__(self, artist, track):
        """
        This method must set any protected attributes,
        which may be modified from outside the class
        if the need arises.
        """
        pass

    @abstractmethod
    def get_lyrics(self, linesep="\n", timeout=None):
        """
        This method must return the lyrics string for the
        given track.
        """
        pass
