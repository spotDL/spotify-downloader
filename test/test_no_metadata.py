from core import const
from core import handle
from core import internals
from core import spotify_tools
from core import youtube_tools
from core import convert
from core import metadata

import spotdl
import loader

import os
import builtins

loader.load_defaults()
raw_song = "Tony's Videos VERY SHORT VIDEO 28.10.2016"


def test_metadata():
    expect_metadata = None
    global metadata
    metadata = spotify_tools.generate_metadata(raw_song)
    assert metadata == expect_metadata


class TestYouTubeURL:
    def test_only_music_category(self):
        expect_url = 'http://youtube.com/watch?v=P11ou3CXKZo'
        const.args.music_videos_only = True
        url = youtube_tools.generate_youtube_url(raw_song, metadata)
        assert url == expect_url

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


def test_youtube_title():
    global content
    global title
    expect_title = "Tony's Videos VERY SHORT VIDEO 28.10.2016"
    content = youtube_tools.go_pafy(raw_song, metadata)
    title = youtube_tools.get_youtube_title(content)
    assert title == expect_title


def test_check_exists(tmpdir):
    expect_check = False
    const.args.folder = tmpdir
    # prerequisites for determining filename
    global file_name
    file_name = internals.sanitize_title(title)
    check = spotdl.check_exists(file_name, raw_song, metadata)
    assert check == expect_check


class TestDownload:
    def test_m4a(self):
        expect_download = True
        download = youtube_tools.download_song(file_name + '.m4a', content)
        assert download == expect_download

    def test_webm(self):
        # content does not have any .webm audiostream
        expect_download = False
        download = youtube_tools.download_song(file_name + '.webm', content)
        assert download == expect_download

    def test_other(self):
        expect_download = False
        download = youtube_tools.download_song(file_name + '.fake_extension', content)
        assert download == expect_download


def test_convert():
    # exit code 0 = success
    expect_converted = 0
    global input_song
    global output_song
    input_song = file_name + const.args.input_ext
    output_song = file_name + const.args.output_ext
    ffmpeg = convert.song(input_song, output_song, const.args.folder)
    os.remove(os.path.join(const.args.folder, output_song))
    avconv = convert.song(input_song, output_song, const.args.folder, avconv=True)
    assert (ffmpeg == expect_converted) and (avconv == expect_converted)


def test_check_exists2():
    expect_check = True
    os.remove(os.path.join(const.args.folder, input_song))
    check = spotdl.check_exists(file_name, raw_song, metadata)
    os.remove(os.path.join(const.args.folder, output_song))
    assert check == expect_check
