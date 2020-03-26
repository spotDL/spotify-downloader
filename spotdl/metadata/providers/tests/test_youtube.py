from spotdl.metadata.providers.youtube import YouTubeSearch
from spotdl.metadata.providers.youtube import YouTubeStreams
from spotdl.metadata.providers import youtube
from spotdl.metadata.providers import ProviderYouTube
from spotdl.metadata.exceptions import YouTubeMetadataNotFoundError

import pytube
import urllib.request
import pickle
import sys
import os
import pytest


@pytest.fixture(scope="module")
def track():
    return "selena gomez wolves"


@pytest.fixture(scope="module")
def no_result_track():
    return "n0 v1d305 3x157 f0r 7h15 53arc4 qu3ry"


@pytest.fixture(scope="module")
def expect_search_results():
    return [
        "https://www.youtube.com/watch?v=cH4E_t3m3xM",
        "https://www.youtube.com/watch?v=xrbY9gDVms0",
        "https://www.youtube.com/watch?v=jX0n2rSmDbE",
        "https://www.youtube.com/watch?v=nVzA1uWTydQ",
        "https://www.youtube.com/watch?v=rQ6jcpwzQZU",
        "https://www.youtube.com/watch?v=-grLLLTza6k",
        "https://www.youtube.com/watch?v=j0AxZ4V5WQw",
        "https://www.youtube.com/watch?v=zbWsb36U0uo",
        "https://www.youtube.com/watch?v=3B1aY9Ob8r0",
        "https://www.youtube.com/watch?v=hd2SGk90r9k",
    ]


@pytest.fixture(scope="module")
def expect_mock_search_results():
    return [
        "https://www.youtube.com/watch?v=cH4E_t3m3xM",
        "https://www.youtube.com/watch?v=xrbY9gDVms0",
        "https://www.youtube.com/watch?v=jX0n2rSmDbE",
        "https://www.youtube.com/watch?v=rQ6jcpwzQZU",
        "https://www.youtube.com/watch?v=nVzA1uWTydQ",
        "https://www.youtube.com/watch?v=-grLLLTza6k",
        "https://www.youtube.com/watch?v=zbWsb36U0uo",
        "https://www.youtube.com/watch?v=rykH1BkGwTo",
        "https://www.youtube.com/watch?v=j0AxZ4V5WQw",
        "https://www.youtube.com/watch?v=RyxsaKfu-ZY",
    ]


class TestYouTubeSearch:
    @pytest.fixture(scope="module")
    def youtube_searcher(self):
        return YouTubeSearch()

    def test_generate_search_url(self, track, youtube_searcher):
        url = youtube_searcher.generate_search_url(track)
        expect_url = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q=selena%20gomez%20wolves"
        assert url == expect_url

    @pytest.mark.network
    def test_search(self, track, youtube_searcher, expect_search_results):
        results = youtube_searcher.search(track)
        assert results == expect_search_results

    class MockHTTPResponse:
        response_file = ""

        def __init__(self, url):
            pass

        def read(self):
            module_directory = os.path.dirname(__file__)
            mock_html = os.path.join(module_directory, "data", self.response_file)
            with open(mock_html, "r") as fin:
                html = fin.read()
            return html

    # @pytest.mark.mock
    def test_mock_search(self, track, youtube_searcher, expect_mock_search_results, monkeypatch):
        self.MockHTTPResponse.response_file = "youtube_search_results.html"
        monkeypatch.setattr(urllib.request, "urlopen", self.MockHTTPResponse)
        self.test_search(track, youtube_searcher, expect_mock_search_results)

    @pytest.mark.network
    def test_no_videos_search(self, no_result_track, youtube_searcher):
        results = youtube_searcher.search(no_result_track)
        assert results == []

    def test_mock_no_videos_search(self, no_result_track, youtube_searcher, monkeypatch):
        self.MockHTTPResponse.response_file = "youtube_no_search_results.html"
        monkeypatch.setattr(urllib.request, "urlopen", self.MockHTTPResponse)
        self.test_no_videos_search(no_result_track, youtube_searcher)


@pytest.fixture(scope="module")
def content():
    return pytube.YouTube("https://www.youtube.com/watch?v=cH4E_t3m3xM")


class MockYouTube:
    def __init__(self, url):
        self.watch_html = '\\"category\\":\\"Music\\",\\"publishDate\\":\\"2017-11-18\\",\\"ownerChannelName\\":\\"SelenaGomezVEVO\\",'
        self.title = "Selena Gomez, Marshmello - Wolves"
        self.author = "SelenaGomezVEVO"
        self.length = 213
        self.watch_url = "https://youtube.com/watch?v=cH4E_t3m3xM"
        self.thumbnail_url = "https://i.ytimg.com/vi/cH4E_t3m3xM/maxresdefault.jpg"

    @property
    def streams(self):
        module_directory = os.path.dirname(__file__)
        mock_streams = os.path.join(module_directory, "data", "streams.dump")
        with open(mock_streams, "rb") as fin:
            streams_dump = pickle.load(fin)
        return streams_dump


@pytest.fixture(scope="module")
def mock_content():
    return MockYouTube("https://www.youtube.com/watch?v=cH4E_t3m3xM")


@pytest.fixture(scope="module")
def expect_formatted_streams():
        return [
            {"bitrate": 160, "download_url": None, "encoding": "opus", "filesize": 3614184},
            {"bitrate": 128, "download_url": None, "encoding": "mp4a.40.2", "filesize": 3444850},
            {"bitrate": 70, "download_url": None, "encoding": "opus", "filesize": 1847626},
            {"bitrate": 50, "download_url": None, "encoding": "opus", "filesize": 1407962}
        ]


class TestYouTubeStreams:
    @pytest.mark.network
    def test_streams(self, content, expect_formatted_streams):
        formatted_streams = YouTubeStreams(content.streams)
        for index in range(len(formatted_streams.all)):
            assert isinstance(formatted_streams.all[index]["download_url"], str)
            formatted_streams.all[index]["download_url"] = None

        assert formatted_streams.all == expect_formatted_streams

    # @pytest.mark.mock
    def test_mock_streams(self, mock_content, expect_formatted_streams):
        self.test_streams(mock_content, expect_formatted_streams)

    @pytest.mark.network
    def test_getbest(self, content):
        formatted_streams = YouTubeStreams(content.streams)
        best_stream = formatted_streams.getbest()
        best_stream["download_url"] = None
        assert best_stream == {
            "bitrate": 160,
            "download_url": None,
            "encoding": "opus",
            "filesize": 3614184
        }

    # @pytest.mark.mock
    def test_mock_getbest(self, mock_content):
        self.test_getbest(mock_content)

    @pytest.mark.network
    def test_getworst(self, content):
        formatted_streams = YouTubeStreams(content.streams)
        worst_stream = formatted_streams.getworst()
        worst_stream["download_url"] = None
        assert worst_stream == {
            "bitrate": 50,
            "download_url": None,
            "encoding": 'opus',
            "filesize": 1407962
        }

    # @pytest.mark.mock
    def test_mock_getworst(self, mock_content):
        self.test_getworst(mock_content)


class TestProviderYouTube:
    @pytest.fixture(scope="module")
    def youtube_provider(self):
        return ProviderYouTube()

    class MockYouTubeSearch:
        watch_urls = []
        def search(self, query):
            return self.watch_urls

    @pytest.mark.network
    def test_from_query(self, track, youtube_provider):
        metadata = youtube_provider.from_query(track)
        assert isinstance(metadata["streams"], YouTubeStreams)

        metadata["streams"] = []
        assert metadata == {
          'album': {'artists': [{'name': None}],
                    'images': [{'url': 'https://i.ytimg.com/vi/cH4E_t3m3xM/maxresdefault.jpg'}],
                    'name': None},
          'artists': [{'name': 'SelenaGomezVEVO'}],
          'copyright': None,
          'disc_number': 1,
          'duration': 213,
          'external_ids': {'isrc': None},
          'external_urls': {'youtube': 'https://youtube.com/watch?v=cH4E_t3m3xM'},
          'genre': None,
          'lyrics': None,
          'name': 'Selena Gomez, Marshmello - Wolves',
          'provider': 'youtube',
          'publisher': None,
          'release_date': '2017-11-1',
          'streams': [],
          'total_tracks': 1,
          'track_number': 1,
          'type': 'track',
          'year': '2017'
       }

    def test_mock_from_query(self, track, youtube_provider, expect_mock_search_results, monkeypatch):
        self.MockYouTubeSearch.watch_urls = expect_mock_search_results
        monkeypatch.setattr(youtube, "YouTubeSearch", self.MockYouTubeSearch)
        monkeypatch.setattr(pytube, "YouTube", MockYouTube)
        self.test_from_query(track, youtube_provider)

    @pytest.mark.network
    def test_error_exception_from_query(self, no_result_track, youtube_provider):
        with pytest.raises(YouTubeMetadataNotFoundError):
            youtube_provider.from_query(no_result_track)

    def test_mock_error_exception_from_query(self, no_result_track, youtube_provider, monkeypatch):
        self.MockYouTubeSearch.watch_urls = []
        monkeypatch.setattr(youtube, "YouTubeSearch", self.MockYouTubeSearch)
        monkeypatch.setattr(pytube, "YouTube", MockYouTube)
        self.test_error_exception_from_query(no_result_track, youtube_provider)

