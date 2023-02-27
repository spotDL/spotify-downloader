import pytest

from spotdl.types.playlist import Playlist
from spotdl.utils.m3u import create_m3u_content, create_m3u_file

PLAYLIST = "https://open.spotify.com/playlist/5LkNhFidYyyjRWwnkcMbQs"


def test_create_m3u_content():
    playlist = Playlist.from_url(PLAYLIST)
    content = create_m3u_content(
        playlist.songs, "{title} - {output-ext}.{output-ext}", "mp3"
    )

    assert content != ""
    assert len(content.split("\n")) > 5
    assert content.split("\n")[0].endswith("mp3.mp3")


def test_create_m3u_file(tmpdir, monkeypatch):
    monkeypatch.chdir(tmpdir)
    playlist = Playlist.from_url(PLAYLIST)
    create_m3u_file("test.m3u", playlist.songs, "", "mp3")
    assert tmpdir.join("test.m3u").isfile() is True
