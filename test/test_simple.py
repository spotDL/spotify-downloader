# -*- coding: UTF-8 -*-

from spotdl import logger
import spotdl
import os

raw_song = "Tony's Videos VERY SHORT VIDEO 28.10.2016"


class TestArgs:
    manual = False
    input_ext = '.m4a'
    output_ext = '.mp3'
    folder = 'test'
    log_level = logger.logging.DEBUG

test_args = TestArgs()
setattr(spotdl, "args", test_args)

spotdl.log = logger.logzero.setup_logger(formatter=logger.formatter,
                                  level=spotdl.args.log_level)


def test_youtube_url():
    expect_url = 'http://youtube.com/watch?v=qOOcy2-tmbk'
    url = spotdl.generate_youtube_url(raw_song, meta_tags=None)
    assert url == expect_url


def test_youtube_title():
    global content
    global title
    expect_title = "Tony's Videos VERY SHORT VIDEO 28.10.2016"
    content = spotdl.go_pafy(raw_song, meta_tags=None)
    title = spotdl.get_youtube_title(content)
    assert title == expect_title

def test_check_exists():
    expect_check = False
    # prerequisites for determining filename
    file_name = spotdl.internals.sanitize_title(title)
    check = spotdl.check_exists(file_name, raw_song, meta_tags=None, islist=True)
    assert check == expect_check


def test_download():
    expect_download = True
    # prerequisites for determining filename
    file_name = spotdl.internals.sanitize_title(title)
    download = spotdl.download_song(file_name, content)
    assert download == expect_download


def test_convert():
    # exit code 0 = success
    expect_convert = 0
    # prerequisites for determining filename
    file_name = spotdl.internals.sanitize_title(title)
    global input_song
    global output_song
    input_song = file_name + spotdl.args.input_ext
    output_song = file_name + spotdl.args.output_ext
    convert = spotdl.convert.song(input_song, output_song, spotdl.args.folder)
    assert convert == expect_convert


def test_metadata():
    expect_metadata = None
    # prerequisites for determining filename
    meta_tags = spotdl.generate_metadata(raw_song)
    file_name = spotdl.internals.sanitize_title(title)
    metadata_output = spotdl.metadata.embed(os.path.join(spotdl.args.folder, output_song), meta_tags)
    metadata_input = spotdl.metadata.embed(os.path.join(spotdl.args.folder, input_song), meta_tags)
    assert (metadata_output == expect_metadata) and (metadata_input == expect_metadata)


def test_check_exists2():
    expect_check = True
    # prerequisites for determining filename
    file_name = spotdl.internals.sanitize_title(title)
    os.remove(os.path.join(spotdl.args.folder, input_song))
    check = spotdl.check_exists(file_name, raw_song, meta_tags=None, islist=True)
    os.remove(os.path.join(spotdl.args.folder, output_song))
    assert check == expect_check
