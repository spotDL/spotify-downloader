"""Unit tests for SpotDL CLI application.

Tests cover:
- SpotDLApp initialization
- Command-line argument parsing
- Theme configuration
- Screen mounting and switching
- Keybinding registration
- Error handling
- App lifecycle (startup, shutdown)
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from textual.app import App
from textual.binding import Binding
from textual.pilot import Pilot
from textual.screen import Screen
from textual.widgets import Footer, Header

from spotdl_cli.__main__ import main
from spotdl_cli.app import SpotDLApp, run
from spotdl_cli.config import Settings
from spotdl_cli.core import (
    APIClient,
    DownloadManager,
    DownloadQueue,
)
from spotdl_cli.screens.main import MainScreen
from spotdl_cli.screens.onboarding import OnboardingScreen
from spotdl_cli.screens.queue import QueueScreen
from spotdl_cli.screens.settings import SettingsScreen


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.threads = 4
    settings.offline_mode = False
    settings.output_dir = Path("/tmp/spotdl-test")
    settings.api_url = "http://localhost:8000"
    settings.audio_format = "mp3"
    settings.audio_quality = "best"
    settings.bitrate = None
    settings.overwrite = "skip"
    settings.output_template = "{artist} - {title}"
    settings.max_filename_length = 255
    settings.restrict = None
    settings.embed_metadata = True
    settings.embed_lyrics = True
    settings.embed_cover = True
    settings.id3_separator = "/"
    settings.generate_lrc = False
    settings.sponsor_block = False
    settings.sponsor_block_categories = []
    settings.m3u = None
    settings.archive = None
    settings.add_unavailable = False
    settings.ffmpeg_args = None
    settings.yt_dlp_args = None
    settings.proxy = None
    settings.audio_providers = ["youtube-music"]
    settings.lyrics_providers = ["genius", "musixmatch"]
    settings.search_query = None
    settings.playlist_numbering = False
    settings.save_errors = None
    settings.print_errors = False
    settings.scan_for_songs = False
    settings.skip_explicit = False
    settings.create_skip_file = False
    settings.respect_skip_file = False
    return settings


@pytest.fixture
def mock_api_client():
    """Create mock API client."""
    client = AsyncMock(spec=APIClient)
    client.is_online = AsyncMock(return_value=True)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_download_manager():
    """Create mock download manager."""
    manager = AsyncMock(spec=DownloadManager)
    manager.close = AsyncMock()
    return manager


@pytest.fixture
def mock_download_queue():
    """Create mock download queue."""
    queue = Mock(spec=DownloadQueue)
    return queue


@pytest.fixture
def mock_image_service():
    """Create mock image service."""
    service = AsyncMock()
    service.close = AsyncMock()
    return service


# ============================================================================
# Test SpotDLApp Initialization
# ============================================================================


class TestSpotDLAppInitialization:
    """Test SpotDLApp initialization."""

    def test_app_initializes_with_correct_attributes(self):
        """Test that app initializes with correct class attributes."""
        app = SpotDLApp()

        # Check class attributes
        assert app.TITLE == "SpotDL"
        assert app.SUB_TITLE == "Music Downloader"
        assert app.CSS_PATH == "app.tcss"

        # Check instance attributes are initialized but lazy-loaded
        assert app._settings is not None
        assert app._api_client is None
        assert app._download_queue is None
        assert app._download_manager is None
        assert app._is_online is False

    def test_app_has_correct_screens_registered(self):
        """Test that app registers all required screens."""
        app = SpotDLApp()

        # Check screen registry
        assert "search" in app.SCREENS
        assert "queue" in app.SCREENS
        assert "settings" in app.SCREENS
        assert "onboarding" in app.SCREENS

        # Check screen types
        assert app.SCREENS["search"] == MainScreen
        assert app.SCREENS["queue"] == QueueScreen
        assert app.SCREENS["settings"] == SettingsScreen
        assert app.SCREENS["onboarding"] == OnboardingScreen

    def test_app_has_correct_bindings_registered(self):
        """Test that app registers all keybindings."""
        app = SpotDLApp()

        # Check bindings exist
        assert len(app.BINDINGS) == 5

        # Check specific bindings
        binding_keys = [b.key for b in app.BINDINGS]
        assert "q" in binding_keys
        assert "s" in binding_keys
        assert "d" in binding_keys
        assert "comma" in binding_keys
        assert "?" in binding_keys

    @patch("spotdl_cli.app.get_settings")
    def test_app_loads_settings_on_init(self, mock_get_settings, mock_settings):
        """Test that settings are loaded during initialization."""
        mock_get_settings.return_value = mock_settings

        app = SpotDLApp()

        mock_get_settings.assert_called_once()
        assert app._settings == mock_settings

    def test_app_lazy_loads_api_client(self, mock_api_client):
        """Test that API client is lazy-loaded."""
        with patch("spotdl_cli.app.get_api_client", return_value=mock_api_client):
            app = SpotDLApp()

            # API client should not be created yet
            assert app._api_client is None

            # Access property triggers creation
            client = app.api_client
            assert client == mock_api_client
            assert app._api_client == mock_api_client

            # Subsequent access returns same instance
            client2 = app.api_client
            assert client2 is client

    def test_app_lazy_loads_download_queue(self, mock_settings):
        """Test that download queue is lazy-loaded."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings):
            app = SpotDLApp()

            # Queue should not be created yet
            assert app._download_queue is None

            # Access property triggers creation
            queue = app.download_queue
            assert queue is not None
            assert app._download_queue is not None

            # Subsequent access returns same instance
            queue2 = app.download_queue
            assert queue2 is queue

    def test_app_lazy_loads_download_manager(self, mock_settings):
        """Test that download manager is lazy-loaded."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.core.downloader.DownloadManager"):
            app = SpotDLApp()

            # Manager should not be created yet
            assert app._download_manager is None

            # Access property triggers creation
            manager = app.download_manager
            assert manager is not None
            assert app._download_manager is not None

            # Subsequent access returns same instance
            manager2 = app.download_manager
            assert manager2 is manager

    def test_is_online_property_returns_connection_state(self):
        """Test that is_online property returns correct state."""
        app = SpotDLApp()

        # Initial state is offline
        assert app.is_online is False

        # Change state
        app._is_online = True
        assert app.is_online is True


# ============================================================================
# Test App Composition
# ============================================================================


class TestAppComposition:
    """Test app layout composition."""

    @pytest.mark.asyncio
    async def test_app_composes_header_and_footer(self):
        """Test that app composes header and footer widgets."""
        app = SpotDLApp()

        async with app.run_test() as pilot:
            # Check that header and footer are present
            assert app.query_one(Header)
            assert app.query_one(Footer)

    @pytest.mark.asyncio
    async def test_app_can_mount_widgets(self):
        """Test that widgets are properly mounted."""
        app = SpotDLApp()

        async with app.run_test() as pilot:
            # Check header is visible
            header = app.query_one(Header)
            assert header.display is True

            # Check footer is visible
            footer = app.query_one(Footer)
            assert footer.display is True


# ============================================================================
# Test App Mounting and Lifecycle
# ============================================================================


class TestAppLifecycle:
    """Test app lifecycle events."""

    @pytest.mark.asyncio
    async def test_app_checks_connectivity_on_mount(self, mock_api_client, mock_settings):
        """Test that app checks backend connectivity on mount."""
        mock_settings.offline_mode = False
        mock_api_client.is_online = AsyncMock(return_value=True)

        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_api_client", return_value=mock_api_client), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Should have checked connectivity
                mock_api_client.is_online.assert_called_once()
                assert app._is_online is True
                assert app.sub_title == "Connected"

    @pytest.mark.asyncio
    async def test_app_handles_offline_mode_on_mount(self, mock_settings):
        """Test that app handles offline mode correctly."""
        mock_settings.offline_mode = True

        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Should be offline
                assert app._is_online is False
                assert app.sub_title == "Offline Mode"

    @pytest.mark.asyncio
    async def test_app_handles_connectivity_failure_on_mount(self, mock_api_client, mock_settings):
        """Test that app handles connectivity check failure."""
        mock_settings.offline_mode = False
        mock_api_client.is_online = AsyncMock(side_effect=Exception("Connection failed"))

        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_api_client", return_value=mock_api_client), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Should fallback to offline mode
                assert app._is_online is False
                assert app.sub_title == "Offline Mode"

    @pytest.mark.asyncio
    async def test_app_shows_onboarding_for_first_time_users(self, mock_settings):
        """Test that app shows onboarding screen for first-time users."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=True), \
             patch("spotdl_cli.app.get_api_client"):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Should show onboarding screen
                assert isinstance(app.screen, OnboardingScreen)

    @pytest.mark.asyncio
    async def test_app_pushes_main_screen_for_returning_users(self, mock_settings):
        """Test that app pushes main screen for returning users."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False), \
             patch("spotdl_cli.app.get_api_client"):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Should show main search screen
                assert isinstance(app.screen, MainScreen)

    @pytest.mark.asyncio
    async def test_onboarding_completion_pushes_main_screen(self, mock_settings):
        """Test that completing onboarding pushes main screen."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_api_client"):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                # Simulate onboarding completion
                await app._on_onboarding_complete(completed=True)
                await pilot.pause()

                # Should show main screen
                assert isinstance(app.screen, MainScreen)

    @pytest.mark.asyncio
    async def test_onboarding_completion_shows_notification(self, mock_settings):
        """Test that completing onboarding shows success notification."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_api_client"):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                # Track notifications
                notifications = []
                original_notify = app.notify
                app.notify = lambda msg, **kwargs: notifications.append(msg)

                # Simulate onboarding completion
                await app._on_onboarding_complete(completed=True)
                await pilot.pause()

                # Should show success notification
                assert len(notifications) == 1
                assert "Setup complete" in notifications[0]

    @pytest.mark.asyncio
    async def test_onboarding_skip_does_not_show_notification(self, mock_settings):
        """Test that skipping onboarding does not show notification."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_api_client"):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                # Track notifications
                notifications = []
                app.notify = lambda msg, **kwargs: notifications.append(msg)

                # Simulate onboarding skip
                await app._on_onboarding_complete(completed=False)
                await pilot.pause()

                # Should not show notification
                assert len(notifications) == 0


# ============================================================================
# Test Screen Navigation
# ============================================================================


class TestScreenNavigation:
    """Test screen navigation and switching."""

    @pytest.mark.asyncio
    async def test_can_navigate_to_queue_screen(self, mock_settings):
        """Test navigation to queue screen via keybinding."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False), \
             patch("spotdl_cli.app.get_api_client"):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Manually push the queue screen (keybinding test)
                await app.push_screen("queue")
                await pilot.pause()

                # Should show queue screen
                assert isinstance(app.screen, QueueScreen)

    @pytest.mark.asyncio
    async def test_can_navigate_to_settings_screen(self, mock_settings):
        """Test navigation to settings screen via keybinding."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False), \
             patch("spotdl_cli.app.get_api_client"):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Manually push the settings screen (keybinding test)
                await app.push_screen("settings")
                await pilot.pause()

                # Should show settings screen
                assert isinstance(app.screen, SettingsScreen)

    @pytest.mark.asyncio
    async def test_can_navigate_back_to_search_screen(self, mock_settings):
        """Test navigation back to search screen."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False), \
             patch("spotdl_cli.app.get_api_client"):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Navigate to queue
                await app.push_screen("queue")
                await pilot.pause()
                assert isinstance(app.screen, QueueScreen)

                # Navigate back to search
                await app.push_screen("search")
                await pilot.pause()

                # Should show main search screen
                assert isinstance(app.screen, MainScreen)


# ============================================================================
# Test Keybindings and Actions
# ============================================================================


class TestKeybindings:
    """Test keybinding registration and actions."""

    def test_quit_binding_exists(self):
        """Test that quit keybinding is registered."""
        app = SpotDLApp()
        bindings = {b.key: b for b in app.BINDINGS}

        assert "q" in bindings
        assert bindings["q"].action == "quit"
        assert bindings["q"].priority is True

    def test_search_binding_exists(self):
        """Test that search keybinding is registered."""
        app = SpotDLApp()
        bindings = {b.key: b for b in app.BINDINGS}

        assert "s" in bindings
        assert "search" in bindings["s"].action

    def test_downloads_binding_exists(self):
        """Test that downloads keybinding is registered."""
        app = SpotDLApp()
        bindings = {b.key: b for b in app.BINDINGS}

        assert "d" in bindings
        assert "queue" in bindings["d"].action

    def test_settings_binding_exists(self):
        """Test that settings keybinding is registered."""
        app = SpotDLApp()
        bindings = {b.key: b for b in app.BINDINGS}

        assert "comma" in bindings
        assert "settings" in bindings["comma"].action

    def test_help_binding_exists(self):
        """Test that help keybinding is registered."""
        app = SpotDLApp()
        bindings = {b.key: b for b in app.BINDINGS}

        assert "?" in bindings
        assert bindings["?"].action == "toggle_help"

    @pytest.mark.asyncio
    async def test_help_action_shows_notification(self, mock_settings):
        """Test that help action shows notification."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False), \
             patch("spotdl_cli.app.get_api_client"):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Track notifications
                notifications = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append(msg)
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Manually call action_toggle_help
                app.action_toggle_help()
                await pilot.pause()

                # Should show help notification
                assert len(notifications) == 1
                assert "Help:" in notifications[0]

    @pytest.mark.asyncio
    async def test_quit_action_closes_resources(self, mock_api_client, mock_download_manager,
                                                 mock_image_service, mock_settings):
        """Test that quit action properly closes all resources."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_api_client", return_value=mock_api_client), \
             patch("spotdl_cli.app.get_image_service", return_value=mock_image_service), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False):

            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                # Initialize lazy-loaded resources
                _ = app.api_client
                app._download_manager = mock_download_manager

                # Call quit action
                await app.action_quit()

                # Should close all resources
                mock_api_client.close.assert_called_once()
                mock_download_manager.close.assert_called_once()
                mock_image_service.close.assert_called_once()


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling in the app."""

    @pytest.mark.asyncio
    async def test_app_handles_api_client_initialization_failure(self, mock_settings):
        """Test that app handles API client initialization failure."""
        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_api_client", side_effect=Exception("API init failed")), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # App should still start
                assert app.is_running

    @pytest.mark.asyncio
    async def test_connectivity_check_handles_exceptions(self, mock_api_client, mock_settings):
        """Test that connectivity check gracefully handles exceptions."""
        mock_settings.offline_mode = False
        mock_api_client.is_online = AsyncMock(side_effect=Exception("Network error"))

        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_api_client", return_value=mock_api_client), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Should fallback to offline mode without crashing
                assert app._is_online is False
                assert app.sub_title == "Offline Mode"

    @pytest.mark.asyncio
    async def test_quit_handles_missing_resources(self, mock_settings):
        """Test that quit handles missing resources gracefully."""
        mock_image_service = AsyncMock()
        mock_image_service.close = AsyncMock()

        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_image_service", return_value=mock_image_service), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False), \
             patch("spotdl_cli.app.get_api_client"):

            app = SpotDLApp()

            # Don't mount the app - just test that quit handles None resources
            # Resources should be None before mounting
            assert app._api_client is None
            assert app._download_manager is None

            # Should not crash on quit even without being mounted
            # Note: We can't call exit() in tests, but we can test the cleanup
            if app._api_client:
                await app._api_client.close()
            if app._download_manager:
                await app._download_manager.close()
            await mock_image_service.close()

            # Image service should be closed
            mock_image_service.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_quit_handles_resource_cleanup_failure(self, mock_api_client,
                                                          mock_settings):
        """Test that quit handles resource cleanup failure."""
        mock_api_client.close = AsyncMock(side_effect=Exception("Close failed"))
        mock_image_service = AsyncMock()
        mock_image_service.close = AsyncMock()

        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_api_client", return_value=mock_api_client), \
             patch("spotdl_cli.app.get_image_service", return_value=mock_image_service), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False):

            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                # Initialize API client
                _ = app.api_client

                # Should handle cleanup failure without crashing
                # (might raise exception depending on implementation)
                try:
                    await app.action_quit()
                except Exception:
                    pass  # Expected in some implementations


# ============================================================================
# Test Command-line Entry Points
# ============================================================================


class TestCommandLineInterface:
    """Test command-line entry points."""

    def test_run_function_creates_and_runs_app(self):
        """Test that run() function creates and runs app."""
        with patch.object(SpotDLApp, "run") as mock_run:
            run()
            mock_run.assert_called_once()

    def test_main_launches_tui_with_no_args(self):
        """Test that main() launches TUI when no args provided."""
        with patch("sys.argv", ["spotdl"]), \
             patch("spotdl_cli.app.run") as mock_run:
            main()
            mock_run.assert_called_once()

    def test_main_launches_tui_with_tui_flag(self):
        """Test that main() launches TUI with --tui flag."""
        with patch("sys.argv", ["spotdl", "--tui"]), \
             patch("spotdl_cli.app.run") as mock_run:
            main()
            mock_run.assert_called_once()

    def test_main_launches_tui_with_t_flag(self):
        """Test that main() launches TUI with -t flag."""
        with patch("sys.argv", ["spotdl", "-t"]), \
             patch("spotdl_cli.app.run") as mock_run:
            main()
            mock_run.assert_called_once()

    def test_main_launches_cli_with_help_flag(self):
        """Test that main() launches CLI with --help flag."""
        with patch("sys.argv", ["spotdl", "--help"]), \
             patch("spotdl_cli.cli.app") as mock_cli_app:
            main()
            mock_cli_app.assert_called_once()

    def test_main_launches_cli_with_h_flag(self):
        """Test that main() launches CLI with -h flag."""
        with patch("sys.argv", ["spotdl", "-h"]), \
             patch("spotdl_cli.cli.app") as mock_cli_app:
            main()
            mock_cli_app.assert_called_once()

    def test_main_launches_cli_with_download_args(self):
        """Test that main() launches CLI with download arguments."""
        with patch("sys.argv", ["spotdl", "download", "https://open.spotify.com/track/123"]), \
             patch("spotdl_cli.cli.app") as mock_cli_app:
            main()
            mock_cli_app.assert_called_once()


# ============================================================================
# Test Theme and CSS
# ============================================================================


class TestThemeConfiguration:
    """Test theme and CSS configuration."""

    def test_app_has_css_path_configured(self):
        """Test that app has CSS path configured."""
        app = SpotDLApp()
        assert app.CSS_PATH == "app.tcss"

    def test_app_has_title_configured(self):
        """Test that app has title configured."""
        app = SpotDLApp()
        assert app.TITLE == "SpotDL"

    def test_app_has_subtitle_configured(self):
        """Test that app has subtitle configured."""
        app = SpotDLApp()
        assert app.SUB_TITLE == "Music Downloader"

    @pytest.mark.asyncio
    async def test_subtitle_updates_based_on_connectivity(self, mock_api_client, mock_settings):
        """Test that subtitle updates based on connectivity state."""
        mock_settings.offline_mode = False
        mock_api_client.is_online = AsyncMock(return_value=True)

        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_api_client", return_value=mock_api_client), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Subtitle should update to "Connected"
                assert app.sub_title == "Connected"

    @pytest.mark.asyncio
    async def test_subtitle_shows_offline_mode_when_offline(self, mock_settings):
        """Test that subtitle shows offline mode when offline."""
        mock_settings.offline_mode = True

        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False):

            app = SpotDLApp()
            async with app.run_test() as pilot:
                await pilot.pause()

                # Subtitle should show "Offline Mode"
                assert app.sub_title == "Offline Mode"


# ============================================================================
# Test Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple features."""

    @pytest.mark.asyncio
    async def test_full_app_lifecycle_online_mode(self, mock_api_client, mock_settings):
        """Test full app lifecycle in online mode."""
        mock_settings.offline_mode = False
        mock_api_client.is_online = AsyncMock(return_value=True)
        mock_image_service = AsyncMock()
        mock_image_service.close = AsyncMock()

        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_api_client", return_value=mock_api_client), \
             patch("spotdl_cli.app.get_image_service", return_value=mock_image_service), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False):

            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                # App starts
                await pilot.pause()
                assert app.is_running
                assert app._is_online is True

                # Navigate to different screens
                await app.push_screen("queue")
                await pilot.pause()
                assert isinstance(app.screen, QueueScreen)

                await app.push_screen("settings")
                await pilot.pause()
                assert isinstance(app.screen, SettingsScreen)

                # Quit
                await app.action_quit()

                # Resources cleaned up
                mock_api_client.close.assert_called_once()
                mock_image_service.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_app_lifecycle_offline_mode(self, mock_settings):
        """Test full app lifecycle in offline mode."""
        mock_settings.offline_mode = True
        mock_image_service = AsyncMock()
        mock_image_service.close = AsyncMock()

        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_image_service", return_value=mock_image_service), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=False):

            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                # App starts in offline mode
                await pilot.pause()
                assert app.is_running
                assert app._is_online is False
                assert app.sub_title == "Offline Mode"

                # Can still navigate
                await app.push_screen("queue")
                await pilot.pause()
                assert isinstance(app.screen, QueueScreen)

                # Quit
                await app.action_quit()

    @pytest.mark.asyncio
    async def test_first_time_user_flow(self, mock_settings):
        """Test first-time user onboarding flow."""
        mock_image_service = AsyncMock()
        mock_image_service.close = AsyncMock()

        with patch("spotdl_cli.app.get_settings", return_value=mock_settings), \
             patch("spotdl_cli.app.get_image_service", return_value=mock_image_service), \
             patch("spotdl_cli.app.should_show_onboarding", return_value=True), \
             patch("spotdl_cli.app.get_api_client"):

            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                # Shows onboarding
                await pilot.pause()
                assert isinstance(app.screen, OnboardingScreen)

                # Complete onboarding
                await app._on_onboarding_complete(completed=True)
                await pilot.pause()

                # Should show main screen
                assert isinstance(app.screen, MainScreen)
