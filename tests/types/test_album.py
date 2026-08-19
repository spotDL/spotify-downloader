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


def test_album_get_metadata_missing_label(mocker, monkeypatch):
    """
    Test that Album.get_metadata handles missing 'label' key in album metadata
    without raising KeyError (issue #2767).
    """
    mock_album_meta = {
        "id": "test_album_id",
        "name": "Test Album",
        "artists": [{"id": "artist1", "name": "Test Artist"}],
        "release_date": "2024-01-01",
        "album_type": "album",
        "total_tracks": 1,
        "tracks": {"items": [{"disc_number": 1}], "total_tracks": 1},
        "images": [
            {"url": "https://example.com/cover.jpg", "width": 300, "height": 300}
        ],
        "copyrights": [{"text": "Copyright 2024"}],
        # "label" key intentionally omitted
    }
    mock_tracks_response = {
        "items": [
            {
                "id": "track1",
                "name": "Test Track",
                "artists": [{"id": "artist1", "name": "Test Artist"}],
                "is_local": False,
                "duration_ms": 180000,
                "disc_number": 1,
                "track_number": 1,
                "explicit": False,
                "external_urls": {"spotify": "https://open.spotify.com/track/track1"},
            }
        ],
        "next": None,
    }

    mock_client = mocker.MagicMock()
    mock_client.album.return_value = mock_album_meta
    mock_client.album_tracks.return_value = mock_tracks_response
    mock_client.next.return_value = None

    monkeypatch.setattr("spotdl.types.album.SpotifyClient", lambda: mock_client)

    metadata, songs = Album.get_metadata("https://open.spotify.com/album/test_album_id")

    assert metadata["name"] == "Test Album"
    assert len(songs) == 1
    assert songs[0].publisher == ""


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
#
#     album = Album.from_search_term("album: demon days gorillaz")
#
#     assert album.name == "Demon Days"
#     assert album.url == "http://open.spotify.com/album/0bUTHlWbkSQysoM3VsWldT"
#     assert album.artist["name"] == "Gorillaz"
#     assert len(album.urls) == 15


@pytest.mark.vcr()
def test_album_length():
    """
    Tests if Album.length works correctly.
    """

    album = Album.from_url("https://open.spotify.com/album/4MQnUDGXmHOvnsWCpzeqWT")

    assert album.length == 16
