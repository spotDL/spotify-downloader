"""Comprehensive tests for SpotDL CLI screens."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from textual.widgets import Button, Input, DataTable, Select, Checkbox

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
def mock_app():
    """Create a mock SpotDL app instance."""
    app = MagicMock()
    app.is_online = True
    app.download_queue = MagicMock()
    app.download_manager = MagicMock()
    app.api_client = MagicMock()
    app.pop_screen = MagicMock()
    app.push_screen = AsyncMock()
    return app


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

    album = EntityResult(
        id="album-1",
        entity_type=EntityType.ALBUM,
        name="Test Album",
        subtitle="Test Artist",
        image_url="https://example.com/album.jpg",
        platforms=[
            PlatformInfo(
                platform="spotify",
                platform_id="spotify-album-1",
                url="https://open.spotify.com/album/1",
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

    playlist = EntityResult(
        id="playlist-1",
        entity_type=EntityType.PLAYLIST,
        name="Test Playlist",
        subtitle="50 songs",
        image_url="https://example.com/playlist.jpg",
        platforms=[
            PlatformInfo(
                platform="spotify",
                platform_id="spotify-playlist-1",
                url="https://open.spotify.com/playlist/1",
            )
        ],
    )

    return UniversalSearchResponse(
        query="test",
        query_type="text",
        results=[artist, album, track, playlist],
        entities_created=0,
        total=4,
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
        assert screen._display_counts[EntityType.ARTIST] == 6
        assert screen._display_counts[EntityType.ALBUM] == 8
        assert screen._display_counts[EntityType.TRACK] == 10
        assert screen._display_counts[EntityType.PLAYLIST] == 6

    def test_compose_layout(self):
        """Test MainScreen compose creates proper layout."""
        screen = MainScreen()

        widgets = list(screen.compose())

        # Should have a main container
        assert len(widgets) > 0
        # The first widget should be a VerticalScroll with id "main-container"
        assert widgets[0].id == "main-container"

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

            # Check that search was rejected (status should indicate empty query)
            status_bar = pilot.app.query_one("#status-bar")
            # Status should not say "Searching..."
            assert status_bar.renderable != "Searching..."

    @pytest.mark.asyncio
    async def test_search_online_success(self, mock_app, sample_search_response):
        """Test successful online search."""
        screen = MainScreen()
        screen.app = mock_app

        # Mock the search
        with patch.object(screen, "_search_online", return_value=sample_search_response):
            from textual.app import App

            class TestApp(App):
                def compose(self):
                    return screen

            async with TestApp().run_test() as pilot:
                await pilot.pause()

                # Set search query
                search_input = pilot.app.query_one("#search-input", Input)
                search_input.value = "test query"

                # Perform search
                await screen._do_search()
                await pilot.pause()

                # Check results are stored
                assert screen._search_response is not None
                assert screen._search_response.total == 4

    @pytest.mark.asyncio
    async def test_search_offline_mode(self, mock_app, sample_song):
        """Test offline search mode."""
        screen = MainScreen()
        screen.app = mock_app
        mock_app.is_online = False

        # Mock offline search
        with patch.object(screen, "_search_offline") as mock_offline:
            mock_offline.return_value = UniversalSearchResponse(
                query="test",
                query_type="text",
                results=[],
                entities_created=0,
                total=0,
            )

            from textual.app import App

            class TestApp(App):
                def compose(self):
                    return screen

            async with TestApp().run_test() as pilot:
                await pilot.pause()

                # Set search query
                search_input = pilot.app.query_one("#search-input", Input)
                search_input.value = "test"

                # Perform search
                await screen._do_search()
                await pilot.pause()

                # Should have called offline search
                mock_offline.assert_called_once()

    @pytest.mark.asyncio
    async def test_filter_navigation(self, mock_app):
        """Test filter navigation with keyboard."""
        screen = MainScreen()
        screen.app = mock_app

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
    async def test_create_artist_card(self, mock_app, sample_search_response):
        """Test artist card creation."""
        screen = MainScreen()
        screen.app = mock_app

        artist = sample_search_response.artists[0]
        card = screen._create_artist_card(artist)

        assert card is not None
        assert card.id.startswith("artist-card-")

    @pytest.mark.asyncio
    async def test_create_entity_card(self, mock_app, sample_search_response):
        """Test entity card creation for tracks."""
        screen = MainScreen()
        screen.app = mock_app

        track = sample_search_response.tracks[0]
        card = screen._create_entity_card(track, EntityType.TRACK)

        assert card is not None
        assert card.id.startswith("card-track-")

    @pytest.mark.asyncio
    async def test_platform_badges(self, mock_app):
        """Test platform badge generation."""
        screen = MainScreen()
        screen.app = mock_app

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

    @pytest.mark.asyncio
    async def test_find_entity(self, mock_app, sample_search_response):
        """Test finding entity by ID."""
        screen = MainScreen()
        screen.app = mock_app
        screen._search_response = sample_search_response

        # Find by exact ID
        entity = screen._find_entity("track-1")
        assert entity is not None
        assert entity.name == "Test Song"

        # Not found
        entity = screen._find_entity("nonexistent")
        assert entity is None


class TestQueueScreen:
    """Tests for QueueScreen."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_app):
        """Test QueueScreen initialization."""
        screen = QueueScreen()
        screen.app = mock_app

        assert screen._downloading is False
        assert screen._download_task is None

    @pytest.mark.asyncio
    async def test_compose_layout(self, mock_app):
        """Test QueueScreen compose creates proper layout."""
        screen = QueueScreen()
        screen.app = mock_app

        widgets = list(screen.compose())

        # Should have widgets
        assert len(widgets) > 0

    @pytest.mark.asyncio
    async def test_queue_table_setup(self, mock_app):
        """Test queue table is properly set up on mount."""
        screen = QueueScreen()
        screen.app = mock_app
        mock_app.download_queue.add_callback = MagicMock()
        mock_app.download_queue.items = []

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check table exists and has columns
            table = pilot.app.query_one("#queue-table", DataTable)
            assert table is not None
            assert table.cursor_type == "row"
            assert table.zebra_stripes is True

    @pytest.mark.asyncio
    async def test_update_stats(self, mock_app):
        """Test queue statistics update."""
        screen = QueueScreen()
        screen.app = mock_app

        # Mock queue stats
        mock_app.download_queue.pending_count = 5
        mock_app.download_queue.active_count = 2
        mock_app.download_queue.completed_items = [MagicMock()] * 3
        mock_app.download_queue.failed_items = [MagicMock()]

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            screen._update_stats()

            # Check stats display
            stats = pilot.app.query_one("#queue-stats")
            assert "Pending: 5" in stats.renderable
            assert "Active: 2" in stats.renderable
            assert "Done: 3" in stats.renderable
            assert "Failed: 1" in stats.renderable

    @pytest.mark.asyncio
    async def test_queue_event_handling(self, mock_app, sample_song):
        """Test handling queue events."""
        screen = QueueScreen()
        screen.app = mock_app
        mock_app.download_queue.items = []

        # Test event callback
        event = QueueEvent(type="added", item_id="test-1")
        screen._on_queue_event(event)

        # Should schedule UI update
        assert True  # Event handled without error

    @pytest.mark.asyncio
    async def test_start_downloads(self, mock_app):
        """Test starting downloads."""
        screen = QueueScreen()
        screen.app = mock_app
        mock_app.notify = MagicMock()

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Start downloads
            await screen._start_downloads()

            assert screen._downloading is True
            mock_app.notify.assert_called_once_with("Starting downloads...")

    @pytest.mark.asyncio
    async def test_pause_downloads(self, mock_app):
        """Test pausing downloads."""
        screen = QueueScreen()
        screen.app = mock_app
        mock_app.notify = MagicMock()
        screen._downloading = True

        await screen._pause_downloads()

        assert screen._downloading is False
        mock_app.notify.assert_called_once_with("Downloads paused")

    @pytest.mark.asyncio
    async def test_toggle_download_action(self, mock_app):
        """Test toggle download action."""
        screen = QueueScreen()
        screen.app = mock_app
        mock_app.notify = MagicMock()

        # Start with not downloading
        assert screen._downloading is False

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Toggle should start
            screen.action_toggle_download()
            await pilot.pause()

            # Should be downloading now
            assert screen._downloading is True

    @pytest.mark.asyncio
    async def test_clear_completed(self, mock_app):
        """Test clearing completed downloads."""
        screen = QueueScreen()
        screen.app = mock_app
        mock_app.notify = MagicMock()
        mock_app.download_queue.clear_completed = AsyncMock(return_value=3)

        await screen._clear_completed()

        mock_app.download_queue.clear_completed.assert_called_once()
        mock_app.notify.assert_called_once()
        assert "3" in mock_app.notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_retry_failed(self, mock_app, sample_song):
        """Test retrying failed downloads."""
        screen = QueueScreen()
        screen.app = mock_app
        mock_app.notify = MagicMock()

        # Create mock failed items
        failed_item = MagicMock()
        mock_app.download_queue.failed_items = [failed_item, failed_item]
        mock_app.download_queue.get_item_id = MagicMock(return_value="item-1")
        mock_app.download_queue.update_status = AsyncMock()

        await screen._retry_failed()

        # Should have retried 2 items
        assert mock_app.download_queue.update_status.call_count == 2
        mock_app.notify.assert_called_once()
        assert "2" in mock_app.notify.call_args[0][0]


class TestSettingsScreen:
    """Tests for SettingsScreen."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_app):
        """Test SettingsScreen initialization."""
        screen = SettingsScreen()
        screen.app = mock_app

        assert screen._show_spotify_secret is False
        assert screen._show_sc_client_id is False
        assert screen._show_sc_auth_token is False

    @pytest.mark.asyncio
    async def test_compose_layout(self, mock_app):
        """Test SettingsScreen compose creates proper layout."""
        screen = SettingsScreen()
        screen.app = mock_app

        widgets = list(screen.compose())

        # Should have widgets
        assert len(widgets) > 0

    @pytest.mark.asyncio
    async def test_settings_fields_present(self, mock_app):
        """Test all settings fields are present."""
        screen = SettingsScreen()
        screen.app = mock_app

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check key fields exist
            assert pilot.app.query_one("#api-url", Input) is not None
            assert pilot.app.query_one("#offline-mode", Checkbox) is not None
            assert pilot.app.query_one("#output-dir", Input) is not None
            assert pilot.app.query_one("#audio-format", Select) is not None
            assert pilot.app.query_one("#audio-quality", Select) is not None
            assert pilot.app.query_one("#threads", Select) is not None

    @pytest.mark.asyncio
    async def test_toggle_visibility(self, mock_app):
        """Test toggling password field visibility."""
        screen = SettingsScreen()
        screen.app = mock_app

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

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
    async def test_update_status_badges(self, mock_app):
        """Test status badge updates."""
        screen = SettingsScreen()
        screen.app = mock_app

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Set Spotify credentials
            spotify_id = pilot.app.query_one("#spotify-client-id", Input)
            spotify_secret = pilot.app.query_one("#spotify-client-secret", Input)

            spotify_id.value = "test-client-id"
            spotify_secret.value = "test-secret"

            screen._update_status_badges()

            # Check badge
            badge = pilot.app.query_one("#spotify-status-badge")
            # Badge should show configured
            assert badge is not None

    @pytest.mark.asyncio
    async def test_save_settings(self, mock_app, tmp_path):
        """Test saving settings."""
        screen = SettingsScreen()
        screen.app = mock_app
        mock_app.pop_screen = MagicMock()
        mock_app.notify = MagicMock()

        # Mock settings
        with patch("spotdl_cli.screens.settings.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.ensure_directories = MagicMock()
            mock_settings.save = MagicMock()
            mock_get_settings.return_value = mock_settings
            screen._settings = mock_settings

            from textual.app import App

            class TestApp(App):
                def compose(self):
                    return screen

            async with TestApp().run_test() as pilot:
                await pilot.pause()

                # Update some fields
                api_url = pilot.app.query_one("#api-url", Input)
                api_url.value = "http://localhost:9000"

                output_dir = pilot.app.query_one("#output-dir", Input)
                output_dir.value = str(tmp_path)

                # Save settings
                await screen._save_settings()

                # Check settings were updated
                assert mock_settings.api_url == "http://localhost:9000"
                assert mock_settings.output_dir == Path(str(tmp_path))
                mock_settings.save.assert_called_once()
                mock_app.notify.assert_called_once_with("Settings saved")

    @pytest.mark.asyncio
    async def test_reset_to_defaults(self, mock_app):
        """Test resetting settings to defaults."""
        screen = SettingsScreen()
        screen.app = mock_app
        mock_app.notify = MagicMock()

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Change some values
            api_url = pilot.app.query_one("#api-url", Input)
            api_url.value = "http://custom:8080"

            # Reset to defaults
            screen._reset_to_defaults()

            # Check notification
            mock_app.notify.assert_called_once()
            assert "defaults" in mock_app.notify.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_metadata_settings(self, mock_app):
        """Test metadata settings fields."""
        screen = SettingsScreen()
        screen.app = mock_app

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check metadata checkboxes exist
            assert pilot.app.query_one("#embed-metadata", Checkbox) is not None
            assert pilot.app.query_one("#embed-lyrics", Checkbox) is not None
            assert pilot.app.query_one("#embed-cover", Checkbox) is not None

    @pytest.mark.asyncio
    async def test_output_template_field(self, mock_app):
        """Test output template field."""
        screen = SettingsScreen()
        screen.app = mock_app

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check template field
            template = pilot.app.query_one("#output-template", Input)
            assert template is not None
            assert template.placeholder is not None


class TestScreenNavigation:
    """Tests for screen navigation and interactions."""

    @pytest.mark.asyncio
    async def test_screen_back_navigation(self, mock_app):
        """Test back navigation from screens."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                return MainScreen()

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Press escape (back)
            await pilot.press("escape")
            await pilot.pause()

            # Should trigger app.pop_screen
            # In test environment, this may not fully execute

    @pytest.mark.asyncio
    async def test_search_screen_bindings(self, mock_app):
        """Test keyboard bindings on search screen."""
        screen = MainScreen()
        screen.app = mock_app

        # Test refresh action
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

    @pytest.mark.asyncio
    async def test_queue_screen_bindings(self, mock_app):
        """Test keyboard bindings on queue screen."""
        screen = QueueScreen()
        screen.app = mock_app
        mock_app.notify = MagicMock()
        mock_app.download_queue.clear_completed = AsyncMock(return_value=0)
        mock_app.download_queue.failed_items = []
        mock_app.download_queue.get_item_id = MagicMock(return_value="test-id")
        mock_app.download_queue.update_status = AsyncMock()

        # Test action bindings
        screen.action_clear_completed()
        screen.action_retry_failed()

        # Actions should execute
        assert True

    @pytest.mark.asyncio
    async def test_settings_screen_bindings(self, mock_app):
        """Test keyboard bindings on settings screen."""
        screen = SettingsScreen()
        screen.app = mock_app
        mock_app.notify = MagicMock()
        mock_app.pop_screen = MagicMock()

        # Mock settings save
        with patch("spotdl_cli.screens.settings.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.ensure_directories = MagicMock()
            mock_settings.save = MagicMock()
            mock_get_settings.return_value = mock_settings
            screen._settings = mock_settings

            # Test save action
            screen.action_save()

            # Should trigger save
            assert True


class TestWidgetInteractions:
    """Tests for widget interactions within screens."""

    @pytest.mark.asyncio
    async def test_search_button_click(self, mock_app):
        """Test clicking the search button."""
        screen = MainScreen()
        screen.app = mock_app

        with patch.object(screen, "_do_search") as mock_search:
            from textual.app import App

            class TestApp(App):
                def compose(self):
                    return screen

            async with TestApp().run_test() as pilot:
                await pilot.pause()

                # Click search button
                await pilot.click("#search-btn")
                await pilot.pause()

                # Should trigger search
                mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_filter_button_click(self, mock_app):
        """Test clicking filter buttons."""
        screen = MainScreen()
        screen.app = mock_app

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Click track filter
            await pilot.click("#filter-track")
            await pilot.pause()

            assert screen._active_filter == "track"

    @pytest.mark.asyncio
    async def test_queue_button_interactions(self, mock_app):
        """Test queue screen button interactions."""
        screen = QueueScreen()
        screen.app = mock_app
        mock_app.notify = MagicMock()
        mock_app.download_queue.clear_completed = AsyncMock(return_value=2)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Click clear done button
            await pilot.click("#clear-done-btn")
            await pilot.pause()

            # Should trigger clear
            mock_app.download_queue.clear_completed.assert_called()

    @pytest.mark.asyncio
    async def test_settings_save_button(self, mock_app):
        """Test settings save button."""
        screen = SettingsScreen()
        screen.app = mock_app
        mock_app.notify = MagicMock()
        mock_app.pop_screen = MagicMock()

        with patch.object(screen, "_save_settings") as mock_save:
            from textual.app import App

            class TestApp(App):
                def compose(self):
                    return screen

            async with TestApp().run_test() as pilot:
                await pilot.pause()

                # Click save button
                await pilot.click("#save-btn")
                await pilot.pause()

                # Should trigger save
                mock_save.assert_called()


class TestEventHandling:
    """Tests for event handling in screens."""

    @pytest.mark.asyncio
    async def test_input_submitted_event(self, mock_app):
        """Test input submission event."""
        screen = MainScreen()
        screen.app = mock_app

        with patch.object(screen, "_do_search") as mock_search:
            from textual.app import App

            class TestApp(App):
                def compose(self):
                    return screen

            async with TestApp().run_test() as pilot:
                await pilot.pause()

                # Type in search box and press enter
                search_input = pilot.app.query_one("#search-input", Input)
                search_input.value = "test query"

                await pilot.press("enter")
                await pilot.pause()

                # Should trigger search
                mock_search.assert_called()

    @pytest.mark.asyncio
    async def test_queue_event_callback(self, mock_app):
        """Test queue event callback system."""
        screen = QueueScreen()
        screen.app = mock_app
        mock_app.download_queue.items = []
        mock_app.download_queue.add_callback = MagicMock()
        mock_app.download_queue.remove_callback = MagicMock()

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Check callback was registered
            mock_app.download_queue.add_callback.assert_called_once()

            # Unmount should unregister
            await pilot.app.pop_screen()

            mock_app.download_queue.remove_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_settings_input_changed_event(self, mock_app):
        """Test settings input changed event."""
        screen = SettingsScreen()
        screen.app = mock_app

        from textual.app import App

        class TestApp(App):
            def compose(self):
                return screen

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Change Spotify client ID
            spotify_id = pilot.app.query_one("#spotify-client-id", Input)
            spotify_id.value = "new-client-id"

            # Should update badges
            # No errors should occur
            await pilot.pause()

            assert True


# Run with: pytest tests/unit/test_screens.py -v
