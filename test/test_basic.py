# -*- coding: UTF-8 -*-

import spotdl

raw_song = 'http://open.spotify.com/track/2e0jnySVkYF1pvBlpoNX1Y'

def test_spotify_title():
    expect_title = 'David André Østby - Tilbake (SAEVIK Remix)'
    title = spotdl.generate_songname(raw_song)
    assert title == expect_title

def test_youtube_url():
    expect_url = 'youtube.com/watch?v=zkD4smbefbc'
    url = spotdl.generate_youtube_url(raw_song)
    assert url == expect_url

def test_youtube_title():
    expect_title = 'Tilbake (SAEVIK Remix) [Feat. Marie Hognestad] - David André Østby'
    content = spotdl.go_pafy(raw_song)
    title = spotdl.get_youtube_title(content)
    assert title == expect_title

def test_check_exists():
    expect_check = False
    content = spotdl.go_pafy(raw_song)
    music_file = spotdl.misc.generate_filename(content.title)
    music_file = spotdl.misc.fix_decoding(music_file)
    check = spotdl.check_exists(music_file, raw_song)
    assert check == expect_check

def test_download():
    expect_download = True
    content = spotdl.go_pafy(raw_song)
    download = spotdl.download_song(content)
    assert download == expect_download
