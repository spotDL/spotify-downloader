# -*- coding: UTF-8 -*-

import spotdl

raw_song = "http://open.spotify.com/track/2e0jnySVkYF1pvBlpoNX1Y"

def test_spotify():
    expected_title = "David André Østby - Tilbake (SAEVIK Remix)"
    title = spotdl.generate_songname(raw_song)
    assert title == expected_title

def test_youtube_title():
    expected_url = "youtube.com/watch?v=zkD4smbefbc"
    url = spotdl.generate_youtube_url(raw_song)
    assert url == expected_url
