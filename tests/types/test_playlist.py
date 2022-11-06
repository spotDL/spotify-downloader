from spotdl.types.playlist import Playlist

import pytest


def test_playlist_init():
    """
    Test if Playlist class is initialized correctly.
    """

    playlist = Playlist(
        name="test",
        url="test",
        songs=[],
        urls=[],
        description="test",
        author_url="test",
        author_name="test",
    )

    assert playlist.name == "test"
    assert playlist.url == "test"
    assert playlist.songs == []
    assert playlist.description == "test"
    assert playlist.author_url == "test"
    assert playlist.author_name == "test"


def test_playlist_wrong_init():
    """
    Tests if Playlist class raises exception when initialized with wrong parameters.
    """

    with pytest.raises(TypeError):
        Playlist(
            name=1,
            url="test",
            songs=[],
            description="test",
        )  # type: ignore


@pytest.mark.vcr()
def test_playlist_from_url():
    """
    Tests if Playlist.from_url() works correctly.
    """

    playlist = Playlist.from_url(
        "https://open.spotify.com/playlist/5LkNhFidYyyjRWwnkcMbQs"
    )

    assert playlist.name == "Top 10 NCS Songs Episode 2"
    assert playlist.url == "https://open.spotify.com/playlist/5LkNhFidYyyjRWwnkcMbQs"
    assert len(playlist.songs) == 10
    assert playlist.description == ""


@pytest.mark.vcr()
def test_playlist_length():
    """
    Tests if Playlist.length works correctly.
    """

    playlist = Playlist.from_url(
        "https://open.spotify.com/playlist/5LkNhFidYyyjRWwnkcMbQs"
    )

    assert playlist.length == 10
