from spotdl.lyrics import LyricBase
from spotdl.lyrics import exceptions
from spotdl.lyrics.providers import Genius

import urllib.request
import pytest


class TestGenius:
    def test_subclass(self):
        assert issubclass(Genius, LyricBase)

    @pytest.fixture(scope="module")
    def track(self):
        return Genius("artist", "song")

    def test_base_url(self, track):
        assert track.base_url == "https://genius.com"

    def test_get_lyrics(self, track, monkeypatch):
        def mocked_urlopen(url, timeout=None):
            class DummyHTTPResponse:
                def read(self):
                    return "<p>amazing lyrics!</p>"

            return DummyHTTPResponse()

        monkeypatch.setattr("urllib.request.urlopen", mocked_urlopen)
        assert track.get_lyrics() == "amazing lyrics!"

    def test_lyrics_not_found_error(self, track, monkeypatch):
        def mocked_urlopen(url, timeout=None):
            raise urllib.request.HTTPError("", "", "", "", "")

        monkeypatch.setattr("urllib.request.urlopen", mocked_urlopen)
        with pytest.raises(exceptions.LyricsNotFound):
            track.get_lyrics()
