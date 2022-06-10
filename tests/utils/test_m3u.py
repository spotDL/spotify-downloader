import pytest

from spotdl.utils.m3u import create_m3u_content, create_m3u_file
from spotdl.types.playlist import Playlist

PLAYLIST = ["https://open.spotify.com/playlist/78Lg6HmUqlTnmipvNxc536"]


@pytest.mark.vcr()
def test_create_m3u_content():
    playlist = Playlist.from_url(PLAYLIST[0])
    content = create_m3u_content(
        playlist.songs, "{title} - {output-ext}.{output-ext}", "mp3"
    )

    assert content != ""
    assert len(content.split("\n")) > 5
    assert content.split("\n")[0].endswith("mp3.mp3")


@pytest.mark.vcr()
def test_create_m3u_file(tmpdir, monkeypatch):
    monkeypatch.chdir(tmpdir)
    playlist = Playlist.from_url(PLAYLIST[0])
    create_m3u_file("test.m3u", playlist.songs, "", "mp3")
    assert tmpdir.join("test.m3u").isfile() is True
