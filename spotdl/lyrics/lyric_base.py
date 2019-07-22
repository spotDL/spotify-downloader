import lyricwikia

from abc import ABC
from abc import abstractmethod


class LyricBase(ABC):
    @abstractmethod
    def __init__(self, artist, song):
        pass

    @abstractmethod
    def get_lyrics(self, linesep="\n", timeout=None):
        pass
