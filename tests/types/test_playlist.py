from unittest.mock import MagicMock, patch

import pytest

from spotdl.types.playlist import Playlist


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
        cover_url="test",
    )

    assert playlist.name == "test"
    assert playlist.url == "test"
    assert playlist.songs == []
    assert playlist.description == "test"
    assert playlist.author_url == "test"
    assert playlist.author_name == "test"


def test_playlist_wrong_initget_results():
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
    assert len(playlist.songs) == 9
    assert playlist.description == ""


@pytest.mark.vcr()
def test_playlist_from_string():
    """
    Test if Playlist class can be initialized from string.
    """

    playlist = Playlist.from_search_term("playlist: This Is Gorillaz")

    assert playlist.name == "This Is Gorillaz"
    assert playlist.url == "http://open.spotify.com/playlist/37i9dQZF1DZ06evO25rXbO"
    assert len(playlist.urls) > 1


def _make_track_item(field_name="track"):
    """Helper to create a playlist item using the given field name for track metadata."""
    return {
        field_name: {
            "id": "abc123",
            "name": "Test Song",
            "artists": [{"name": "Test Artist"}],
            "album": {
                "id": "album123",
                "name": "Test Album",
                "artists": [{"name": "Test Artist"}],
                "album_type": "album",
                "release_date": "2024-01-01",
                "total_tracks": 1,
                "images": [{"url": "https://example.com/img.jpg", "width": 300, "height": 300}],
            },
            "type": "track",
            "is_local": False,
            "disc_number": 1,
            "track_number": 1,
            "duration_ms": 180000,
            "explicit": False,
            "external_urls": {"spotify": "https://open.spotify.com/track/abc123"},
            "external_ids": {"isrc": "USTEST0000001"},
        }
    }


def _mock_spotify_client(items):
    """Create a mock SpotifyClient that returns the given playlist items."""
    mock_client = MagicMock()
    mock_client.playlist.return_value = {
        "name": "Mock Playlist",
        "description": "desc",
        "external_urls": {"spotify": "https://open.spotify.com/playlist/mock"},
        "owner": {"display_name": "Owner"},
        "images": [{"url": "https://example.com/cover.jpg", "width": 300, "height": 300}],
    }
    mock_client.playlist_items.return_value = {
        "items": items,
        "next": None,
    }
    return mock_client


@patch("spotdl.types.playlist.SpotifyClient")
def test_playlist_parses_new_item_field(mock_sc_cls):
    """
    Spotify's Feb 2026 API returns 'item' instead of 'track' in playlist responses.
    """
    mock_sc_cls.return_value = _mock_spotify_client([_make_track_item("item")])

    metadata, songs = Playlist.get_metadata("https://open.spotify.com/playlist/mock")

    assert len(songs) == 1
    assert songs[0].name == "Test Song"


@patch("spotdl.types.playlist.SpotifyClient")
def test_playlist_parses_legacy_track_field(mock_sc_cls):
    """
    Backward compatibility: the old 'track' field should still work.
    """
    mock_sc_cls.return_value = _mock_spotify_client([_make_track_item("track")])

    metadata, songs = Playlist.get_metadata("https://open.spotify.com/playlist/mock")

    assert len(songs) == 1
    assert songs[0].name == "Test Song"


@patch("spotdl.types.playlist.SpotifyClient")
def test_playlist_skips_item_with_neither_field(mock_sc_cls):
    """
    Items with neither 'item' nor 'track' should be skipped.
    """
    mock_sc_cls.return_value = _mock_spotify_client([{"other_key": {}}])

    metadata, songs = Playlist.get_metadata("https://open.spotify.com/playlist/mock")

    assert len(songs) == 0


@pytest.mark.vcr()
def test_playlist_length():
    """
    Tests if Playlist.length works correctly.
    """

    playlist = Playlist.from_url(
        "https://open.spotify.com/playlist/5LkNhFidYyyjRWwnkcMbQs"
    )

    assert playlist.length == 9
