# -*- coding: UTF-8 -*-

import spotdl
import os

raw_song = 'http://open.spotify.com/track/0JlS7BXXD07hRmevDnbPDU'

for x in os.listdir(spotdl.args.folder):
    os.remove(os.path.join(spotdl.args.folder, x))


def test_spotify_title():
    expect_title = 'David André Østby - Intro'
    global meta_tags
    meta_tags = spotdl.generate_metadata(raw_song)
    title = spotdl.generate_songname(meta_tags)
    assert title == expect_title


def youtube_url():
    expect_url = 'youtube.com/watch?v=rg1wfcty0BA'
    url = spotdl.generate_youtube_url(raw_song)
    assert url == expect_url


def youtube_title():
    expect_title = 'Intro - David André Østby'
    content = spotdl.go_pafy(raw_song)
    title = spotdl.get_youtube_title(content)
    assert title == expect_title


def test_check_exists():
    expect_check = False
    # prerequisites for determining filename
    songname = spotdl.generate_songname(meta_tags)
    global file_name
    file_name = spotdl.misc.sanitize_title(songname)
    check = spotdl.check_exists(file_name, raw_song, islist=True)
    assert check == expect_check


def test_download():
    expect_download = True
    # prerequisites for determining filename
    content = spotdl.go_pafy(raw_song)
    download = spotdl.download_song(file_name, content)
    assert download == expect_download


def test_convert():
    # exit code 0 = success
    expect_convert = 0
    # prerequisites for determining filename
    input_song = file_name + spotdl.args.input_ext
    output_song = file_name + spotdl.args.output_ext
    convert = spotdl.convert.song(input_song, output_song, spotdl.args.folder)
    assert convert == expect_convert


def test_metadata():
    expect_metadata = True
    # prerequisites for determining filename
    output_song = file_name + spotdl.args.output_ext
    metadata_output = spotdl.metadata.embed(os.path.join(spotdl.args.folder, output_song), meta_tags)
    input_song = file_name + spotdl.args.input_ext
    metadata_input = spotdl.metadata.embed(os.path.join(spotdl.args.folder, input_song), meta_tags)
    assert metadata_output == (metadata_input == expect_metadata)


def test_check_exists2():
    expect_check = True
    # prerequisites for determining filename
    input_song = file_name + spotdl.args.input_ext
    os.remove(os.path.join(spotdl.args.folder, input_song))
    check = spotdl.check_exists(file_name, raw_song, islist=True)
    assert check == expect_check
