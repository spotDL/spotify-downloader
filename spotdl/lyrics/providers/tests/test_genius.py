from spotdl.lyrics import LyricBase
from spotdl.lyrics import exceptions
from spotdl.lyrics.providers import Genius

import urllib.request
import json
import pytest

class TestGenius:
    def test_subclass(self):
        assert issubclass(Genius, LyricBase)

    @pytest.fixture(scope="module")
    def expect_lyrics_count(self):
        # This is the number of characters in lyrics found
        # for the track in `lyric_url` fixture below
        return 1845

    @pytest.fixture(scope="module")
    def genius(self):
        return Genius()

    def test_base_url(self, genius):
        assert genius.base_url == "https://genius.com"

    @pytest.fixture(scope="module")
    def artist(self):
        return "selena gomez"

    @pytest.fixture(scope="module")
    def track(self):
        return "wolves"

    @pytest.fixture(scope="module")
    def query(self, artist, track):
        return "{} {}".format(artist, track)

    @pytest.fixture(scope="module")
    def guess_url(self, query):
        return "https://genius.com/selena-gomez-wolves-lyrics"

    @pytest.fixture(scope="module")
    def lyric_url(self):
        return "https://genius.com/Selena-gomez-and-marshmello-wolves-lyrics"

    def test_guess_lyric_url_from_artist_and_track(self, genius, artist, track, guess_url):
        url = genius._guess_lyric_url_from_artist_and_track(artist, track)
        assert url == guess_url

    class MockHTTPResponse:
        expect_lyrics = ""

        def __init__(self, request, timeout=None):
            search_results_url = "https://genius.com/api/search/multi?per_page=1&q=selena%2Bgomez%2Bwolves"
            if request._full_url == search_results_url:
                read_method = lambda: json.dumps({
                    "response": {"sections": [{"hits": [{"result": {
                        "path": "/Selena-gomez-and-marshmello-wolves-lyrics"
                    } }] }] }
                })
            else:
                read_method = lambda: "<p>" + self.expect_lyrics + "</p>"

            self.read = read_method

    @pytest.mark.network
    def test_best_matching_lyric_url_from_query(self, genius, query, lyric_url):
        url = genius.best_matching_lyric_url_from_query(query)
        assert url == lyric_url

    def test_mock_best_matching_lyric_url_from_query(self, genius, query, lyric_url, monkeypatch):
        monkeypatch.setattr("urllib.request.urlopen", self.MockHTTPResponse)
        self.test_best_matching_lyric_url_from_query(genius, query, lyric_url)

    @pytest.mark.network
    def test_from_url(self, genius, lyric_url, expect_lyrics_count):
        lyrics = genius.from_url(lyric_url)
        assert len(lyrics) == expect_lyrics_count

    def test_mock_from_url(self, genius, lyric_url, expect_lyrics_count, monkeypatch):
        self.MockHTTPResponse.expect_lyrics = "a" * expect_lyrics_count
        monkeypatch.setattr("urllib.request.urlopen", self.MockHTTPResponse)
        self.test_from_url(genius, lyric_url, expect_lyrics_count)

    @pytest.mark.network
    def test_from_artist_and_track(self, genius, artist, track, expect_lyrics_count):
        lyrics = genius.from_artist_and_track(artist, track)
        assert len(lyrics) == expect_lyrics_count

    def test_mock_from_artist_and_track(self, genius, artist, track, expect_lyrics_count, monkeypatch):
        self.MockHTTPResponse.expect_lyrics = "a" * expect_lyrics_count
        monkeypatch.setattr("urllib.request.urlopen", self.MockHTTPResponse)
        self.test_from_artist_and_track(genius, artist, track, expect_lyrics_count)

    @pytest.mark.network
    def test_from_query(self, genius, query, expect_lyrics_count):
        lyrics = genius.from_query(query)
        assert len(lyrics) == expect_lyrics_count

    def test_mock_from_query(self, genius, query, expect_lyrics_count, monkeypatch):
        self.MockHTTPResponse.expect_lyrics = "a" * expect_lyrics_count
        monkeypatch.setattr("urllib.request.urlopen", self.MockHTTPResponse)
        self.test_from_query(genius, query, expect_lyrics_count)

    @pytest.mark.network
    def test_lyrics_not_found_error(self, genius):
        with pytest.raises(exceptions.LyricsNotFoundError):
            genius.from_artist_and_track(self, "nonexistent_artist", "nonexistent_track")

    def test_mock_lyrics_not_found_error(self, genius, monkeypatch):
        def mock_urlopen(url, timeout=None):
            raise urllib.request.HTTPError("", "", "", "", "")

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        self.test_lyrics_not_found_error(genius)

