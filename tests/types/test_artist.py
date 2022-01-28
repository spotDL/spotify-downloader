from spotdl.types import Artist
from spotdl.utils.spotify import SpotifyClient

import pytest


def test_setup(patch_dependencies):
    """
    Sets up the tests.
    """

    SpotifyClient.init(
        client_id="5f573c9620494bae87890c0f08a60293",
        client_secret="212476d9b0f3472eaa762d90b19b0ba8",
        user_auth=False,
    )


def test_artist_init():
    """
    Test if Artist class initializes correctly.
    """

    artist = Artist(
        name="test",
        tracks=[],
        albums=[],
        genres=[],
        artist_id="test",
    )

    assert artist.name == "test"
    assert artist.artist_id == "test"
    assert artist.tracks == []
    assert artist.albums == []
    assert artist.genres == []


def test_artist_wrong_init():
    """
    Test if Artist class raises exception when initialized with wrong parameters.
    """

    with pytest.raises(TypeError):
        Artist(
            name="test",
            tracks=[],
            albums=[],
            genres=[],
            artist_id="test",
            wrong_key="test",  # type: ignore
        )


@pytest.mark.vcr()
def test_artist_from_url():
    """
    Test if Artist class can be initialized from url.
    """

    artist = Artist.from_url("https://open.spotify.com/artist/1FPC2zwfMHhrP3frOfaai6")

    assert artist.name == "Kontinuum"
    assert artist.artist_id == "1FPC2zwfMHhrP3frOfaai6"
    assert len(artist.tracks) > 5
    assert len(artist.albums) > 2
    assert len(artist.genres) >= 1
