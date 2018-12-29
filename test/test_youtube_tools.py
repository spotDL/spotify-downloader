import os
import builtins

from spotdl import const
from spotdl import internals
from spotdl import spotify_tools
from spotdl import youtube_tools
from spotdl import downloader

import loader
import pytest

loader.load_defaults()

YT_API_KEY = "AIzaSyAnItl3udec-Q1d5bkjKJGL-RgrKO_vU90"

TRACK_SEARCH = "Tony's Videos VERY SHORT VIDEO 28.10.2016"
EXPECTED_TITLE = TRACK_SEARCH
EXPECTED_YT_URL = "http://youtube.com/watch?v=qOOcy2-tmbk"
EXPECTED_YT_URLS = (EXPECTED_YT_URL, "http://youtube.com/watch?v=5USR1Omo7f0")

RESULT_COUNT_SEARCH = "she is still sleeping SAO"

EXPECTED_YT_API_KEY = "AIzaSyC6cEeKlxtOPybk9sEe5ksFN5sB-7wzYp0"
EXPECTED_YT_API_KEY_CUSTOM = "some_api_key"


class TestYouTubeAPIKeys:
    def test_custom(self):
        const.args.youtube_api_key = EXPECTED_YT_API_KEY_CUSTOM
        youtube_tools.set_api_key()
        key = youtube_tools.pafy.g.api_key
        assert key == EXPECTED_YT_API_KEY_CUSTOM

    def test_default(self):
        const.args.youtube_api_key = None
        youtube_tools.set_api_key()
        key = youtube_tools.pafy.g.api_key
        assert key == EXPECTED_YT_API_KEY


@pytest.fixture(scope="module")
def metadata_fixture():
    metadata = spotify_tools.generate_metadata(TRACK_SEARCH)
    return metadata


def test_metadata(metadata_fixture):
    expect_metadata = None
    assert metadata_fixture == expect_metadata


class TestArgsManualResultCount:
    # Regresson test for issue #264
    def test_scrape(self):
        const.args.manual = True
        url = youtube_tools.GenerateYouTubeURL(RESULT_COUNT_SEARCH, meta_tags=None)
        video_ids = url.scrape(bestmatch=False)
        # Web scraping gives us all videos on the 1st page
        assert len(video_ids) == 20

    def test_api(self):
        url = youtube_tools.GenerateYouTubeURL(RESULT_COUNT_SEARCH, meta_tags=None)
        video_ids = url.api(bestmatch=False)
        const.args.manual = False
        # API gives us 50 videos (or as requested)
        assert len(video_ids) == 50


class TestYouTubeURL:
    def test_only_music_category(self, metadata_fixture):
        const.args.music_videos_only = True
        url = youtube_tools.generate_youtube_url(TRACK_SEARCH, metadata_fixture)
        # YouTube keeps changing its results
        assert url in EXPECTED_YT_URLS

    def test_all_categories(self, metadata_fixture):
        const.args.music_videos_only = False
        url = youtube_tools.generate_youtube_url(TRACK_SEARCH, metadata_fixture)
        assert url == EXPECTED_YT_URL

    def test_args_manual(self, metadata_fixture, monkeypatch):
        const.args.manual = True
        monkeypatch.setattr("builtins.input", lambda x: "1")
        url = youtube_tools.generate_youtube_url(TRACK_SEARCH, metadata_fixture)
        assert url == EXPECTED_YT_URL

    def test_args_manual_none(self, metadata_fixture, monkeypatch):
        expect_url = None
        monkeypatch.setattr("builtins.input", lambda x: "0")
        url = youtube_tools.generate_youtube_url(TRACK_SEARCH, metadata_fixture)
        const.args.manual = False
        assert url == expect_url


@pytest.fixture(scope="module")
def content_fixture(metadata_fixture):
    content = youtube_tools.go_pafy(TRACK_SEARCH, metadata_fixture)
    return content


@pytest.fixture(scope="module")
def title_fixture(content_fixture):
    title = youtube_tools.get_youtube_title(content_fixture)
    return title


class TestYouTubeTitle:
    def test_single_download_with_youtube_api(self, title_fixture):
        const.args.youtube_api_key = YT_API_KEY
        youtube_tools.set_api_key()
        assert title_fixture == EXPECTED_TITLE

    def test_download_from_list_without_youtube_api(
        self, metadata_fixture, content_fixture
    ):
        const.args.youtube_api_key = None
        youtube_tools.set_api_key()
        content_fixture = youtube_tools.go_pafy(TRACK_SEARCH, metadata_fixture)
        title = youtube_tools.get_youtube_title(content_fixture, 1)
        assert title == "1. {0}".format(EXPECTED_TITLE)


@pytest.fixture(scope="module")
def filename_fixture(title_fixture):
    filename = internals.sanitize_title(title_fixture)
    return filename


def test_check_exists(metadata_fixture, filename_fixture, tmpdir):
    expect_check = False
    const.args.folder = str(tmpdir)
    # prerequisites for determining filename
    track_existence = downloader.CheckExists(filename_fixture, metadata_fixture)
    check = track_existence.already_exists(TRACK_SEARCH)
    assert check == expect_check


class TestDownload:
    def test_webm(self, content_fixture, filename_fixture, monkeypatch):
        # content_fixture does not have any .webm audiostream
        expect_download = False
        monkeypatch.setattr("pafy.backend_shared.BaseStream.download", lambda x: None)
        download = youtube_tools.download_song(
            filename_fixture + ".webm", content_fixture
        )
        assert download == expect_download

    def test_other(self, content_fixture, filename_fixture, monkeypatch):
        expect_download = False
        monkeypatch.setattr("pafy.backend_shared.BaseStream.download", lambda x: None)
        download = youtube_tools.download_song(
            filename_fixture + ".fake_extension", content_fixture
        )
        assert download == expect_download
