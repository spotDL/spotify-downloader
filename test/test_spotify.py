# -*- coding: UTF-8 -*-

from spotdl import const
from spotdl import handle
import spotdl

import os

const.args = handle.get_arguments(to_group=False, raw_args='')
const.args.folder = 'test'
const.args.overwrite = 'skip'
const.args.log_level = handle.logging.DEBUG

spotdl.args = const.args
spotdl.log = const.logzero.setup_logger(formatter=const.formatter,
                                  level=const.args.log_level)


raw_song = 'http://open.spotify.com/track/0JlS7BXXD07hRmevDnbPDU'

def test_spotify_title():
    expect_title = 'David André Østby - Intro'
    global meta_tags
    meta_tags = spotdl.spotify_tools.generate_metadata(raw_song)
    title = spotdl.internals.generate_songname(meta_tags)
    assert title == expect_title


def test_youtube_url():
    expect_url = 'http://youtube.com/watch?v=rg1wfcty0BA'
    url = spotdl.youtube_tools.generate_youtube_url(raw_song, meta_tags)
    assert url == expect_url


def test_youtube_title():
    expect_title = 'Intro - David André Østby'
    content = spotdl.youtube_tools.go_pafy(raw_song, meta_tags)
    title = spotdl.youtube_tools.get_youtube_title(content)
    assert title == expect_title


def test_check_exists():
    expect_check = False
    # prerequisites for determining filename
    songname = spotdl.internals.generate_songname(meta_tags)
    global file_name
    file_name = spotdl.internals.sanitize_title(songname)
    check = spotdl.check_exists(file_name, raw_song, meta_tags)
    assert check == expect_check


def test_download():
    expect_download = True
    # prerequisites for determining filename
    content = spotdl.youtube_tools.go_pafy(raw_song, meta_tags)
    download = spotdl.youtube_tools.download_song(file_name, content)
    assert download == expect_download


def test_convert():
    # exit code 0 = success
    expect_convert = 0
    # prerequisites for determining filename
    global input_song
    global output_song
    input_song = file_name + spotdl.args.input_ext
    output_song = file_name + spotdl.args.output_ext
    convert = spotdl.convert.song(input_song, output_song, spotdl.args.folder)
    assert convert == expect_convert


def test_metadata():
    expect_metadata = True
    # prerequisites for determining filename
    metadata_output = spotdl.metadata.embed(os.path.join(spotdl.args.folder, output_song), meta_tags)
    metadata_input = spotdl.metadata.embed(os.path.join(spotdl.args.folder, input_song), meta_tags)
    assert metadata_output == (metadata_input == expect_metadata)


def test_check_exists2():
    expect_check = True
    # prerequisites for determining filename
    os.remove(os.path.join(spotdl.args.folder, input_song))
    check = spotdl.check_exists(file_name, raw_song, meta_tags)
    os.remove(os.path.join(spotdl.args.folder, output_song))
    assert check == expect_check
