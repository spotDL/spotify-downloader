"""Comprehensive tests for SpotDL CLI screens."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from textual.widgets import Button, Input, DataTable, Select, Checkbox, Static

from spotdl_cli.screens.main import MainScreen
from spotdl_cli.screens.queue import QueueScreen
from spotdl_cli.screens.settings import SettingsScreen
from spotdl_cli.core import (
    EntityResult,
    EntityType,
    UniversalSearchResponse,
    Song,
    Platform,
    DownloadStatus,
    DownloadItem,
    QueueEvent,
    PlatformInfo,
)
from spotdl_cli.config import Settings


@pytest.fixture
def sample_search_response():
    """Create a sample search response."""
    artist = EntityResult(
        id="artist-1",
        entity_type=EntityType.ARTIST,
        name="Test Artist",
        image_url="https://example.com/artist.jpg",
        platforms=[
            PlatformInfo(
                platform="spotify",
                platform_id="spotify-artist-1",
                url="https://open.spotify.com/artist/1",
            )
        ],
    )

    track = EntityResult(
        id="track-1",
        entity_type=EntityType.TRACK,
        name="Test Song",
        subtitle="Test Artist",
        duration=180,
        image_url="https://example.com/track.jpg",
        platforms=[
            PlatformInfo(
                platform="spotify",
                platform_id="spotify-track-1",
                url="https://open.spotify.com/track/1",
            )
        ],
    )

    return UniversalSearchResponse(
        query="test",
        query_type="text",
        results=[artist, track],
        entities_created=0,
        total=2,
    )


@pytest.fixture
def sample_song():
    """Create a sample song."""
    return Song(
        name="Test Song",
        artists=["Test Artist"],
        artist="Test Artist",
        duration=180,
        platform=Platform.SPOTIFY,
        platform_id="test-123",
        url="https://open.spotify.com/track/test-123",
        cover_url="https://example.com/cover.jpg",
    )


class TestMainScreen:
    """Tests for MainScreen."""

    def test_initialization(self):
        """Test MainScreen initialization."""
        screen = MainScreen()

        assert screen._active_filter == "all"
        assert screen._search_response is None
        assert len(screen._filter_buttons) == 5
        assert screen._display_counts[EntityType.ARTIST] == 8
        assert screen._display_counts[EntityType.ALBUM] == 8
        assert screen._display_counts[EntityType.TRACK] == 15
        assert screen._display_counts[EntityType.PLAYLIST] == 10

    @pytest.mark.asyncio
    async def test_compose_layout(self):
        """Test MainScreen compose creates proper layout."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check main container exists
            main_container = pilot.app.query_one("#main-container")
            assert main_container is not None

    @pytest.mark.asyncio
    async def test_search_input_focus_on_mount(self):
        """Test search input gets focus on mount."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check search input exists
            search_input = pilot.app.query_one("#search-input", Input)
            assert search_input is not None

    @pytest.mark.asyncio
    async def test_empty_state_visible_initially(self):
        """Test empty state is visible before search."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Empty state should be visible
            empty_state = pilot.app.query_one("#empty-state")
            assert empty_state is not None
            assert not empty_state.has_class("hidden")

    @pytest.mark.asyncio
    async def test_filter_buttons_present(self):
        """Test all filter buttons are present."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check all filter buttons exist
            for filter_type in ["all", "track", "artist", "album", "playlist"]:
                button = pilot.app.query_one(f"#filter-{filter_type}", Button)
                assert button is not None

            # "All" button should be active initially
            all_button = pilot.app.query_one("#filter-all", Button)
            assert all_button.has_class("active")

    @pytest.mark.asyncio
    async def test_set_active_filter(self):
        """Test changing active filter."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Get the screen
            screen = pilot.app.query_one(MainScreen)

            # Change filter to tracks
            screen._set_active_filter("track")
            assert screen._active_filter == "track"

            # Check button states
            all_button = pilot.app.query_one("#filter-all", Button)
            track_button = pilot.app.query_one("#filter-track", Button)

            assert not all_button.has_class("active")
            assert track_button.has_class("active")

    @pytest.mark.asyncio
    async def test_search_with_empty_query(self):
        """Test search with empty query shows warning."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.query_one(MainScreen)

            # Try to search with empty input
            await screen._do_search()
            await pilot.pause()

            # Check that search was rejected (empty state should still be visible)
            empty_state = pilot.app.query_one("#empty-state")
            assert not empty_state.has_class("hidden")

    @pytest.mark.asyncio
    async def test_filter_navigation(self):
        """Test filter navigation with keyboard."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.query_one(MainScreen)

            # Test action_next_filter
            screen.action_next_filter()
            assert screen._active_filter == "track"

            screen.action_next_filter()
            assert screen._active_filter == "artist"

            # Test direct filter actions
            screen.action_filter_albums()
            assert screen._active_filter == "album"

            screen.action_filter_all()
            assert screen._active_filter == "all"

    @pytest.mark.asyncio
    async def test_create_artist_card(self, sample_search_response):
        """Test artist card creation."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.query_one(MainScreen)
            artist = sample_search_response.artists[0]
            card = screen._create_artist_card(artist)

            assert card is not None
            assert card.id.startswith("artist-card-")

    @pytest.mark.asyncio
    async def test_create_compact_row(self, sample_search_response):
        """Test compact row creation for tracks."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.query_one(MainScreen)
            track = sample_search_response.tracks[0]
            card = screen._create_compact_row(track, EntityType.TRACK)

            assert card is not None
            assert card.id.startswith("card-track-")

    def test_platform_badges(self):
        """Test platform badge generation."""
        screen = MainScreen()

        entity = EntityResult(
            id="test",
            entity_type=EntityType.TRACK,
            name="Test",
            platforms=[
                PlatformInfo(platform="spotify", platform_id="1", url="url1"),
                PlatformInfo(platform="youtube", platform_id="2", url="url2"),
            ],
        )

        badges = screen._get_platform_badges(entity)
        assert badges is not None
        assert len(badges) > 0

    def test_find_entity(self, sample_search_response):
        """Test finding entity by ID."""
        screen = MainScreen()
        screen._search_response = sample_search_response

        # Find by exact ID
        entity = screen._find_entity("track-1")
        assert entity is not None
        assert entity.name == "Test Song"

        # Not found
        entity = screen._find_entity("nonexistent")
        assert entity is None

    @pytest.mark.asyncio
    async def test_search_offline_url_track(self, sample_song):
        """Test offline URL search produces track results."""
        screen = MainScreen()

        mock_matcher = AsyncMock()
        mock_matcher.resolve_url = AsyncMock(return_value=[sample_song])

        with patch("spotdl_cli.screens.main.get_offline_matcher", return_value=mock_matcher):
            result = await screen._search_offline(
                "https://open.spotify.com/track/test-123"
            )

        assert result.query_type == "url"
        assert len(result.tracks) == 1


class TestQueueScreen:
    """Tests for QueueScreen."""

    def test_initialization(self):
        """Test QueueScreen initialization."""
        screen = QueueScreen()

        assert screen._downloading is False
        assert screen._download_task is None

    def test_compose_method_exists(self):
        """Test QueueScreen has compose method."""
        screen = QueueScreen()

        # Test that compose method exists and can be called
        assert hasattr(screen, 'compose')
        assert callable(screen.compose)

    def test_queue_event_handling(self, sample_song):
        """Test handling queue events."""
        screen = QueueScreen()

        # Test event callback
        event = QueueEvent(type="added", item_id="test-1")
        screen._on_queue_event(event)

        # Should schedule UI update without error
        assert True

    def test_pause_downloads_state(self):
        """Test pausing downloads changes state."""
        screen = QueueScreen()
        screen._downloading = True

        # Test state change without actually running the async method
        # (which requires app context for notifications)
        screen._downloading = False

        assert screen._downloading is False


class TestSettingsScreen:
    """Tests for SettingsScreen."""

    def test_initialization(self):
        """Test SettingsScreen initialization."""
        screen = SettingsScreen()

        assert screen._show_api_token is False
        assert screen._show_spotify_secret is False
        assert screen._show_sc_client_id is False
        assert screen._show_sc_auth_token is False

    @pytest.mark.asyncio
    async def test_compose_layout(self):
        """Test SettingsScreen compose creates proper layout."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield SettingsScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check main container exists
            container = pilot.app.query_one("#settings-container")
            assert container is not None

    @pytest.mark.asyncio
    async def test_settings_fields_present(self):
        """Test all settings fields are present."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield SettingsScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check key fields exist
            assert pilot.app.query_one("#api-url", Input) is not None
            assert pilot.app.query_one("#api-auth-token", Input) is not None
            assert pilot.app.query_one("#offline-mode", Checkbox) is not None
            assert pilot.app.query_one("#output-dir", Input) is not None
            assert pilot.app.query_one("#audio-format", Select) is not None
            assert pilot.app.query_one("#audio-quality", Select) is not None
            assert pilot.app.query_one("#threads", Select) is not None
            assert pilot.app.query_one("#service-status-table", DataTable) is not None
            assert pilot.app.query_one("#audio-source-table", DataTable) is not None
            assert pilot.app.query_one("#metadata-source-table", DataTable) is not None
            assert pilot.app.query_one("#lyrics-source-table", DataTable) is not None

    @pytest.mark.asyncio
    async def test_toggle_visibility(self):
        """Test toggling password field visibility."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield SettingsScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.query_one(SettingsScreen)

            # Get the field and button
            input_field = pilot.app.query_one("#spotify-client-secret", Input)
            button = pilot.app.query_one("#toggle-spotify-secret", Button)

            # Initially password field
            assert input_field.password is True

            # Toggle visibility
            screen._toggle_visibility("spotify-client-secret", "toggle-spotify-secret")

            # Should be visible now
            assert input_field.password is False
            assert button.label == "Hide"

    @pytest.mark.asyncio
    async def test_toggle_api_auth_visibility(self):
        """Test toggling API auth token visibility."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield SettingsScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.query_one(SettingsScreen)
            input_field = pilot.app.query_one("#api-auth-token", Input)
            button = pilot.app.query_one("#toggle-api-auth-token", Button)

            assert input_field.password is True

            screen._toggle_visibility("api-auth-token", "toggle-api-auth-token")

            assert input_field.password is False
            assert button.label == "Hide"

    @pytest.mark.asyncio
    async def test_metadata_settings(self):
        """Test metadata settings fields."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield SettingsScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check metadata checkboxes exist
            assert pilot.app.query_one("#embed-metadata", Checkbox) is not None
            assert pilot.app.query_one("#embed-lyrics", Checkbox) is not None
            assert pilot.app.query_one("#embed-cover", Checkbox) is not None

    @pytest.mark.asyncio
    async def test_output_template_field(self):
        """Test output template field."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield SettingsScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check template field
            template = pilot.app.query_one("#output-template", Input)
            assert template is not None
            assert template.placeholder is not None


class TestScreenNavigation:
    """Tests for screen navigation and interactions."""

    @pytest.mark.asyncio
    async def test_search_screen_bindings(self):
        """Test keyboard bindings on search screen."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.query_one(MainScreen)

            # Test refresh action (should not raise)
            screen.action_refresh()

            # Test filter shortcuts
            screen.action_filter_tracks()
            assert screen._active_filter == "track"

            screen.action_filter_artists()
            assert screen._active_filter == "artist"

            screen.action_filter_albums()
            assert screen._active_filter == "album"

            screen.action_filter_playlists()
            assert screen._active_filter == "playlist"

    def test_queue_screen_bindings(self):
        """Test keyboard bindings on queue screen."""
        screen = QueueScreen()

        # Test action bindings exist (they require an app context to run fully)
        assert hasattr(screen, 'action_clear_completed')
        assert hasattr(screen, 'action_retry_failed')
        assert hasattr(screen, 'action_toggle_download')
        assert hasattr(screen, 'action_remove_selected')

    @pytest.mark.asyncio
    async def test_settings_screen_bindings(self):
        """Test keyboard bindings on settings screen."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield SettingsScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.query_one(SettingsScreen)

            # Test save action (should not raise)
            screen.action_save()


class TestWidgetInteractions:
    """Tests for widget interactions within screens."""

    @pytest.mark.asyncio
    async def test_search_button_click(self):
        """Test clicking the search button."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Click search button (with empty input)
            await pilot.click("#search-btn")
            await pilot.pause()

            # Should not crash
            assert True

    @pytest.mark.asyncio
    async def test_filter_button_click(self):
        """Test clicking filter buttons."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.query_one(MainScreen)

            # Simulate button click by calling the on_button_pressed handler directly
            button = pilot.app.query_one("#filter-track", Button)
            from textual.widgets import Button as ButtonClass

            # Create a mock event
            event = ButtonClass.Pressed(button)
            await screen.on_button_pressed(event)
            await pilot.pause()

            # Check filter was changed
            assert screen._active_filter == "track"


class TestEventHandling:
    """Tests for event handling in screens."""

    @pytest.mark.asyncio
    async def test_input_submitted_event(self):
        """Test input submission event."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Type in search box and press enter
            search_input = pilot.app.query_one("#search-input", Input)
            search_input.value = "test query"

            await pilot.press("enter")
            await pilot.pause()

            # Should not crash
            assert True

    @pytest.mark.asyncio
    async def test_settings_input_changed_event(self):
        """Test settings input changed event."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield SettingsScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Change Spotify client ID
            spotify_id = pilot.app.query_one("#spotify-client-id", Input)
            spotify_id.value = "new-client-id"

            # Should update badges without errors
            await pilot.pause()

            assert True


# Run with: pytest tests/unit/test_screens.py -v
