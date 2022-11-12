import pytest

from spotdl.types.album import Album


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
def test_album_from_string():
    """
    Test if Album class can be initialized from string.
    """

    album = Album.from_search_term("album:demon days")

    assert album.name == "Demon Days"
    assert album.url == "http://open.spotify.com/album/0bUTHlWbkSQysoM3VsWldT"
    assert album.artist["name"] == "Gorillaz"
    assert len(album.urls) == 15


@pytest.mark.vcr()
def test_album_length():
    """
    Tests if Album.length works correctly.
    """

    album = Album.from_url("https://open.spotify.com/album/4MQnUDGXmHOvnsWCpzeqWT")

    assert album.length == 16
