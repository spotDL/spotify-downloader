# -*- coding: UTF-8 -*-

import spotdl
import os

raw_song = "Tony's Videos VERY SHORT VIDEO 28.10.2016"

for x in os.listdir(spotdl.args.folder):
    os.remove(os.path.join(spotdl.args.folder, x))

def test_youtube_url():
    expect_url = 'youtube.com/watch?v=qOOcy2-tmbk'
    url = spotdl.generate_youtube_url(raw_song)
    assert url == expect_url


def test_youtube_title():
    expect_title = "Tony's Videos VERY SHORT VIDEO 28.10.2016"
    global content
    content = spotdl.go_pafy(raw_song)
    global title
    title = spotdl.get_youtube_title(content)
    assert title == expect_title

def test_check_exists():
    expect_check = False
    # prerequisites for determining filename
    file_name = spotdl.misc.sanitize_title(title)
    check = spotdl.check_exists(file_name, raw_song, islist=True)
    assert check == expect_check


def test_download():
    expect_download = True
    # prerequisites for determining filename
    file_name = spotdl.misc.sanitize_title(title)
    download = spotdl.download_song(file_name, content)
    assert download == expect_download


def test_convert():
    # exit code 0 = success
    expect_convert = 0
    # prerequisites for determining filename
    file_name = spotdl.misc.sanitize_title(title)
    input_song = file_name + spotdl.args.input_ext
    output_song = file_name + spotdl.args.output_ext
    convert = spotdl.convert.song(input_song, output_song, spotdl.args.folder)
    assert convert == expect_convert


def test_metadata():
    expect_metadata = None
    # prerequisites for determining filename
    meta_tags = spotdl.generate_metadata(raw_song)
    meta_tags = spotdl.generate_metadata(raw_song)
    file_name = spotdl.misc.sanitize_title(title)
    output_song = file_name + spotdl.args.output_ext
    metadata_output = spotdl.metadata.embed(os.path.join(spotdl.args.folder, output_song), meta_tags)
    input_song = file_name + spotdl.args.input_ext
    metadata_input = spotdl.metadata.embed(os.path.join(spotdl.args.folder, input_song), meta_tags)
    assert (metadata_output == expect_metadata) and (metadata_input == expect_metadata)


def test_check_exists2():
    expect_check = True
    # prerequisites for determining filename
    file_name = spotdl.misc.sanitize_title(title)
    input_song = file_name + spotdl.args.input_ext
    os.remove(os.path.join(spotdl.args.folder, input_song))
    check = spotdl.check_exists(file_name, raw_song, islist=True)
    assert check == expect_check
