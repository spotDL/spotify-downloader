import lyricwikia

from spotdl.lyrics import LyricBase
from spotdl.lyrics import exceptions
from spotdl.lyrics.providers import LyricWikia

import pytest


class TestLyricWikia:
    def test_subclass(self):
        assert issubclass(LyricWikia, LyricBase)

    def test_from_artist_and_track(self, monkeypatch):
        # `LyricWikia` class uses the 3rd party method `lyricwikia.get_lyrics`
        # internally and there is no need to test a 3rd party library as they
        # have their own implementation of tests.
        monkeypatch.setattr(
            "lyricwikia.get_lyrics", lambda a, b, c, d: "awesome lyrics!"
        )
        artist, track = "selena gomez", "wolves"
        lyrics = LyricWikia().from_artist_and_track(artist, track)
        assert lyrics == "awesome lyrics!"

    def test_lyrics_not_found_error(self, monkeypatch):
        def lyricwikia_lyrics_not_found(msg):
            raise lyricwikia.LyricsNotFound(msg)

        # Wrap `lyricwikia.LyricsNotFoundError` with `exceptions.LyricsNotFoundError` error.
        monkeypatch.setattr(
            "lyricwikia.get_lyrics",
            lambda a, b, c, d: lyricwikia_lyrics_not_found("Nope, no lyrics."),
        )
        artist, track = "nonexistent_artist", "nonexistent_track"
        with pytest.raises(exceptions.LyricsNotFoundError):
            LyricWikia().from_artist_and_track(artist, track)
