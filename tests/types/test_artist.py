import pytest

from spotdl.types.artist import Artist
from spotdl.types.song import Song


def test_artist_init():
    """
    Test if Artist class initializes correctly.
    """

    artist = Artist(
        name="test",
        songs=[],
        urls=[],
        albums=[],
        genres=[],
        url="test",
    )

    assert artist.name == "test"
    assert artist.url == "test"
    assert artist.songs == []
    assert artist.albums == []
    assert artist.genres == []


def test_artist_wrong_init():
    """
    Test if Artist class raises exception when initialized with wrong parameters.
    """

    with pytest.raises(TypeError):
        Artist(
            name="test",
            songs=[],
            urls=[],
            albums=[],
            genres=[],
            url="test",
            wrong_key="test",  # type: ignore
        )


@pytest.mark.vcr()
def test_artist_from_url():
    """
    Test if Artist class can be initialized from url.
    """

    artist = Artist.from_url("https://open.spotify.com/artist/1FPC2zwfMHhrP3frOfaai6")

    assert artist.name == "Kontinuum"
    assert artist.url == "https://open.spotify.com/artist/1FPC2zwfMHhrP3frOfaai6"
    assert len(artist.songs) > 1
    assert len(artist.albums) > 2


def test_song_duplicate_key_keeps_live_and_album_variants_distinct():
    """Same song title should stay distinct when the album or version differs."""

    studio_variant = Song.from_missing_data(
        name="No Surprises",
        artist="Radiohead",
        album_name="OK Computer",
        artists=["Radiohead"],
    )
    live_variant = Song.from_missing_data(
        name="No Surprises (Live)",
        artist="Radiohead",
        album_name="OK Computer",
        artists=["Radiohead"],
    )
    other_album_variant = Song.from_missing_data(
        name="No Surprises",
        artist="Radiohead",
        album_name="Live in Berlin",
        artists=["Radiohead"],
    )

    assert studio_variant.duplicate_key != live_variant.duplicate_key
    assert studio_variant.duplicate_key != other_album_variant.duplicate_key
    assert live_variant.duplicate_key != other_album_variant.duplicate_key


def test_song_duplicate_key_matches_identical_tracks():
    """Identical title, album and artist should produce the same key."""

    first = Song.from_missing_data(
        name="No Surprises",
        artist="Radiohead",
        album_name="OK Computer",
        artists=["Radiohead"],
    )
    second = Song.from_missing_data(
        name="No Surprises",
        artist="Radiohead",
        album_name="OK Computer",
        artists=["Radiohead"],
    )

    assert first.duplicate_key == second.duplicate_key


@pytest.mark.vcr()
def test_artist_from_string():
    """
    Test if Artist class can be initialized from string.
    """

    artist = Artist.from_search_term("artist: gorillaz")
    assert artist.name.lower().startswith("gor")
    # assert artist.url == "http://open.spotify.com/artist/3AA28KZvwAUcZuOKwyblJQ"
    assert len(artist.urls) > 1
