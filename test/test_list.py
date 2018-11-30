import pafy

import builtins
import os

from spotdl import spotify_tools
from spotdl import youtube_tools
from spotdl import const
from spotdl import internals
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
    test_spotify_track = "https://open.spotify.com/track/2nT5m433s95hvYJH4S7ont"
    test_youtube_track = "http://www.youtube.com/watch?v=AOeY-nDp7hI"

    m3u_track_file = os.path.join(str(tmpdir), "m3u_test.txt")

    with open(m3u_track_file, "w") as track_file:
        track_file.write("\n" + test_spotify_track)
        track_file.write("\n" + test_youtube_track)

    first_video, *_ = youtube_tools.generate_m3u(m3u_track_file)
    m3u_file = "{}.m3u".format(m3u_track_file.split(".")[0])

    with open(m3u_file, "r") as m3u_in:
        m3u_content = m3u_in.readlines()

    match_video = loader.match_url_in_search_results(first_video.watchv_url, test_spotify_track)
    pafy_vid = pafy.new(match_video['link'])

    expect_m3u = (
        "#EXTM3U\n\n"
        "#EXTINF:{t1_duration},{t1_title}\n"
        "{t1_watchv_url}\n"
        "#EXTINF:{t2_duration},{t2_title}\n"
        "{t2_watchv_url}\n"
    ).format(t1_duration=str(internals.get_sec(pafy_vid.duration)),
             t1_title=pafy_vid.title,
             t1_watchv_url=pafy_vid.watchv_url,
             t2_duration="226",
             t2_title="Alan Walker - Spectre [NCS Release]",
             t2_watchv_url=test_youtube_track)

    assert ''.join(m3u_content) == expect_m3u


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
