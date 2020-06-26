import lyricwikia

from spotdl.lyrics.lyric_base import LyricBase
from spotdl.lyrics.exceptions import LyricsNotFoundError


class LyricWikia(LyricBase):
    """
    Fetch lyrics from LyricWikia.

    Examples
    --------
    + Fetching lyrics for *"Tobu - Cruel"*:

        >>> from spotdl.lyrics.providers import LyricWikia
        >>> genius = LyricWikia()
        >>> lyrics = genius.from_artist_and_track("Tobu", "Cruel")
        >>> print(lyrics)
    """

    def from_artist_and_track(self, artist, track, linesep="\n", timeout=None):
        """
        Returns the lyric string for the given artist and track.
        """
        try:
            lyrics = lyricwikia.get_lyrics(artist, track, linesep, timeout)
        except lyricwikia.LyricsNotFound as e:
            raise LyricsNotFoundError(e.args[0])
        return lyrics

