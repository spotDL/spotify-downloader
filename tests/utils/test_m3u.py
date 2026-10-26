import os

import pytest

from spotdl.types.playlist import Playlist
from spotdl.types.song import Song
from spotdl.utils.m3u import create_m3u_content, create_m3u_file, gen_m3u_files

PLAYLIST = "https://open.spotify.com/playlist/5LkNhFidYyyjRWwnkcMbQs"


@pytest.mark.vcr()
def test_create_m3u_content():
    playlist = Playlist.from_url(PLAYLIST)
    content = create_m3u_content(
        playlist.songs, "{title} - {output-ext}.{output-ext}", "mp3"
    )

    assert content != ""
    assert len(content.split("\n")) > 5
    assert content.split("\n")[0] == "#EXTM3U"
    assert content.split("\n")[1].startswith("#EXTINF:")
    assert content.split("\n")[2].endswith(".mp3")


@pytest.mark.vcr()
@pytest.mark.default_cassette("test_create_m3u_content")
def test_create_m3u_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    playlist = Playlist.from_url(PLAYLIST)
    create_m3u_file("test.m3u", playlist.songs, "", "mp3")
    assert (tmp_path / "test.m3u").is_file() is True


def test_gen_m3u_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    songs = [_song(list_name="something / or other")]

    gen_m3u_files(songs, "./{list}", "", "mp3")

    assert (tmp_path / "something or other.m3u8").is_file()


def _song(list_name):
    return Song(
        name="test",
        artists=["test"],
        artist="test",
        genres=[],
        disc_number=1,
        disc_count=1,
        album_name="test",
        album_artist="test",
        duration=1,
        year=2024,
        date="2024-01-01",
        track_number=1,
        tracks_count=1,
        song_id="test",
        explicit=False,
        publisher="test",
        url="https://example.com/test",
        isrc=None,
        cover_url=None,
        copyright_text=None,
        list_name=list_name,
    )


def test_gen_m3u_files_trailing_backslash(monkeypatch):
    """Regression test for #2727: a file_name ending in a single backslash
    (plain Windows directory form, e.g. "C:\\Music\\") was not detected as
    directory-only, so ".m3u8" was appended directly, producing a hidden
    ".m3u8" file instead of "<list>.m3u8" inside the directory."""
    captured = []
    monkeypatch.setattr(
        "spotdl.utils.m3u.create_m3u_file",
        lambda file_name, *args: captured.append(file_name),
    )
    songs = [_song(list_name="mylist")]

    gen_m3u_files(songs, "C:\\Music\\", "", "mp3")

    assert captured == ["C:\\Music/mylist.m3u8"]


def test_gen_m3u_files_absolute_directory(tmp_path, monkeypatch):
    """An absolute directory must be written to as is, not relative to the cwd
    with its anchor sanitized (e.g. "C:\\" -> "C-")."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    songs = [_song(list_name="mylist")]

    gen_m3u_files(songs, str(tmp_path / "out") + os.sep, "", "mp3")

    assert (tmp_path / "out" / "mylist.m3u8").is_file()
    assert not any(cwd.iterdir())


def test_gen_m3u_files_list_directory(tmp_path, monkeypatch):
    """A directory-only name using `{list}` must not end up with `{list[0]}`
    indexing into the list name."""
    monkeypatch.chdir(tmp_path)
    songs = [_song(list_name="mylist")]

    gen_m3u_files(songs, "./{list}/", "", "mp3")

    assert (tmp_path / "mylist" / "mylist.m3u8").is_file()
