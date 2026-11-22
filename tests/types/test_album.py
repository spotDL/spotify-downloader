import pytest

from spotdl.types.album import Album
from spotdl.utils.spotify import SpotifyClient


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


# @pytest.mark.vcr()
# def test_album_from_string():
#     """
#     Test if Album class can be initialized from string.
#     """

#     album = Album.from_search_term("album: demon days gorillaz")

#     assert album.name == "Demon Days"
#     assert album.url == "http://open.spotify.com/album/0bUTHlWbkSQysoM3VsWldT"
#     assert album.artist["name"] == "Gorillaz"
#     assert len(album.urls) == 15


@pytest.mark.vcr()
@pytest.mark.default_cassette("test_album_from_url")
def test_album_length():
    """
    Tests if Album.length works correctly.
    """

    album = Album.from_url("https://open.spotify.com/album/4MQnUDGXmHOvnsWCpzeqWT")

    assert album.length == 16


@pytest.mark.vcr()
@pytest.mark.default_cassette("test_album_from_url")
def test_album_fetches_tracks_when_embedded_list_is_short(mocker):
    url = "https://open.spotify.com/album/4MQnUDGXmHOvnsWCpzeqWT"
    client = SpotifyClient()
    details = client.album(url)
    tracks = details["tracks"]["items"]
    mocker.patch.object(
        client,
        "album",
        return_value=details | {"tracks": {"items": tracks[:1]}, "total_tracks": 1},
    )
    album_tracks = mocker.spy(client, "album_tracks")

    album = Album.from_url(url, fetch_songs=False)

    assert [song.song_id for song in album.songs] == [track["id"] for track in tracks]
    assert {song.tracks_count for song in album.songs} == {len(tracks)}
    album_tracks.assert_called_once_with(url)
