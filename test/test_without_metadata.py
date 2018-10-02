import os
import builtins

from spotdl import const
from spotdl import internals
from spotdl import spotify_tools
from spotdl import youtube_tools
from spotdl import spotdl

import loader

loader.load_defaults()

YT_API_KEY = 'AIzaSyAnItl3udec-Q1d5bkjKJGL-RgrKO_vU90'

TRACK_SEARCH = "Tony's Videos VERY SHORT VIDEO 28.10.2016"
EXPECTED_TITLE = TRACK_SEARCH
EXPECTED_YT_URL = 'http://youtube.com/watch?v=qOOcy2-tmbk'
EXPECTED_YT_URLS = (EXPECTED_YT_URL, 'http://youtube.com/watch?v=5USR1Omo7f0')

RESULT_COUNT_SEARCH = "she is still sleeping SAO"

EXPECTED_YT_API_KEY = 'AIzaSyC6cEeKlxtOPybk9sEe5ksFN5sB-7wzYp0'
EXPECTED_YT_API_KEY_CUSTOM = 'some_api_key'


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


def test_metadata():
    expect_metadata = None
    global metadata
    metadata = spotify_tools.generate_metadata(TRACK_SEARCH)
    assert metadata == expect_metadata


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
    def test_only_music_category(self):
        const.args.music_videos_only = True
        url = youtube_tools.generate_youtube_url(TRACK_SEARCH, metadata)
        # YouTube keeps changing its results
        assert url in EXPECTED_YT_URLS

    def test_all_categories(self):
        const.args.music_videos_only = False
        url = youtube_tools.generate_youtube_url(TRACK_SEARCH, metadata)
        assert url == EXPECTED_YT_URL

    def test_args_manual(self, monkeypatch):
        const.args.manual = True
        monkeypatch.setattr('builtins.input', lambda x: '1')
        url = youtube_tools.generate_youtube_url(TRACK_SEARCH, metadata)
        assert url == EXPECTED_YT_URL

    def test_args_manual_none(self, monkeypatch):
        expect_url = None
        monkeypatch.setattr('builtins.input', lambda x: '0')
        url = youtube_tools.generate_youtube_url(TRACK_SEARCH, metadata)
        const.args.manual = False
        assert url == expect_url


class TestYouTubeTitle:
    def test_single_download_with_youtube_api(self):
        global content
        global title
        const.args.youtube_api_key = YT_API_KEY
        youtube_tools.set_api_key()
        content = youtube_tools.go_pafy(TRACK_SEARCH, metadata)
        title = youtube_tools.get_youtube_title(content)
        assert title == EXPECTED_TITLE

    def test_download_from_list_without_youtube_api(self):
        const.args.youtube_api_key = None
        youtube_tools.set_api_key()
        content = youtube_tools.go_pafy(TRACK_SEARCH, metadata)
        title = youtube_tools.get_youtube_title(content, 1)
        assert title == "1. {0}".format(EXPECTED_TITLE)


def test_check_exists(tmpdir):
    expect_check = False
    const.args.folder = str(tmpdir)
    # prerequisites for determining filename
    global file_name
    file_name = internals.sanitize_title(title)
    check = spotdl.check_exists(file_name, TRACK_SEARCH, metadata)
    assert check == expect_check


class TestDownload:
    def test_webm(self):
        # content does not have any .webm audiostream
        expect_download = False
        download = youtube_tools.download_song(file_name + '.webm', content)
        assert download == expect_download

    def test_other(self):
        expect_download = False
        download = youtube_tools.download_song(file_name + '.fake_extension', content)
        assert download == expect_download
