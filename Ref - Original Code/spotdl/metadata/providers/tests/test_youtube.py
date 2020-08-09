from spotdl.metadata.providers.youtube import YouTubeSearch
from spotdl.metadata.providers.youtube import YouTubeStreams
from spotdl.metadata.providers.youtube import YouTubeVideos
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
    """
    This query is to be searched on YouTube for queries
    that do return search results.
    """
    return "selena gomez wolves"


@pytest.fixture(scope="module")
def no_result_track():
    """
    This query is to be searched on YouTube for queries
    that return no search results.
    """
    return "n0 v1d305 3x157 f0r 7h15 53arc4 qu3ry"


@pytest.fixture(scope="module")
def expect_search_results():
    """
    These are the expected search results for the "track"
    query.
    """
    return YouTubeVideos([
        {'duration': '3:33',
         'title': 'Selena Gomez, Marshmello - Wolves',
         'url': 'https://www.youtube.com/watch?v=cH4E_t3m3xM'},
        {'duration': '3:18',
         'title': 'Selena Gomez, Marshmello - Wolves (Lyrics)',
         'url': 'https://www.youtube.com/watch?v=xrbY9gDVms0'},
        {'duration': '3:21',
         'title': 'Wolves - Selena Gomez, Marshmello (Lyrics)',
         'url': 'https://www.youtube.com/watch?v=jX0n2rSmDbE'},
        {'duration': '6:26',
         'title': 'Selena Gomez and Marshmello - Wolves (Official) Extended',
         'url': 'https://www.youtube.com/watch?v=rQ6jcpwzQZU'},
        {'duration': '3:43',
         'title': 'Selena Gomez, Marshmello - Wolves (Vertical Video)',
         'url': 'https://www.youtube.com/watch?v=nVzA1uWTydQ'},
        {'duration': '3:18',
         'title': 'Selena Gomez, Marshmello - Wolves (Visualizer)',
         'url': 'https://www.youtube.com/watch?v=-grLLLTza6k'},
        {'duration': '1:32',
         'title': 'Wolves - Selena Gomez, Marshmello / Jun Liu Choreography',
         'url': 'https://www.youtube.com/watch?v=zbWsb36U0uo'},
        {'duration': '3:17',
         'title': 'Selena Gomez, Marshmello - Wolves (Lyrics)',
         'url': 'https://www.youtube.com/watch?v=rykH1BkGwTo'},
        {'duration': '3:16',
         'title': 'Selena Gomez, Marshmello - Wolves (8D AUDIO)',
         'url': 'https://www.youtube.com/watch?v=j0AxZ4V5WQw'},
        {'duration': '3:47',
         'title': 'Selena Gomez, Marshmello - Wolves (Vanrip Remix)',
         'url': 'https://www.youtube.com/watch?v=RyxsaKfu-ZY'}
    ])


@pytest.fixture(scope="module")
def expect_mock_search_results():
    """
    These are the expected mock search results for the
    "track" query.
    """
    return YouTubeVideos([
        {'duration': '3:33',
         'title': 'Selena Gomez, Marshmello - Wolves',
         'url': 'https://www.youtube.com/watch?v=cH4E_t3m3xM'},
        {'duration': '3:18',
         'title': 'Selena Gomez, Marshmello - Wolves (Lyrics)',
         'url': 'https://www.youtube.com/watch?v=xrbY9gDVms0'},
        {'duration': '3:21',
         'title': 'Wolves - Selena Gomez, Marshmello (Lyrics)',
         'url': 'https://www.youtube.com/watch?v=jX0n2rSmDbE'},
        {'duration': '6:26',
         'title': 'Selena Gomez and Marshmello - Wolves (Official) Extended',
         'url': 'https://www.youtube.com/watch?v=rQ6jcpwzQZU'},
        {'duration': '3:43',
         'title': 'Selena Gomez, Marshmello - Wolves (Vertical Video)',
         'url': 'https://www.youtube.com/watch?v=nVzA1uWTydQ'},
        {'duration': '3:18',
         'title': 'Selena Gomez, Marshmello - Wolves (Visualizer)',
         'url': 'https://www.youtube.com/watch?v=-grLLLTza6k'},
        {'duration': '1:32',
         'title': 'Wolves - Selena Gomez, Marshmello / Jun Liu Choreography',
         'url': 'https://www.youtube.com/watch?v=zbWsb36U0uo'},
        {'duration': '3:17',
         'title': 'Selena Gomez, Marshmello - Wolves (Lyrics)',
         'url': 'https://www.youtube.com/watch?v=rykH1BkGwTo'},
        {'duration': '3:16',
         'title': 'Selena Gomez, Marshmello - Wolves (8D AUDIO)',
         'url': 'https://www.youtube.com/watch?v=j0AxZ4V5WQw'},
        {'duration': '3:47',
         'title': 'Selena Gomez, Marshmello - Wolves (Vanrip Remix)',
         'url': 'https://www.youtube.com/watch?v=RyxsaKfu-ZY'}
    ])


class MockHTTPResponse:
    """
    This mocks `urllib.request.urlopen` for custom response text.
    """
    response_file = ""

    def __init__(self, request):
        if isinstance(request, urllib.request.Request):
            if request._full_url.endswith("ouVRL5arzUg=="):
                self.headers = {"Content-Length": 3614184}
            elif request._full_url.endswith("egl0iK2D-Bk="):
                self.headers = {"Content-Length": 3444850}
            elif request._full_url.endswith("J7VXJtoi3as="):
                self.headers = {"Content-Length": 1847626}
            elif request._full_url.endswith("_d5_ZthQdvtD"):
                self.headers = {"Content-Length": 1407962}

    def read(self):
        module_directory = os.path.dirname(__file__)
        mock_html = os.path.join(module_directory, "data", self.response_file)
        with open(mock_html, "r") as fin:
            html = fin.read()
        return html


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
        """
        This mocks `urllib.request.urlopen` for custom response text.
        """
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
        MockHTTPResponse.response_file = "youtube_search_results.html.test"
        monkeypatch.setattr(urllib.request, "urlopen", MockHTTPResponse)
        self.test_search(track, youtube_searcher, expect_mock_search_results)

    @pytest.mark.network
    def test_no_videos_search(self, no_result_track, youtube_searcher):
        results = youtube_searcher.search(no_result_track)
        assert results == YouTubeVideos([])

    def test_mock_no_videos_search(self, no_result_track, youtube_searcher, monkeypatch):
        MockHTTPResponse.response_file = "youtube_no_search_results.html.test"
        monkeypatch.setattr(urllib.request, "urlopen", MockHTTPResponse)
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
        # For updating the test data:
        # from spotdl.metadata.providers.youtube import YouTubeStreams
        # import pytube
        # import pickle
        # content = pytube.YouTube("https://youtube.com/watch?v=cH4E_t3m3xM")
        # with open("streams.dump", "wb") as fout:
        #       pickle.dump(content.streams, fout)
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
    """
    Expected streams for the best matching video for "track" in
    search results.

    The `download_url` is expected as `None` since it's impossible
    to predict its value before-hand.
    """
    return [
        {"bitrate": 160, "content": None, "download_url": None, "encoding": "opus", "filesize": 3614184},
        {"bitrate": 128, "content": None, "download_url": None, "encoding": "mp4a.40.2", "filesize": 3444850},
        {"bitrate": 70, "content": None, "download_url": None, "encoding": "opus", "filesize": 1847626},
        {"bitrate": 50, "content": None, "download_url": None, "encoding": "opus", "filesize": 1407962}
    ]


class TestYouTubeStreams:
    @pytest.mark.network
    def test_streams(self, content, expect_formatted_streams):
        formatted_streams = YouTubeStreams(content.streams)
        for index in range(len(formatted_streams.streams)):
            assert isinstance(formatted_streams.streams[index]["download_url"], str)
            assert formatted_streams.streams[index]["connection"] is not None
            # We `None` the `download_url` since it's impossible to
            # predict its value before-hand.
            formatted_streams.streams[index]["download_url"] = None
            formatted_streams.streams[index]["connection"] = None

        # assert formatted_streams.streams == expect_formatted_streams
        for f, e in zip(formatted_streams.streams, expect_formatted_streams):
            assert f["filesize"] == e["filesize"]

    # @pytest.mark.mock
    def test_mock_streams(self, mock_content, expect_formatted_streams, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen", MockHTTPResponse)
        self.test_streams(mock_content, expect_formatted_streams)

    @pytest.mark.network
    def test_getbest(self, content):
        formatted_streams = YouTubeStreams(content.streams)
        best_stream = formatted_streams.getbest()
        assert isinstance(best_stream["download_url"], str)
        assert best_stream["connection"] is not None
        # We `None` the `download_url` since it's impossible to
        # predict its value before-hand.
        best_stream["download_url"] = None
        best_stream["connection"] = None
        assert best_stream == {
            "bitrate": 160,
            "connection": None,
            "download_url": None,
            "encoding": "opus",
            "filesize": 3614184
        }

    # @pytest.mark.mock
    def test_mock_getbest(self, mock_content, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen", MockHTTPResponse)
        self.test_getbest(mock_content)

    @pytest.mark.network
    def test_getworst(self, content):
        formatted_streams = YouTubeStreams(content.streams)
        worst_stream = formatted_streams.getworst()
        assert isinstance(worst_stream["download_url"], str)
        assert worst_stream["connection"] is not None
        # We `None` the `download_url` since it's impossible to
        # predict its value before-hand.
        worst_stream["download_url"] = None
        worst_stream["connection"] = None
        assert worst_stream == {
            "bitrate": 50,
            "connection": None,
            "download_url": None,
            "encoding": 'opus',
            "filesize": 1407962
        }

    # @pytest.mark.mock
    def test_mock_getworst(self, mock_content, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen", MockHTTPResponse)
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
        # We avoid testing each item for the `streams` key here
        # again. It this has already been tested above.
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
        monkeypatch.setattr(urllib.request, "urlopen", MockHTTPResponse)
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

