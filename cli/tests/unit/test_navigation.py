"""Tests for screen navigation and data loading."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from spotdl_cli.screens.main import MainScreen
from spotdl_cli.screens.artist import ArtistScreen
from spotdl_cli.core import EntityResult, EntityType, PlatformInfo, Song, Platform

@pytest.mark.asyncio
async def test_main_handle_entity_click_passes_entity():
    """Test that MainScreen passes the entity object to view/download methods."""
    screen = MainScreen()
    screen.notify = MagicMock()
    screen._view_entity = AsyncMock()
    screen._download_entity = AsyncMock()
    
    # Mock entity
    entity = EntityResult(
        id="test-id",
        entity_type=EntityType.ARTIST,
        name="Test Artist",
        image_url="http://example.com/img.jpg",
        platforms=[PlatformInfo(platform="spotify", platform_id="p1", url="u1")]
    )
    
    # Simulate button click
    button_id = "entity-artist-1"
    screen._entity_button_map[button_id] = entity
    await screen._handle_entity_click(button_id)
    
    # Verify _view_entity called with entity object
    screen._view_entity.assert_called_once_with("artist", "test-id", entity=entity)

@pytest.mark.asyncio
async def test_artist_screen_offline_load_uses_url():
    """Test that ArtistScreen tries URL resolution for valid IDs in offline mode."""
    # Mock offline matcher
    mock_matcher = AsyncMock()
    mock_matcher.resolve_url.return_value = [
        Song(
            name="Song 1",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="s1",
            url="u1"
        )
    ]
    
    with patch("spotdl_cli.screens.artist.get_offline_matcher", return_value=mock_matcher):
        # Initialize screen with a Spotify ID
        screen = ArtistScreen(artist_id="12345", platform="spotify")
        screen.query_one = MagicMock()
        
        # Trigger offline load
        await screen._load_offline_data()
        
        # Verify resolve_url was called
        mock_matcher.resolve_url.assert_called_once()
        args = mock_matcher.resolve_url.call_args[0]
        assert "spotify.com/artist/12345" in args[0]

@pytest.mark.asyncio
async def test_artist_screen_offline_load_fallback_search():
    """Test that ArtistScreen falls back to search if URL resolution fails."""
    # Mock offline matcher
    mock_matcher = AsyncMock()
    mock_matcher.resolve_url.side_effect = Exception("Failed")
    mock_matcher.search_all.return_value = [
        Song(
            name="Song 1",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="s1",
            url="u1"
        )
    ]
    
    with patch("spotdl_cli.screens.artist.get_offline_matcher", return_value=mock_matcher):
        # Initialize screen
        screen = ArtistScreen(artist_id="12345", platform="spotify", initial_data={"name": "Test Artist"})
        screen.query_one = MagicMock()
        
        # Trigger offline load
        await screen._load_offline_data()
        
        # Verify search_all was called with artist name
        mock_matcher.search_all.assert_called_once()
        assert "Test Artist" in mock_matcher.search_all.call_args[0][0]

@pytest.mark.asyncio
async def test_artist_screen_view_album_passes_ids():
    """Test that ArtistScreen passes IDs correctly when viewing an album."""
    screen = ArtistScreen(artist_id="123", platform="spotify")
    
    # Mock app property
    with patch.object(ArtistScreen, "app", new_callable=MagicMock) as mock_app:
        mock_app.push_screen = AsyncMock()
        
        album_data = {
            "id": "internal-id",
            "platform_id": "p-id",
            "name": "Test Album",
            "platform": "spotify"
        }
        
        await screen._view_album(album_data)
        
        # Verify AlbumScreen pushed with correct IDs
        call_args = mock_app.push_screen.call_args
        assert call_args is not None
        album_screen = call_args[0][0]
        
        assert album_screen._album_id == "p-id"
        assert album_screen._entity_id == "internal-id"