
from core import const
from core import internals
from core import spotify_tools
from core import youtube_tools
from core import convert
from core import metadata

import spotdl

import loader
import os

loader.load_defaults()
raw_song = 'http://open.spotify.com/track/0JlS7BXXD07hRmevDnbPDU'


def test_metadata():
    expect_number = 22
    global meta_tags
    meta_tags = spotify_tools.generate_metadata(raw_song)
    assert len(meta_tags) == expect_number


class TestFileFormat:
    def test_with_spaces(self):
        expect_title = 'David André Østby - Intro'
        title = internals.generate_songname(const.args.file_format, meta_tags)
        assert title == expect_title

    def test_without_spaces(self):
        expect_title = 'David_André_Østby_-_Intro'
        const.args.no_spaces = True
        title = internals.generate_songname(const.args.file_format, meta_tags)
        assert title == expect_title


def test_youtube_url():
    expect_url = 'http://youtube.com/watch?v=rg1wfcty0BA'
    url = youtube_tools.generate_youtube_url(raw_song, meta_tags)
    assert url == expect_url


def test_youtube_title():
    expect_title = 'Intro - David André Østby'
    global content
    content = youtube_tools.go_pafy(raw_song, meta_tags)
    title = youtube_tools.get_youtube_title(content)
    assert title == expect_title


def test_check_exists(tmpdir):
    expect_check = False
    const.args.folder = str(tmpdir)
    # prerequisites for determining filename
    songname = internals.generate_songname(const.args.file_format, meta_tags)
    global file_name
    file_name = internals.sanitize_title(songname)
    check = spotdl.check_exists(file_name, raw_song, meta_tags)
    assert check == expect_check


class TestDownload:
    def test_m4a(self):
        expect_download = True
        download = youtube_tools.download_song(file_name + '.m4a', content)
        assert download == expect_download

    def test_webm(self):
        expect_download = True
        download = youtube_tools.download_song(file_name + '.webm', content)
        assert download == expect_download


class TestFFmpeg():
    def test_convert_from_webm_to_mp3(self):
        expect_return_code = 0
        return_code = convert.song(file_name + '.webm',
                                   file_name + '.mp3',
                                   const.args.folder)
        assert return_code == expect_return_code

    def test_convert_from_webm_to_m4a(self):
        expect_return_code = 0
        return_code = convert.song(file_name + '.webm',
                                   file_name + '.m4a',
                                   const.args.folder)
        assert return_code == expect_return_code


    def test_convert_from_m4a_to_mp3(self):
        expect_return_code = 0
        return_code = convert.song(file_name + '.m4a',
                                   file_name + '.mp3',
                                   const.args.folder)
        assert return_code == expect_return_code

    def test_convert_from_m4a_to_webm(self):
        expect_return_code = 0
        return_code = convert.song(file_name + '.m4a',
                                   file_name + '.webm',
                                   const.args.folder)
        os.remove(os.path.join(const.args.folder, file_name + '.webm'))
        assert return_code == expect_return_code


class TestAvconv:
    def test_convert_from_m4a_to_mp3(self):
        expect_return_code = 0
        return_code = convert.song(file_name + '.m4a',
                                   file_name + '.mp3',
                                   const.args.folder,
                                   avconv=True)
        assert return_code == expect_return_code


def test_embed_metadata():
    expect_metadata = True
    # prerequisites for determining filename
    metadata_input = metadata.embed(os.path.join(const.args.folder,
                                                 file_name + '.m4a'), meta_tags)
    metadata_output = metadata.embed(os.path.join(const.args.folder,
                                                  file_name + '.mp3'), meta_tags)
    assert metadata_output == (metadata_input == expect_metadata)


def test_check_exists2():
    expect_check = True
    # prerequisites for determining filename
    os.remove(os.path.join(const.args.folder, file_name + '.m4a'))
    check = spotdl.check_exists(file_name, raw_song, meta_tags)
    os.remove(os.path.join(const.args.folder, file_name + '.mp3'))
    assert check == expect_check
