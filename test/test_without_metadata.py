from core import const
from core import internals
from core import spotify_tools
from core import youtube_tools

import spotdl
import loader

import os
import builtins

loader.load_defaults()
raw_song = "Tony's Videos VERY SHORT VIDEO 28.10.2016"


class TestYouTubeAPIKeys:
    def test_custom(self):
        expect_key = 'some_api_key'
        const.args.youtube_api_key = expect_key
        youtube_tools.set_api_key()
        key = youtube_tools.pafy.g.api_key
        assert key == expect_key

    def test_default(self):
        expect_key = 'AIzaSyC6cEeKlxtOPybk9sEe5ksFN5sB-7wzYp0'
        const.args.youtube_api_key = None
        youtube_tools.set_api_key()
        key = youtube_tools.pafy.g.api_key
        assert key == expect_key


def test_metadata():
    expect_metadata = None
    global metadata
    metadata = spotify_tools.generate_metadata(raw_song)
    assert metadata == expect_metadata


class TestYouTubeURL:
    def test_only_music_category(self):
        # YouTube keeps changing its results
        expect_urls = ('http://youtube.com/watch?v=qOOcy2-tmbk',
                       'http://youtube.com/watch?v=5USR1Omo7f0')
        const.args.music_videos_only = True
        url = youtube_tools.generate_youtube_url(raw_song, metadata)
        assert url in expect_urls

    def test_all_categories(self):
        expect_url = 'http://youtube.com/watch?v=qOOcy2-tmbk'
        const.args.music_videos_only = False
        url = youtube_tools.generate_youtube_url(raw_song, metadata)
        assert url == expect_url

    def test_args_manual(self, monkeypatch):
        expect_url = 'http://youtube.com/watch?v=qOOcy2-tmbk'
        const.args.manual = True
        monkeypatch.setattr('builtins.input', lambda x: '1')
        url = youtube_tools.generate_youtube_url(raw_song, metadata)
        assert url == expect_url

    def test_args_manual_none(self, monkeypatch):
        expect_url = None
        monkeypatch.setattr('builtins.input', lambda x: '0')
        url = youtube_tools.generate_youtube_url(raw_song, metadata)
        const.args.manual = False
        assert url == expect_url


class TestYouTubeTitle:
    def test_single_download_with_youtube_api(self):
        global content
        global title
        expect_title = "Tony's Videos VERY SHORT VIDEO 28.10.2016"
        key = 'AIzaSyAnItl3udec-Q1d5bkjKJGL-RgrKO_vU90'
        const.args.youtube_api_key = key
        youtube_tools.set_api_key()
        content = youtube_tools.go_pafy(raw_song, metadata)
        title = youtube_tools.get_youtube_title(content)
        assert title == expect_title

    def test_download_from_list_without_youtube_api(self):
        expect_title = "1. Tony's Videos VERY SHORT VIDEO 28.10.2016"
        const.args.youtube_api_key = None
        youtube_tools.set_api_key()
        content = youtube_tools.go_pafy(raw_song, metadata)
        title = youtube_tools.get_youtube_title(content, 1)
        assert title == expect_title


def test_check_exists(tmpdir):
    expect_check = False
    const.args.folder = str(tmpdir)
    # prerequisites for determining filename
    global file_name
    file_name = internals.sanitize_title(title)
    check = spotdl.check_exists(file_name, raw_song, metadata)
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
