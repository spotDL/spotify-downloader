import builtins
import os

from spotdl import spotify_tools
from spotdl import const
from spotdl import spotdl

PLAYLIST_URL = 'https://open.spotify.com/user/alex/playlist/0iWOVoumWlkXIrrBTSJmN8'
ALBUM_URL = 'https://open.spotify.com/album/499J8bIsEnU7DSrosFDJJg'


def test_user_playlists(tmpdir, monkeypatch):
    expect_tracks = 14
    text_file = os.path.join(str(tmpdir), 'test_us.txt')
    monkeypatch.setattr('builtins.input', lambda x: 1)
    spotify_tools.write_user_playlist('alex', text_file)
    with open(text_file, 'r') as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


def test_playlist(tmpdir):
    expect_tracks = 14
    text_file = os.path.join(str(tmpdir), 'test_pl.txt')
    spotify_tools.write_playlist(PLAYLIST_URL, text_file)
    with open(text_file, 'r') as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


def test_album(tmpdir):
    expect_tracks = 15
    global text_file
    text_file = os.path.join(str(tmpdir), 'test_al.txt')
    spotify_tools.write_album(ALBUM_URL, text_file)
    with open(text_file, 'r') as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


def test_trim():
    with open(text_file, 'r') as track_file:
        tracks = track_file.readlines()

    expect_number = len(tracks) - 1
    expect_track = tracks[0]
    track = spotdl.internals.trim_song(text_file)

    with open(text_file, 'r') as track_file:
        number = len(track_file.readlines())

    assert expect_number == number and expect_track == track
