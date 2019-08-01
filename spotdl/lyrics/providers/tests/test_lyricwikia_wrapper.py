import lyricwikia

from spotdl.lyrics import LyricBase
from spotdl.lyrics import exceptions
from spotdl.lyrics.providers import LyricWikia

import pytest


class TestLyricWikia:
    def test_subclass(self):
        assert issubclass(LyricWikia, LyricBase)

    def test_get_lyrics(self, monkeypatch):
        # `LyricWikia` class uses the 3rd party method `lyricwikia.get_lyrics`
        # internally and there is no need to test a 3rd party library as they
        # have their own implementation of tests.
        monkeypatch.setattr(
            "lyricwikia.get_lyrics", lambda a, b, c, d: "awesome lyrics!"
        )
        track = LyricWikia("Lyricwikia", "Lyricwikia")
        assert track.get_lyrics() == "awesome lyrics!"

    def test_lyrics_not_found_error(self, monkeypatch):
        def lyricwikia_lyrics_not_found(msg):
            raise lyricwikia.LyricsNotFound(msg)

        # Wrap `lyricwikia.LyricsNotFound` with `exceptions.LyricsNotFound` error.
        monkeypatch.setattr(
            "lyricwikia.get_lyrics",
            lambda a, b, c, d: lyricwikia_lyrics_not_found("Nope, no lyrics."),
        )
        track = LyricWikia("Lyricwikia", "Lyricwikia")
        with pytest.raises(exceptions.LyricsNotFound):
            track.get_lyrics()
