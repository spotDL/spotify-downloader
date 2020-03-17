import lyricwikia

from spotdl.lyrics.lyric_base import LyricBase
from spotdl.lyrics.exceptions import LyricsNotFoundError


class LyricWikia(LyricBase):
    def __init__(self, artist, track):
        self.artist = artist
        self.track = track

    def get_lyrics(self, linesep="\n", timeout=None):
        try:
            lyrics = lyricwikia.get_lyrics(self.artist, self.track, linesep, timeout)
        except lyricwikia.LyricsNotFound as e:
            raise LyricsNotFoundError(e.args[0])
        else:
            return lyrics
