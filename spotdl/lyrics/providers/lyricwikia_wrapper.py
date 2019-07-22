import lyricwikia

from spotdl.lyrics.lyric_base import LyricBase
from spotdl.lyrics.exceptions import LyricsNotFound


class LyricWikia(LyricBase):
    def __init__(self, artist, song):
        self.artist = artist
        self.song = song

    def get_lyrics(self, linesep="\n", timeout=None):
        try:
            lyrics = lyricwikia.get_lyrics(self.artist, self.song, linesep, timeout)
        except lyricwikia.LyricsNotFound as e:
            raise LyricsNotFound(e.args[0])
        else:
            return lyrics
