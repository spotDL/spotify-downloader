
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

loader.load_defaults()
internals.filter_path(const.args.folder)
raw_song = 'http://open.spotify.com/track/0JlS7BXXD07hRmevDnbPDU'

def test_spotify_title():
    expect_title = 'David André Østby - Intro'
    global meta_tags
    meta_tags = spotify_tools.generate_metadata(raw_song)
    title = internals.generate_songname(const.args.file_format, meta_tags)
    assert title == expect_title


def test_youtube_url():
    expect_url = 'http://youtube.com/watch?v=rg1wfcty0BA'
    url = youtube_tools.generate_youtube_url(raw_song, meta_tags)
    assert url == expect_url


def test_youtube_title():
    expect_title = 'Intro - David André Østby'
    content = youtube_tools.go_pafy(raw_song, meta_tags)
    title = youtube_tools.get_youtube_title(content)
    assert title == expect_title


def test_check_exists():
    expect_check = False
    # prerequisites for determining filename
    songname = internals.generate_songname(const.args.file_format, meta_tags)
    global file_name
    file_name = internals.sanitize_title(songname)
    check = spotdl.check_exists(file_name, raw_song, meta_tags)
    assert check == expect_check


def test_download():
    expect_download = True
    # prerequisites for determining filename
    content = youtube_tools.go_pafy(raw_song, meta_tags)
    download = youtube_tools.download_song(file_name, content)
    assert download == expect_download


def test_convert():
    # exit code 0 = success
    expect_converted = 0
    # prerequisites for determining filename
    global input_song
    global output_song
    input_song = file_name + const.args.input_ext
    output_song = file_name + const.args.output_ext
    converted = convert.song(input_song, output_song, const.args.folder)
    assert converted == expect_converted


def test_metadata():
    expect_metadata = True
    # prerequisites for determining filename
    metadata_output = metadata.embed(os.path.join(const.args.folder, output_song), meta_tags)
    metadata_input = metadata.embed(os.path.join(const.args.folder, input_song), meta_tags)
    assert metadata_output == (metadata_input == expect_metadata)


def test_check_exists2():
    expect_check = True
    # prerequisites for determining filename
    os.remove(os.path.join(const.args.folder, input_song))
    check = spotdl.check_exists(file_name, raw_song, meta_tags)
    os.remove(os.path.join(const.args.folder, output_song))
    assert check == expect_check
