from spotdl import spotify_tools
from spotdl import const

import spotipy

import os
import pytest
import loader

loader.load_defaults()


def test_generate_token():
    token = spotify_tools.generate_token()
    assert len(token) == 83


class TestMustBeAuthorizedDecorator:
    def test_spotify_instance_is_unset(self):
        spotify_tools.spotify = None

        @spotify_tools.must_be_authorized
        def sample_func():
            return True

        assert sample_func()

    def test_spotify_instance_forces_assertion_error(self):
        @spotify_tools.must_be_authorized
        def sample_func():
            raise AssertionError

        with pytest.raises(AssertionError):
            sample_func()

    def test_fake_token_generator(self, monkeypatch):
        spotify_tools.spotify = None
        monkeypatch.setattr(spotify_tools, "generate_token", lambda: 123123)

        with pytest.raises(spotipy.client.SpotifyException):
            spotify_tools.generate_metadata("ncs - spectre")

    def test_correct_token(self):
        assert spotify_tools.generate_metadata("ncs - spectre")


class TestGenerateMetadata:
    @pytest.fixture(scope="module")
    def metadata_fixture(self):
        metadata = spotify_tools.generate_metadata("ncs - spectre")
        return metadata

    def test_len(self, metadata_fixture):
        assert len(metadata_fixture) == 24

    def test_trackname(self, metadata_fixture):
        assert metadata_fixture["name"] == "Spectre"

    def test_artist(self, metadata_fixture):
        assert metadata_fixture["artists"][0]["name"] == "Alan Walker"

    def test_duration(self, metadata_fixture):
        assert metadata_fixture["duration"] == 230.634


def test_get_playlists():
    expect_playlist_ids = [
        "34gWCK8gVeYDPKcctB6BQJ",
        "04wTU2c2WNQG9XE5oSLYfj",
        "0fWBMhGh38y0wsYWwmM9Kt",
    ]

    expect_playlists = [
        "https://open.spotify.com/playlist/" + playlist_id
        for playlist_id in expect_playlist_ids
    ]

    playlists = spotify_tools.get_playlists("uqlakumu7wslkoen46s5bulq0")
    assert playlists == expect_playlists


def test_write_user_playlist(tmpdir, monkeypatch):
    expect_tracks = 17
    text_file = os.path.join(str(tmpdir), "test_us.txt")
    monkeypatch.setattr("builtins.input", lambda x: 1)
    spotify_tools.write_user_playlist("uqlakumu7wslkoen46s5bulq0", text_file)
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


class TestFetchPlaylist:
    @pytest.fixture(scope="module")
    def playlist_fixture(self):
        playlist = spotify_tools.fetch_playlist(
            "https://open.spotify.com/playlist/0fWBMhGh38y0wsYWwmM9Kt"
        )
        return playlist

    def test_name(self, playlist_fixture):
        assert playlist_fixture["name"] == "special_test_playlist"

    def test_tracks(self, playlist_fixture):
        assert playlist_fixture["tracks"]["total"] == 14


def test_write_playlist(tmpdir):
    expect_tracks = 14
    text_file = os.path.join(str(tmpdir), "test_pl.txt")
    spotify_tools.write_playlist(
        "https://open.spotify.com/playlist/0fWBMhGh38y0wsYWwmM9Kt", text_file
    )
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


# XXX: Monkeypatch these tests if they fail in future
class TestFetchAlbum:
    @pytest.fixture(scope="module")
    def album_fixture(self):
        album = spotify_tools.fetch_album(
            "https://open.spotify.com/album/499J8bIsEnU7DSrosFDJJg"
        )
        return album

    def test_name(self, album_fixture):
        assert album_fixture["name"] == "NCS: Infinity"

    def test_tracks(self, album_fixture):
        assert album_fixture["tracks"]["total"] == 15


# XXX: Monkeypatch these tests if they fail in future
class TestFetchAlbumsFromArtist:
    @pytest.fixture(scope="module")
    def albums_from_artist_fixture(self):
        albums = spotify_tools.fetch_albums_from_artist(
            "https://open.spotify.com/artist/7oPftvlwr6VrsViSDV7fJY"
        )
        return albums

    def test_len(self, albums_from_artist_fixture):
        assert len(albums_from_artist_fixture) == 53

    def test_zeroth_album_name(self, albums_from_artist_fixture):
        assert albums_from_artist_fixture[0]["name"] == "Revolution Radio"

    def test_zeroth_album_tracks(self, albums_from_artist_fixture):
        assert albums_from_artist_fixture[0]["total_tracks"] == 12

    def test_fist_album_name(self, albums_from_artist_fixture):
        assert albums_from_artist_fixture[1]["name"] == "Demolicious"

    def test_first_album_tracks(self, albums_from_artist_fixture):
        assert albums_from_artist_fixture[0]["total_tracks"] == 12


def test_write_all_albums_from_artist(tmpdir):
    expect_tracks = 282
    text_file = os.path.join(str(tmpdir), "test_ab.txt")
    spotify_tools.write_all_albums_from_artist(
        "https://open.spotify.com/artist/4dpARuHxo51G3z768sgnrY", text_file
    )
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks


def test_write_album(tmpdir):
    expect_tracks = 15
    text_file = os.path.join(str(tmpdir), "test_al.txt")
    spotify_tools.write_album(
        "https://open.spotify.com/album/499J8bIsEnU7DSrosFDJJg", text_file
    )
    with open(text_file, "r") as f:
        tracks = len(f.readlines())
    assert tracks == expect_tracks
