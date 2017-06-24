# -*- coding: UTF-8 -*-

import spotdl

def test_songname():
    song = "http://open.spotify.com/track/2e0jnySVkYF1pvBlpoNX1Y"
    expected_title = "David André Østby - Tilbake (SAEVIK Remix)"
    title = spotdl.generate_songname(song)
    assert title == expected_title
