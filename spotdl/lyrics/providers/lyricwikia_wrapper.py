import lyricwikia

from spotdl.lyrics.lyric_base import LyricBase
from spotdl.lyrics.exceptions import LyricsNotFoundError


class LyricWikia(LyricBase):
    def from_query(self, query, linesep="\n", timeout=None):
        raise NotImplementedError

    def from_artist_and_track(self, artist, track, linesep="\n", timeout=None):
        """
        Returns the lyric string for the given artist and track.
        """
        try:
            lyrics = lyricwikia.get_lyrics(artist, track, linesep, timeout)
        except lyricwikia.LyricsNotFound as e:
            raise LyricsNotFoundError(e.args[0])

        return lyrics

    def from_url(self, url, linesep="\n", timeout=None):
        raise NotImplementedError

