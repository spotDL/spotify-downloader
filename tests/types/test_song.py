from unittest.mock import MagicMock, patch

import pytest

from spotdl.types.album import Album
from spotdl.types.song import Song


def test_song_init():
    """
    Test if Song class is initialized correctly.
    """

    song = Song(
        name="test",
        artists=["test"],
        album_id="test",
        album_name="test",
        album_artist="test",
        album_type="test",
        genres=["test"],
        disc_number=1,
        duration=1,
        year=1,
        date="test",
        track_number=1,
        tracks_count=1,
        isrc="test",
        song_id="test",
        cover_url="test",
        explicit=True,
        download_url="test",
        artist="test",
        copyright_text="test",
        disc_count=1,
        publisher="test",
        url="test",
        popularity=1,
    )

    assert song.name == "test"
    assert song.artists == ["test"]
    assert song.album_id == "test"
    assert song.album_name == "test"
    assert song.album_artist == "test"
    assert song.album_type == "test"
    assert song.genres == ["test"]
    assert song.disc_number == 1
    assert song.duration == 1
    assert song.year == 1
    assert song.date == "test"
    assert song.track_number == 1
    assert song.tracks_count == 1
    assert song.isrc == "test"
    assert song.song_id == "test"
    assert song.cover_url == "test"
    assert song.explicit is True
    assert song.download_url == "test"
    assert song.popularity == 1


def test_song_wrong_init():
    """
    Tests if Song class raises exception when initialized with wrong parameters.
    """

    with pytest.raises(TypeError):
        Song(
            name="test",
            artists=["test"],
            album_name="test",
            album_artist=1,
            album_type="test",
            genres=["test"],
            disc_number=1,
            duration=1,
            year=1,
            date="test",
        )  # type: ignore


@pytest.mark.vcr()
def test_song_from_url():
    """
    Tests if Song.from_url() works correctly.
    """

    song = Song.from_url("https://open.spotify.com/track/1t2qKa8K72IBC8yQlhD9bU")

    assert song.name == "Ropes"
    assert song.artists == ["Dirty Palm", "Chandler Jewels"]
    assert song.album_name == "Ropes"
    assert song.album_artist == "Dirty Palm"
    assert song.album_type == "single"
    assert song.genres != []
    assert song.disc_number == 1
    assert song.duration == 188
    assert song.year == 2021
    assert song.date == "2021-10-28"
    assert song.track_number == 1
    assert song.tracks_count == 1
    assert song.isrc == "GB2LD2110301"
    assert song.song_id == "1t2qKa8K72IBC8yQlhD9bU"
    assert (
        song.cover_url
        == "https://i.scdn.co/image/ab67616d0000b273fe2cb38e4d2412dbb0e54332"
    )
    assert song.explicit == False
    assert song.download_url == None
    assert song.popularity == 0


# @pytest.mark.vcr()
# def test_song_from_search_term():
#     """
#     Tests if Song.from_search_term() works correctly.
#     """

#     song = Song.from_search_term("Dirty Palm - Ropes")

#     assert song.name == "Ropes"
#     assert song.artists == ["Dirty Palm", "Chandler Jewels"]
#     assert song.album_name == "Ropes"
#     assert song.album_artist == "Dirty Palm"
#     assert song.genres == ["gaming edm", "melbourne bounce international"]
#     assert song.disc_number == 1
#     assert song.duration == 188
#     assert song.year == 2021
#     assert song.date == "2021-10-28"
#     assert song.track_number == 1
#     assert song.tracks_count == 1
#     assert song.isrc == "GB2LD2110301"
#     assert song.song_id == "4SN9kQlguIcjPtMNQJwD30"
#     assert song.explicit is False
#     assert song.download_url is None
#     assert song.popularity is not None and song.popularity >= 0


def test_song_from_data_dump():
    """
    Tests if Song.from_data_dump() works correctly.
    """

    # Loads from str
    song = Song.from_data_dump(
        """
        {
            "name": "Ropes",
            "artists": ["Dirty Palm", "Chandler Jewels"],
            "album_id": "4SN9kQlguIcjPtMNQJwD30",
            "album_name": "Ropes",
            "album_artist": "Dirty Palm",
            "album_type": "single",
            "genres": ["gaming edm", "melbourne bounce international"],
            "disc_number": 1,
            "duration": 188,
            "year": 2021,
            "date": "2021-10-28",
            "track_number": 1,
            "tracks_count": 1,
            "isrc": "GB2LD2110301",
            "song_id": "1t2qKa8K72IBC8yQlhD9bU",
            "cover_url": "https://i.scdn.co/image/ab67616d0000b273fe2cb38e4d2412dbb0e54332",
            "explicit": false,
            "download_url": null,
            "artist" : "Dirty Palm",
            "disc_count": 1,
            "copyright_text": "",
            "publisher": "",
            "url": "https://open.spotify.com/track/1t2qKa8K72IBC8yQlhD9bU",
            "popularity": 0
        }
        """
    )

    assert song.name == "Ropes"
    assert song.artists == ["Dirty Palm", "Chandler Jewels"]
    assert song.album_name == "Ropes"
    assert song.album_artist == "Dirty Palm"
    assert song.album_type == "single"
    assert song.genres == ["gaming edm", "melbourne bounce international"]
    assert song.disc_number == 1
    assert song.duration == 188
    assert song.year == 2021
    assert song.date == "2021-10-28"
    assert song.track_number == 1
    assert song.tracks_count == 1
    assert song.isrc == "GB2LD2110301"
    assert song.song_id == "1t2qKa8K72IBC8yQlhD9bU"
    assert (
        song.cover_url
        == "https://i.scdn.co/image/ab67616d0000b273fe2cb38e4d2412dbb0e54332"
    )
    assert song.explicit is False
    assert song.download_url is None
    assert song.popularity == 0


def test_song_from_data_dump_wrong_type():
    """
    Tests if Song.from_data_dump() raises exception when wrong type is passed.
    """

    with pytest.raises(TypeError):
        Song.from_data_dump(1)  # type: ignore


def test_song_from_dict():
    """
    Tests if Song.from_dict() works correctly.
    """

    song = Song.from_dict(
        {
            "name": "Ropes",
            "artists": ["Dirty Palm", "Chandler Jewels"],
            "album_id": "4SN9kQlguIasvwv",
            "album_name": "Ropes",
            "album_artist": "Dirty Palm",
            "album_type": "single",
            "genres": ["gaming edm", "melbourne bounce international"],
            "disc_number": 1,
            "duration": 188,
            "year": 2021,
            "date": "2021-10-28",
            "track_number": 1,
            "tracks_count": 1,
            "isrc": "GB2LD2110301",
            "song_id": "1t2qKa8K72IBC8yQlhD9bU",
            "cover_url": "https://i.scdn.co/image/ab67616d0000b273fe2cb38e4d2412dbb0e54332",
            "explicit": False,
            "download_url": None,
            "artist": "Dirty Palm",
            "disc_count": 1,
            "copyright_text": "",
            "publisher": "",
            "url": "https://open.spotify.com/track/1t2qKa8K72IBC8yQlhD9bU",
            "popularity": 0,
        }
    )

    assert song.name == "Ropes"
    assert song.artists == ["Dirty Palm", "Chandler Jewels"]
    assert song.album_name == "Ropes"
    assert song.album_artist == "Dirty Palm"
    assert song.album_type == "single"
    assert song.genres == ["gaming edm", "melbourne bounce international"]
    assert song.disc_number == 1
    assert song.duration == 188
    assert song.year == 2021
    assert song.date == "2021-10-28"
    assert song.track_number == 1
    assert song.tracks_count == 1
    assert song.isrc == "GB2LD2110301"
    assert song.song_id == "1t2qKa8K72IBC8yQlhD9bU"
    assert (
        song.cover_url
        == "https://i.scdn.co/image/ab67616d0000b273fe2cb38e4d2412dbb0e54332"
    )
    assert song.explicit == False
    assert song.popularity == 0


def _make_raw_track_meta():
    return {
        "name": "Test Song",
        "artists": [{"name": "Test Artist", "id": "artist123"}],
        "album": {"id": "album123"},
        "disc_number": 1,
        "track_number": 1,
        "duration_ms": 180000,
        "explicit": False,
        "external_urls": {"spotify": "https://open.spotify.com/track/abc123"},
        "external_ids": {"isrc": "USTEST0000001"},
        "id": "abc123",
        "popularity": 50,
    }


def _make_raw_album_meta(genres=None):
    meta = {
        "name": "Test Album",
        "artists": [{"name": "Test Artist"}],
        "album_type": "album",
        "copyrights": [{"text": "(c) 2024"}],
        "release_date": "2024-01-01",
        "total_tracks": 1,
        "tracks": {"items": [{"disc_number": 1}]},
        "label": "Test Label",
        "images": [{"url": "https://example.com/img.jpg", "width": 300, "height": 300}],
    }
    if genres is not None:
        meta["genres"] = genres
    return meta


def _make_raw_artist_meta(genres=None):
    meta = {"name": "Test Artist"}
    if genres is not None:
        meta["genres"] = genres
    return meta


@patch("spotdl.types.song.SpotifyClient")
def test_song_from_url_missing_genres(mock_sc_cls):
    """
    Spotify's Feb 2026 API removed 'genres' from album/artist metadata.
    Song.from_url should handle missing genres gracefully.
    """
    mock_client = MagicMock()
    mock_client.track.return_value = _make_raw_track_meta()
    mock_client.artist.return_value = _make_raw_artist_meta(genres=None)
    mock_client.album.return_value = _make_raw_album_meta(genres=None)
    mock_sc_cls.return_value = mock_client

    song = Song.from_url("https://open.spotify.com/track/abc123")

    assert song.genres == []
    assert song.name == "Test Song"


@patch("spotdl.types.song.SpotifyClient")
def test_song_from_url_with_genres(mock_sc_cls):
    """
    When genres are present, they should still be combined from album + artist.
    """
    mock_client = MagicMock()
    mock_client.track.return_value = _make_raw_track_meta()
    mock_client.artist.return_value = _make_raw_artist_meta(genres=["pop"])
    mock_client.album.return_value = _make_raw_album_meta(genres=["rock"])
    mock_sc_cls.return_value = mock_client

    song = Song.from_url("https://open.spotify.com/track/abc123")

    assert song.genres == ["rock", "pop"]
