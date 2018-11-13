import builtins
import os

from spotdl import spotify_tools
from spotdl import youtube_tools
from spotdl import const
from spotdl import spotdl

import loader


USERNAME = "uqlakumu7wslkoen46s5bulq0"
PLAYLIST_URL = "https://open.spotify.com/playlist/0fWBMhGh38y0wsYWwmM9Kt"
ALBUM_URL = "https://open.spotify.com/album/499J8bIsEnU7DSrosFDJJg"
ARTIST_URL = "https://open.spotify.com/artist/4dpARuHxo51G3z768sgnrY"

loader.load_defaults()


def test_user_playlists(tmpdir, monkeypatch):
    expect_tracks = 17
    text_file = os.path.join(str(tmpdir), "test_us.txt")
    monkeypatch.setattr("builtins.input", lambda x: 1)
    spotify_tools.write_user_playlist(USERNAME, text_file)
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


def test_playlist(tmpdir):
    expect_tracks = 14
    text_file = os.path.join(str(tmpdir), "test_pl.txt")
    spotify_tools.write_playlist(PLAYLIST_URL, text_file)
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


def test_album(tmpdir):
    expect_tracks = 15
    text_file = os.path.join(str(tmpdir), "test_al.txt")
    spotify_tools.write_album(ALBUM_URL, text_file)
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


def test_m3u(tmpdir):
    expect_m3u = (
        "#EXTM3U\n\n"
        "#EXTINF:31,Eminem - 01 - Eminem - Curtains Up (Skit)\n"
        "http://www.youtube.com/watch?v=qk13SFlwG9A\n"
        "#EXTINF:226,Alan Walker - Spectre [NCS Release]\n"
        "http://www.youtube.com/watch?v=AOeY-nDp7hI\n"
    )
    m3u_track_file = os.path.join(str(tmpdir), "m3u_test.txt")
    with open(m3u_track_file, "w") as track_file:
        track_file.write("\nhttps://open.spotify.com/track/2nT5m433s95hvYJH4S7ont")
        track_file.write("\nhttp://www.youtube.com/watch?v=AOeY-nDp7hI")
    youtube_tools.generate_m3u(m3u_track_file)
    m3u_file = "{}.m3u".format(m3u_track_file.split(".")[0])
    with open(m3u_file, "r") as m3u_in:
        m3u = m3u_in.readlines()
    assert "".join(m3u) == expect_m3u


def test_all_albums(tmpdir):
    # current number of tracks on spotify since as of 10/10/2018
    # in US market only
    expect_tracks = 49
    global text_file
    text_file = os.path.join(str(tmpdir), "test_ab.txt")
    spotify_tools.write_all_albums_from_artist(ARTIST_URL, text_file)
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


def test_trim():
    with open(text_file, "r") as track_file:
        tracks = track_file.readlines()

    expect_number = len(tracks) - 1
    expect_track = tracks[0]
    track = spotdl.internals.trim_song(text_file)

    with open(text_file, "r") as track_file:
        number = len(track_file.readlines())

    assert expect_number == number and expect_track == track
