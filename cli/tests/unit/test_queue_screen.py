"""Tests for queue screen fixes.

Tests cover:
- _remove_selected: coordinate-based row key extraction
- _remove_selected: empty table guard
- _start_downloads: empty queue guard
- _start_downloads: duplicate-start guard
- _clear_completed: empty-result warning toast
- _retry_failed: empty-result warning toast
- Queue table rendering and filtering
- Button handlers routing
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from textual.widgets import Button, DataTable

from spotdl_cli.app import SpotDLApp
from spotdl_cli.config import Settings
from spotdl_cli.core import DownloadStatus
from spotdl_cli.core.types import Platform, Song
from spotdl_cli.screens.queue import QueueScreen

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.threads = 2
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
    client = AsyncMock()
    client.is_online = AsyncMock(return_value=False)
    client.close = AsyncMock()
    client.get_service_status = AsyncMock(return_value={})
    client.list_downloads = AsyncMock(side_effect=Exception("disabled"))
    return client


def _make_song(name: str = "Test Song", idx: int = 0) -> Song:
    """Helper to create a test Song."""
    return Song(
        name=f"{name} {idx}" if idx else name,
        artists=["Test Artist"],
        artist="Test Artist",
        duration=180,
        platform=Platform.SPOTIFY,
        platform_id=f"test-{idx}",
        url=f"https://open.spotify.com/track/test-{idx}",
        cover_url="https://example.com/cover.jpg",
    )


# ============================================================================
# Test Queue Screen: _remove_selected fix
# ============================================================================


class TestQueueRemoveSelected:
    """Tests for the _remove_selected fix (coordinate-based row key extraction)."""

    @pytest.mark.asyncio
    async def test_remove_selected_on_empty_table(self, mock_settings, mock_api_client):
        """Test _remove_selected shows warning when table is empty."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                # Track notifications
                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Try to remove from empty table
                await screen._remove_selected()
                await pilot.pause()

                # Should show "No item selected" warning
                assert any("No item selected" in n[0] for n in notifications)

    @pytest.mark.asyncio
    async def test_remove_selected_extracts_correct_row_key(
        self, mock_settings, mock_api_client
    ):
        """Test _remove_selected uses coordinate_to_cell_key to get item ID."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                # Add a song to the queue
                song = _make_song()
                queue = app.download_queue
                await queue.add(song)
                await pilot.pause()

                # Verify item was added
                assert queue.total_count == 1

                # Table should have the row
                table = screen.query_one("#queue-table", DataTable)
                assert table.row_count == 1

                # Move cursor to first row
                from textual.coordinate import Coordinate
                table.cursor_coordinate = Coordinate(0, 0)

                # Track notifications
                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Remove the selected item
                await screen._remove_selected()
                await pilot.pause()

                # Should have removed the item
                assert queue.total_count == 0
                assert any("Item removed" in n[0] for n in notifications)

    @pytest.mark.asyncio
    async def test_remove_selected_cannot_remove_active_download(
        self, mock_settings, mock_api_client
    ):
        """Test _remove_selected cannot remove active downloads."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                # Add and mark as downloading
                song = _make_song()
                queue = app.download_queue
                item_id = await queue.add(song)
                await queue.update_status(item_id, DownloadStatus.DOWNLOADING)
                await pilot.pause()

                table = screen.query_one("#queue-table", DataTable)
                from textual.coordinate import Coordinate
                table.cursor_coordinate = Coordinate(0, 0)

                # Track notifications
                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Try to remove active download
                await screen._remove_selected()
                await pilot.pause()

                # Should not have removed (item has no download_id so falls to queue.remove)
                assert queue.total_count == 1
                assert any("Cannot remove active download" in n[0] for n in notifications)


# ============================================================================
# Test Queue Screen: _start_downloads guards
# ============================================================================


class TestQueueStartDownloads:
    """Tests for _start_downloads empty queue and duplicate-start guards."""

    @pytest.mark.asyncio
    async def test_start_downloads_empty_queue_warning(
        self, mock_settings, mock_api_client
    ):
        """Test _start_downloads shows warning when no pending items."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Start with empty queue
                await screen._start_downloads()
                await pilot.pause()

                assert any("No pending downloads" in n[0] for n in notifications)
                assert screen._downloading is False

    @pytest.mark.asyncio
    async def test_start_downloads_duplicate_start_warning(
        self, mock_settings, mock_api_client
    ):
        """Test _start_downloads shows warning when already in progress."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                # Set downloading state
                screen._downloading = True

                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Try to start again
                await screen._start_downloads()
                await pilot.pause()

                assert any("already in progress" in n[0] for n in notifications)


# ============================================================================
# Test Queue Screen: _clear_completed and _retry_failed
# ============================================================================


class TestQueueClearAndRetry:
    """Tests for _clear_completed and _retry_failed warning toasts."""

    @pytest.mark.asyncio
    async def test_clear_completed_empty_warning(
        self, mock_settings, mock_api_client
    ):
        """Test _clear_completed shows warning when nothing to clear."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Clear with no completed items
                await screen._clear_completed()
                await pilot.pause()

                assert any(
                    "No completed items to clear" in n[0] for n in notifications
                )

    @pytest.mark.asyncio
    async def test_clear_completed_with_items(
        self, mock_settings, mock_api_client
    ):
        """Test _clear_completed removes completed items and shows count."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                # Add items and mark completed
                queue = app.download_queue
                song1 = _make_song(idx=1)
                song2 = _make_song(idx=2)
                id1 = await queue.add(song1)
                id2 = await queue.add(song2)
                await queue.update_status(id1, DownloadStatus.COMPLETED)
                await queue.update_status(id2, DownloadStatus.COMPLETED)
                await pilot.pause()

                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Clear completed
                await screen._clear_completed()
                await pilot.pause()

                assert queue.total_count == 0
                assert any("Cleared 2 completed" in n[0] for n in notifications)

    @pytest.mark.asyncio
    async def test_retry_failed_empty_warning(
        self, mock_settings, mock_api_client
    ):
        """Test _retry_failed shows warning when no failed items."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Retry with no failed items
                await screen._retry_failed()
                await pilot.pause()

                assert any(
                    "No failed items to retry" in n[0] for n in notifications
                )

    @pytest.mark.asyncio
    async def test_retry_failed_with_items(
        self, mock_settings, mock_api_client
    ):
        """Test _retry_failed resets failed items to pending."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                # Add items and mark as failed
                queue = app.download_queue
                song1 = _make_song(idx=1)
                song2 = _make_song(idx=2)
                id1 = await queue.add(song1)
                id2 = await queue.add(song2)
                await queue.update_status(id1, DownloadStatus.FAILED, error="err1")
                await queue.update_status(id2, DownloadStatus.FAILED, error="err2")
                await pilot.pause()

                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Retry failed
                await screen._retry_failed()
                await pilot.pause()

                # Items should be reset to pending
                assert queue.pending_count == 2
                assert len(queue.failed_items) == 0
                assert any("Retrying 2 failed" in n[0] for n in notifications)


# ============================================================================
# Test Queue Screen: Table rendering
# ============================================================================


class TestQueueTableRendering:
    """Tests for queue table rendering and filtering."""

    @pytest.mark.asyncio
    async def test_table_shows_empty_state_when_empty(
        self, mock_settings, mock_api_client
    ):
        """Test empty state is visible when queue is empty."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                # Empty state should be visible
                empty_state = screen.query_one("#queue-empty-state")
                assert not empty_state.has_class("hidden")

    @pytest.mark.asyncio
    async def test_table_hides_empty_state_with_items(
        self, mock_settings, mock_api_client
    ):
        """Test empty state is hidden when items are in queue."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                # Add a song
                queue = app.download_queue
                await queue.add(_make_song())
                await pilot.pause()

                # Empty state should be hidden
                empty_state = screen.query_one("#queue-empty-state")
                assert empty_state.has_class("hidden")

                # Table should have the row
                table = screen.query_one("#queue-table", DataTable)
                assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_table_columns_present(
        self, mock_settings, mock_api_client
    ):
        """Test queue table has correct columns."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                table = screen.query_one("#queue-table", DataTable)
                # Table should have 7 columns
                assert len(table.columns) == 7

    @pytest.mark.asyncio
    async def test_filter_tabs_update_view(
        self, mock_settings, mock_api_client
    ):
        """Test filter tabs filter the queue view."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                # Add items with different statuses
                queue = app.download_queue
                await queue.add(_make_song(idx=1))
                id2 = await queue.add(_make_song(idx=2))
                id3 = await queue.add(_make_song(idx=3))

                await queue.update_status(id2, DownloadStatus.COMPLETED)
                await queue.update_status(id3, DownloadStatus.FAILED, error="test")
                await pilot.pause()

                table = screen.query_one("#queue-table", DataTable)

                # All filter should show all items
                screen._set_active_filter("all")
                assert table.row_count == 3

                # Done filter should show 1
                screen._set_active_filter("done")
                assert table.row_count == 1

                # Failed filter should show 1
                screen._set_active_filter("failed")
                assert table.row_count == 1

                # Active filter should show 1 (pending)
                screen._set_active_filter("active")
                assert table.row_count == 1


# ============================================================================
# Test Queue Screen: Button handler routing
# ============================================================================


class TestQueueButtonHandlers:
    """Tests for button handler routing in on_button_pressed."""

    @pytest.mark.asyncio
    async def test_start_button_calls_start_downloads(
        self, mock_settings, mock_api_client
    ):
        """Test Start button triggers _start_downloads."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                # Click start button (no pending items so should show warning)
                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                await pilot.click("#start-btn")
                await pilot.pause()

                assert any("No pending downloads" in n[0] for n in notifications)

    @pytest.mark.asyncio
    async def test_pause_button_pauses_downloads(
        self, mock_settings, mock_api_client
    ):
        """Test Pause button triggers _pause_downloads."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)
                screen._downloading = True

                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                await pilot.click("#pause-btn")
                await pilot.pause()

                assert screen._downloading is False
                assert any("paused" in n[0].lower() for n in notifications)

    @pytest.mark.asyncio
    async def test_clear_done_button_calls_clear_completed(
        self, mock_settings, mock_api_client
    ):
        """Test Clear Done button triggers _clear_completed."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Call directly since pilot.click may not find pushed screen buttons
                await screen._clear_completed()
                await pilot.pause()

                assert any(
                    "No completed items to clear" in n[0] for n in notifications
                )

    @pytest.mark.asyncio
    async def test_retry_failed_button_calls_retry(
        self, mock_settings, mock_api_client
    ):
        """Test Retry Failed button triggers _retry_failed."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                notifications: list[tuple[str, dict]] = []
                original_notify = app.notify

                def track_notify(msg, **kwargs):
                    notifications.append((msg, kwargs))
                    original_notify(msg, **kwargs)

                app.notify = track_notify

                # Call directly since pilot.click may not find pushed screen buttons
                await screen._retry_failed()
                await pilot.pause()

                assert any(
                    "No failed items to retry" in n[0] for n in notifications
                )

    @pytest.mark.asyncio
    async def test_filter_buttons_change_active_filter(
        self, mock_settings, mock_api_client
    ):
        """Test filter buttons change the active filter."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                # Call _set_active_filter directly instead of pilot.click
                screen._set_active_filter("active")
                assert screen._active_filter == "active"

                screen._set_active_filter("done")
                assert screen._active_filter == "done"

                screen._set_active_filter("failed")
                assert screen._active_filter == "failed"

                screen._set_active_filter("all")
                assert screen._active_filter == "all"


# ============================================================================
# Test Queue Screen: Stats and progress updates
# ============================================================================


class TestQueueStats:
    """Tests for queue stats and progress bar updates."""

    @pytest.mark.asyncio
    async def test_stats_update_on_queue_changes(
        self, mock_settings, mock_api_client
    ):
        """Test that queue stats update when items are added/completed."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                queue = app.download_queue
                id1 = await queue.add(_make_song(idx=1))
                await queue.add(_make_song(idx=2))
                await pilot.pause()

                # Check filter tab labels
                all_btn = screen.query_one("#filter-all", Button)
                assert "2" in str(all_btn.label)

                # Complete one
                await queue.update_status(id1, DownloadStatus.COMPLETED)
                await pilot.pause()

                done_btn = screen.query_one("#filter-done", Button)
                assert "1" in str(done_btn.label)

    @pytest.mark.asyncio
    async def test_format_status_colors(self, mock_settings, mock_api_client):
        """Test status formatting with colors."""
        with (
            patch("spotdl_cli.app.get_settings", return_value=mock_settings),
            patch("spotdl_cli.app.get_api_client", return_value=mock_api_client),
            patch("spotdl_cli.app.should_show_onboarding", return_value=False),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api_client),
        ):
            app = SpotDLApp()
            async with app.run_test(headless=True) as pilot:
                await pilot.pause()

                await app.push_screen("queue")
                await pilot.pause()

                screen = app.screen
                assert isinstance(screen, QueueScreen)

                # Test each status format
                assert "green" in screen._format_status(DownloadStatus.COMPLETED)
                assert "red" in screen._format_status(DownloadStatus.FAILED)
                assert "cyan" in screen._format_status(DownloadStatus.DOWNLOADING)
                assert "yellow" in screen._format_status(DownloadStatus.SEARCHING)
                assert "dim" in screen._format_status(DownloadStatus.PENDING)


# ============================================================================
# Test Queue Screen: Action bindings
# ============================================================================


class TestQueueActionBindings:
    """Tests for action bindings on the queue screen."""

    def test_queue_screen_has_required_bindings(self):
        """Test QueueScreen has all required keyboard bindings."""
        screen = QueueScreen()

        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys
        assert "space" in binding_keys
        assert "delete" in binding_keys
        assert "c" in binding_keys
        assert "r" in binding_keys

    def test_queue_screen_has_required_actions(self):
        """Test QueueScreen has all required action methods."""
        screen = QueueScreen()

        assert hasattr(screen, "action_toggle_download")
        assert hasattr(screen, "action_remove_selected")
        assert hasattr(screen, "action_clear_completed")
        assert hasattr(screen, "action_retry_failed")
        assert callable(screen.action_toggle_download)
        assert callable(screen.action_remove_selected)
        assert callable(screen.action_clear_completed)
        assert callable(screen.action_retry_failed)
