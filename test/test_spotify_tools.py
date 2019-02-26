from spotdl import spotify_tools

import os
import pytest
import loader

loader.load_defaults()

@pytest.fixture(scope="module")
def spotify():
    return spotify_tools.SpotifyAuthorize()

def test_generate_token(spotify):
    token = spotify.generate_token()
    assert len(token) == 83


def test_refresh_token(spotify):
    old_instance = spotify.spotify
    spotify.refresh_token()
    new_instance = spotify.spotify
    assert not old_instance == new_instance


class TestGenerateMetadata:
    @pytest.fixture(scope="module")
    def metadata_fixture(self, spotify):
        metadata = spotify.generate_metadata("ncs - spectre")
        return metadata

    def test_len(self, metadata_fixture):
        assert len(metadata_fixture) == 24

    def test_trackname(self, metadata_fixture):
        assert metadata_fixture["name"] == "Spectre"

    def test_artist(self, metadata_fixture):
        assert metadata_fixture["artists"][0]["name"] == "Alan Walker"

    def test_duration(self, metadata_fixture):
        assert metadata_fixture["duration"] == 230.634


def test_get_playlists(spotify):
    expect_playlist_ids = [
        "34gWCK8gVeYDPKcctB6BQJ",
        "04wTU2c2WNQG9XE5oSLYfj",
        "0fWBMhGh38y0wsYWwmM9Kt",
    ]

    expect_playlists = [
        "https://open.spotify.com/playlist/" + playlist_id
        for playlist_id in expect_playlist_ids
    ]

    playlists = spotify.get_playlists("uqlakumu7wslkoen46s5bulq0")
    assert playlists == expect_playlists


def test_write_user_playlist(tmpdir, spotify, monkeypatch):
    expect_tracks = 17
    text_file = os.path.join(str(tmpdir), "test_us.txt")
    monkeypatch.setattr("builtins.input", lambda x: 1)
    spotify.write_user_playlist("uqlakumu7wslkoen46s5bulq0", text_file)
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


class TestFetchPlaylist:
    @pytest.fixture(scope="module")
    def playlist_fixture(self, spotify):
        playlist = spotify.fetch_playlist(
            "https://open.spotify.com/playlist/0fWBMhGh38y0wsYWwmM9Kt"
        )
        return playlist

    def test_name(self, playlist_fixture):
        assert playlist_fixture["name"] == "special_test_playlist"

    def test_tracks(self, playlist_fixture):
        assert playlist_fixture["tracks"]["total"] == 14


def test_write_playlist(tmpdir, spotify):
    expect_tracks = 14
    text_file = os.path.join(str(tmpdir), "test_pl.txt")
    spotify.write_playlist(
        "https://open.spotify.com/playlist/0fWBMhGh38y0wsYWwmM9Kt", text_file
    )
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


# XXX: Mock this test off if it fails in future
class TestFetchAlbum:
    @pytest.fixture(scope="module")
    def album_fixture(self, spotify):
        album = spotify.fetch_album(
            "https://open.spotify.com/album/499J8bIsEnU7DSrosFDJJg"
        )
        return album

    def test_name(self, album_fixture):
        assert album_fixture["name"] == "NCS: Infinity"

    def test_tracks(self, album_fixture):
        assert album_fixture["tracks"]["total"] == 15


# XXX: Mock this test off if it fails in future
class TestFetchAlbumsFromArtist:
    @pytest.fixture(scope="module")
    def albums_from_artist_fixture(self, spotify):
        albums = spotify.fetch_albums_from_artist(
            "https://open.spotify.com/artist/7oPftvlwr6VrsViSDV7fJY"
        )
        return albums

    def test_len(self, albums_from_artist_fixture):
        assert len(albums_from_artist_fixture) == 52

    def test_zeroth_album_name(self, albums_from_artist_fixture):
        assert albums_from_artist_fixture[0]["name"] == "Revolution Radio"

    def test_zeroth_album_tracks(self, albums_from_artist_fixture):
        assert albums_from_artist_fixture[0]["total_tracks"] == 12

    def test_fist_album_name(self, albums_from_artist_fixture):
        assert albums_from_artist_fixture[1]["name"] == "Demolicious"

    def test_first_album_tracks(self, albums_from_artist_fixture):
        assert albums_from_artist_fixture[0]["total_tracks"] == 12


def test_write_all_albums_from_artist(tmpdir, spotify):
    expect_tracks = 282
    text_file = os.path.join(str(tmpdir), "test_ab.txt")
    spotify.write_all_albums_from_artist(
        "https://open.spotify.com/artist/4dpARuHxo51G3z768sgnrY", text_file
    )
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


def test_write_album(tmpdir, spotify):
    expect_tracks = 15
    text_file = os.path.join(str(tmpdir), "test_al.txt")
    spotify.write_album(
        "https://open.spotify.com/album/499J8bIsEnU7DSrosFDJJg", text_file
    )
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks
