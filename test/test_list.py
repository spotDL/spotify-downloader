import builtins
import os

from spotdl import spotify_tools
from spotdl import const
from spotdl import spotdl

import loader


USERNAME = "uqlakumu7wslkoen46s5bulq0"
PLAYLIST_URL = "https://open.spotify.com/playlist/0fWBMhGh38y0wsYWwmM9Kt"
ALBUM_URL = "https://open.spotify.com/album/499J8bIsEnU7DSrosFDJJg"
ARTIST_URL = "https://open.spotify.com/artist/4dpARuHxo51G3z768sgnrY"

loader.load_defaults()


def test_trim():
    with open(text_file, "r") as track_file:
        tracks = track_file.readlines()

    expect_number = len(tracks) - 1
    expect_track = tracks[0]
    track = spotdl.internals.trim_song(text_file)

    with open(text_file, "r") as track_file:
        number = len(track_file.readlines())

    assert expect_number == number and expect_track == track
