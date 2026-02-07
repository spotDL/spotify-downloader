"""Download queue screen for SpotDL CLI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    ProgressBar,
    Static,
)

from spotdl_cli.core import (
    DownloadResult,
    DownloadStatus,
    QueueEvent,
    get_offline_matcher,
)
from spotdl_cli.core.types import TargetPlatform

if TYPE_CHECKING:
    from spotdl_cli.app import SpotDLApp

logger = logging.getLogger(__name__)


class QueueScreen(Screen[None]):
    """Download queue management screen."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("space", "toggle_download", "Start/Pause"),
        Binding("delete", "remove_selected", "Remove"),
        Binding("c", "clear_completed", "Clear Done"),
        Binding("r", "retry_failed", "Retry Failed"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._downloading = False
        self._download_task = None
        self._offline_matcher = get_offline_matcher()

    @property
    def spotdl_app(self) -> SpotDLApp:
        """Get the typed app instance."""
        from spotdl_cli.app import SpotDLApp
        assert isinstance(self.app, SpotDLApp)
        return self.app

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        with Vertical(id="queue-container"):
            # Header
            with Horizontal(id="queue-header"):
                with Vertical(id="queue-title-block"):
                    yield Static("Downloads", id="queue-title")
                    yield Static("", id="queue-stats", classes="status-muted")
                with Horizontal(id="queue-actions"):
                    yield Button("Start", id="start-btn", variant="success")
                    yield Button("Pause", id="pause-btn", variant="warning")
                    yield Button("Remove", id="remove-btn", variant="error")
                    yield Button("Clear Done", id="clear-done-btn")
                    yield Button("Retry Failed", id="retry-failed-btn")

            # Content split
            with Horizontal(id="queue-content"):
                with Vertical(id="queue-main"):
                    with Container(id="queue-table-container"):
                        yield DataTable(id="queue-table")

                with Vertical(id="queue-sidebar"):
                    with Vertical(classes="card", id="queue-now-card"):
                        yield Static("Now Downloading", classes="card-title")
                        yield Static("", id="current-download")
                        yield ProgressBar(id="download-progress", total=100, show_eta=False)
                        yield Static("", id="current-meta", classes="status-muted")

                    with Vertical(classes="card", id="queue-summary-card"):
                        yield Static("Summary", classes="card-title")
                        yield Static("", id="queue-summary")

    async def on_mount(self) -> None:
        """Handle screen mount."""
        # Setup queue table
        table = self.query_one("#queue-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(
            "Title",
            "Artist",
            "Status",
            "Progress",
            "Speed",
            "ETA",
        )

        # Subscribe to queue events
        queue = self.spotdl_app.download_queue
        queue.add_callback(self._on_queue_event)

        # Initial update
        self._update_table()
        self._update_stats()

    async def on_unmount(self) -> None:
        """Handle screen unmount."""
        # Unsubscribe from queue events
        queue = self.spotdl_app.download_queue
        queue.remove_callback(self._on_queue_event)

    def _on_queue_event(self, event: QueueEvent) -> None:
        """Handle queue events."""
        # Schedule UI update on the main thread
        self.call_later(self._handle_event, event)

    def _handle_event(self, event: QueueEvent) -> None:
        """Handle a queue event on the main thread."""
        if event.type in ("added", "removed", "cleared", "reordered"):
            self._update_table()
            self._update_stats()
        elif event.type == "status_changed":
            self._update_item(event.item_id, event.data)
            self._update_stats()
            self._update_progress(event.item_id)

    def _update_table(self) -> None:
        """Update the queue table."""
        table = self.query_one("#queue-table", DataTable)
        table.clear()

        queue = self.spotdl_app.download_queue
        for item in queue.items:
            item_id = queue.get_item_id(item)
            progress = f"{item.progress:.0f}%" if item.progress > 0 else "-"
            status = self._format_status(item.status)
            eta = item.eta or "-"

            table.add_row(
                item.song.name,
                item.song.artist,
                status,
                progress,
                item.speed or "-",
                eta,
                key=item_id,
            )

    def _update_item(self, item_id: str, data: dict | None) -> None:
        """Update a single item in the table."""
        table = self.query_one("#queue-table", DataTable)
        queue = self.spotdl_app.download_queue
        item = queue.get_item(item_id)

        if not item:
            return

        # Find the row and update it
        try:
            row_key = table.get_row_index(item_id)
            progress = f"{item.progress:.0f}%" if item.progress > 0 else "-"
            status = self._format_status(item.status)
            eta = item.eta or "-"

            # Update cells
            table.update_cell_at((row_key, 2), status)
            table.update_cell_at((row_key, 3), progress)
            table.update_cell_at((row_key, 4), item.speed or "-")
            table.update_cell_at((row_key, 5), eta)
        except Exception:
            # Row not found, refresh table
            self._update_table()

    def _update_stats(self) -> None:
        """Update queue statistics."""
        queue = self.spotdl_app.download_queue
        stats = self.query_one("#queue-stats", Static)
        summary = self.query_one("#queue-summary", Static)

        pending = queue.pending_count
        active = queue.active_count
        completed = len(queue.completed_items)
        failed = len(queue.failed_items)

        stats.update(
            f"Pending: {pending} | Active: {active} | "
            f"Done: {completed} | Failed: {failed}"
        )
        summary.update(
            f"[bold]{pending}[/bold] pending\n"
            f"[bold]{active}[/bold] active\n"
            f"[bold]{completed}[/bold] done\n"
            f"[bold]{failed}[/bold] failed"
        )

        if active == 0:
            current = self.query_one("#current-download", Static)
            progress = self.query_one("#download-progress", ProgressBar)
            meta = self.query_one("#current-meta", Static)
            current.update("Idle")
            progress.update(progress=0)
            meta.update("")

    def _update_progress(self, item_id: str) -> None:
        """Update progress bar for current download."""
        queue = self.spotdl_app.download_queue
        item = queue.get_item(item_id)

        if not item:
            return

        # Only show progress for active downloads
        if item.status not in (
            DownloadStatus.DOWNLOADING,
            DownloadStatus.CONVERTING,
            DownloadStatus.EMBEDDING,
        ):
            return

        current = self.query_one("#current-download", Static)
        progress = self.query_one("#download-progress", ProgressBar)
        meta = self.query_one("#current-meta", Static)

        current.update(item.song.display_name)
        progress.update(progress=item.progress)
        meta.update(f"{item.status.value.title()} • {item.speed or '-'} • {item.eta or '-'}")

    def _format_status(self, status: DownloadStatus) -> str:
        """Format status string with color."""
        colors = {
            DownloadStatus.PENDING: "dim",
            DownloadStatus.SEARCHING: "yellow",
            DownloadStatus.DOWNLOADING: "cyan",
            DownloadStatus.CONVERTING: "blue",
            DownloadStatus.EMBEDDING: "blue",
            DownloadStatus.COMPLETED: "green",
            DownloadStatus.FAILED: "red",
            DownloadStatus.CANCELLED: "dim",
        }
        color = colors.get(status, "white")
        return f"[{color}]{status.value.title()}[/{color}]"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "start-btn":
            await self._start_downloads()
        elif event.button.id == "pause-btn":
            await self._pause_downloads()
        elif event.button.id == "remove-btn":
            await self._remove_selected()
        elif event.button.id == "clear-done-btn":
            await self._clear_completed()
        elif event.button.id == "retry-failed-btn":
            await self._retry_failed()

    async def _start_downloads(self) -> None:
        """Start downloading."""
        if self._downloading:
            return

        self._downloading = True
        self.notify("Starting downloads...")

        # Start the download loop
        self._download_task = self.run_worker(self._download_loop())

    async def _pause_downloads(self) -> None:
        """Pause downloading."""
        self._downloading = False
        self.notify("Downloads paused")

    async def _download_loop(self) -> None:
        """Main download loop."""
        queue = self.spotdl_app.download_queue
        manager = self.spotdl_app.download_manager

        while self._downloading:
            # Get next pending item
            next_item = await queue.get_next_pending()
            if not next_item:
                # No more items or at max concurrent
                await self._sleep(0.5)
                continue

            item_id, item = next_item

            # Update status to searching
            await queue.update_status(item_id, DownloadStatus.SEARCHING)

            # Find matches if not already found
            if not item.result:
                result = None

                # Try online first if available
                if self.spotdl_app.is_online:
                    try:
                        matches = await self.spotdl_app.api_client.find_matches(item.song)
                        if matches:
                            result = matches[0]
                    except Exception as e:
                        logger.warning(f"Online match finding failed: {e}")

                # Fallback to offline matching
                if result is None:
                    try:
                        result = await self._offline_matcher.get_best_match(
                            item.song, min_score=60.0
                        )
                    except Exception as e:
                        logger.warning(f"Offline match finding failed: {e}")

                # If song is from YouTube, create result directly
                if result is None and "youtube.com" in item.song.url:
                    result = DownloadResult(
                        name=item.song.name,
                        artists=item.song.artists,
                        artist=item.song.artist,
                        duration=item.song.duration,
                        platform=TargetPlatform.YOUTUBE,
                        platform_id=item.song.platform_id,
                        url=item.song.url,
                        verified=False,
                        score=100.0,
                        cover_url=item.song.cover_url,
                    )

                if result:
                    await queue.set_result(item_id, result)
                    item = queue.get_item(item_id)  # Refresh

            if not item or not item.result:
                await queue.update_status(
                    item_id,
                    DownloadStatus.FAILED,
                    error="No download source found",
                )
                continue

            # Create status callback
            def status_callback(
                id_: str,
                status: DownloadStatus,
                progress: float,
                speed: str,
                eta: str,
                error: str | None,
            ) -> None:
                # Use call_soon_threadsafe for thread safety
                self.call_later(
                    self._update_download_status,
                    id_,
                    status,
                    progress,
                    speed,
                    eta,
                    error,
                )

            # Start download
            await manager.download_item(item_id, item, status_callback)

        self.notify("Download loop stopped")

    def _update_download_status(
        self,
        item_id: str,
        status: DownloadStatus,
        progress: float,
        speed: str,
        eta: str,
        error: str | None,
    ) -> None:
        """Update download status (called from callback)."""
        queue = self.spotdl_app.download_queue
        # Fire-and-forget async call - task is managed by event loop
        import asyncio
        asyncio.create_task(  # noqa: RUF006
            queue.update_status(item_id, status, progress, speed, eta, error)
        )

    async def _sleep(self, seconds: float) -> None:
        """Sleep for the given number of seconds."""
        import asyncio
        await asyncio.sleep(seconds)

    async def _remove_selected(self) -> None:
        """Remove the selected item."""
        table = self.query_one("#queue-table", DataTable)

        if table.cursor_row is None:
            self.notify("No item selected", severity="warning")
            return

        # Get the row key (item_id)
        try:
            row_key = table.get_row_at(table.cursor_row)
            item_id = str(row_key.key)

            queue = self.spotdl_app.download_queue
            if await queue.remove(item_id):
                self.notify("Item removed")
            else:
                self.notify("Cannot remove active download", severity="warning")
        except Exception as e:
            logger.warning(f"Failed to remove item: {e}")

    async def _clear_completed(self) -> None:
        """Clear completed downloads."""
        queue = self.spotdl_app.download_queue
        count = await queue.clear_completed()
        self.notify(f"Cleared {count} completed items")

    async def _retry_failed(self) -> None:
        """Retry failed downloads."""
        queue = self.spotdl_app.download_queue
        count = 0

        for item in queue.failed_items:
            item_id = queue.get_item_id(item)
            if item_id:
                await queue.update_status(item_id, DownloadStatus.PENDING)
                count += 1

        self.notify(f"Retrying {count} failed items")

    def action_toggle_download(self) -> None:
        """Toggle download state."""
        if self._downloading:
            self.run_worker(self._pause_downloads())
        else:
            self.run_worker(self._start_downloads())

    def action_remove_selected(self) -> None:
        """Remove selected item."""
        self.run_worker(self._remove_selected())

    def action_clear_completed(self) -> None:
        """Clear completed items."""
        self.run_worker(self._clear_completed())

    def action_retry_failed(self) -> None:
        """Retry failed items."""
        self.run_worker(self._retry_failed())
