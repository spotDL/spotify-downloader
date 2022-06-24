import pytest

from spotdl.types.album import Album
from spotdl.utils.spotify import SpotifyClient


def test_setup(patch_dependencies):
    """
    Sets up the tests.
    """

    SpotifyClient.init(
        client_id="5f573c9620494bae87890c0f08a60293",
        client_secret="212476d9b0f3472eaa762d90b19b0ba8",
        user_auth=False,
        no_cache=True,
    )


def test_album_init():
    """
    Test if Playlist class is initialized correctly.
    """

    Album(name="test", url="test", songs=[], artist={"name": "test"}, urls=[])


def test_album_wrong_init():
    """
    Test if Playlist class raises exception when initialized with wrong parameters.
    """

    with pytest.raises(TypeError):
        Album(
            name="test",
            url="test",
        )  # type: ignore


@pytest.mark.vcr()
def test_album_from_url():
    """
    Test if Album class can be initialized from url.
    """

    album = Album.from_url("https://open.spotify.com/album/4MQnUDGXmHOvnsWCpzeqWT")

    assert album.name == "NCS: The Best of 2017"
    assert album.url == "https://open.spotify.com/album/4MQnUDGXmHOvnsWCpzeqWT"
    assert album.artist["name"] == "Various Artists"
    assert len(album.songs) == 16


@pytest.mark.vcr()
def test_album_length():
    """
    Tests if Album.length works correctly.
    """

    album = Album.from_url("https://open.spotify.com/album/4MQnUDGXmHOvnsWCpzeqWT")

    assert album.length == 16
