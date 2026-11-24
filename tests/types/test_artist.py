import pytest

from spotdl.types.artist import Artist, ArtistError
from spotdl.types.song import Song, SongListError
from spotdl.utils.spotify import SpotifyClient


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


@pytest.fixture
def paginated_artist(mocker):
    client = SpotifyClient()
    first = {"name": "Same title", "external_urls": {"spotify": "album-one"}}
    mocker.patch.object(client, "artist", return_value={"name": "Artist", "genres": []})
    mocker.patch.object(
        client,
        "artist_albums",
        return_value={"items": [first, first], "next": "page-two"},
    )
    return client, first


def test_artist_keeps_same_named_releases_and_tracks_across_pages(
    mocker, paginated_artist
):
    client, first = paginated_artist
    second = {"name": first["name"], "external_urls": {"spotify": "album-two"}}
    mocker.patch.object(
        client, "next", return_value={"items": [first, second], "next": None}
    )
    songs = [
        Song.from_missing_data(
            name="same title", song_id="track-one", artists=["Artist"]
        ),
        Song.from_missing_data(
            name="same title", song_id="track-two", artists=["Artist", "Guest"]
        ),
    ]
    albums = mocker.patch(
        "spotdl.types.artist.Album.get_metadata",
        side_effect=[({}, [songs[0]]), ({}, songs)],
    )

    metadata, tracks = Artist.get_metadata("artist-url")

    assert metadata["albums"] == ["album-one", "album-two"]
    assert tracks == songs
    assert albums.call_args_list == [
        mocker.call("album-one", None),
        mocker.call("album-two", None),
    ]


def test_artist_raises_when_release_pagination_fails(mocker, paginated_artist):
    client, _ = paginated_artist
    mocker.patch.object(client, "next", return_value=None)

    with pytest.raises(ArtistError, match="Failed to get artist releases"):
        Artist.get_metadata("artist-url")


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


@pytest.mark.vcr()
@pytest.mark.default_cassette("test_artist_from_url")
def test_artist_reuses_release_tracklists(mocker):
    client = SpotifyClient()
    album = mocker.spy(client, "album")
    album_tracks = mocker.spy(client, "album_tracks")
    artist = Artist.from_url(
        "https://open.spotify.com/artist/1FPC2zwfMHhrP3frOfaai6", fetch_songs=False
    )

    assert len(artist.songs) == 10
    assert artist.songs[0].name == "Heart"
    album.assert_not_called()
    album_tracks.assert_not_called()


@pytest.mark.xfail(
    raises=SongListError,
    strict=True,
    reason="SpotipyFree's search() ignores type= and only returns tracks",
)
@pytest.mark.vcr()
def test_artist_from_string():
    """
    Test if Artist class can be initialized from string.
    """

    artist = Artist.from_search_term("artist: gorillaz")
    assert artist.name.lower().startswith("gor")
    # assert artist.url == "http://open.spotify.com/artist/3AA28KZvwAUcZuOKwyblJQ"
    assert len(artist.urls) > 1
