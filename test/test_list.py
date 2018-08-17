from core import spotify_tools
from core import youtube_tools
from core import const

import spotdl

import loader
import builtins
import os

loader.load_defaults()


def test_user_playlists(tmpdir, monkeypatch):
    expect_tracks = 14
    text_file = os.path.join(str(tmpdir), 'test_us.txt')
    monkeypatch.setattr('builtins.input', lambda x: 1)
    spotify_tools.write_user_playlist('alex', text_file)
    with open(text_file, 'r') as tin:
        tracks = len(tin.readlines())
    assert tracks == expect_tracks


def test_playlist(tmpdir):
    expect_tracks = 14
    text_file = os.path.join(str(tmpdir), 'test_pl.txt')
    spotify_tools.write_playlist('https://open.spotify.com/user/alex/playlist/0iWOVoumWlkXIrrBTSJmN8', text_file)
    with open(text_file, 'r') as tin:
        tracks = len(tin.readlines())
    assert tracks == expect_tracks


def test_album(tmpdir):
    expect_tracks = 15
    global text_file
    text_file = os.path.join(str(tmpdir), 'test_al.txt')
    spotify_tools.write_album('https://open.spotify.com/album/499J8bIsEnU7DSrosFDJJg', text_file)
    with open(text_file, 'r') as tin:
        tracks = len(tin.readlines())
    assert tracks == expect_tracks


def test_m3u(tmpdir):
    expect_m3u = ('#EXTM3U\n\n'
                  '#EXTM3U:226,Vidya Vidya - Safari Fruits [NCS Release]\n'
                  'http://www.youtube.com/watch?v=PbIjuqd4ENY\n'
                  '#EXTM3U:198,Tobu - Candyland [NCS Release]\n'
                  'http://www.youtube.com/watch?v=IIrCDAV3EgI\n')
    expect_lines = 6
    with open(text_file, 'r') as tin:
        tracks = tin.readlines()
    with open(text_file, 'w') as tout:
        tout.write('\n'.join(tracks[:2]))
    youtube_tools.generate_m3u(text_file)
    m3u_file = '{}.m3u'.format(text_file.split('.')[0])
    with open(m3u_file, 'r') as m3u_in:
        m3u = m3u_in.readlines()
    assert ''.join(m3u) == expect_m3u


def test_trim():
    with open(text_file, 'r') as track_file:
        tracks = track_file.readlines()

    expect_number = len(tracks) - 1
    expect_track = tracks[0]
    track = spotdl.internals.trim_song(text_file)

    with open(text_file, 'r') as track_file:
        number = len(track_file.readlines())

    assert (expect_number == number and expect_track == track)
