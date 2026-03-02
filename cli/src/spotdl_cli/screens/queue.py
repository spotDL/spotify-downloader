"""Download queue screen for SpotDL CLI."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

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

from spotdl_cli.widgets import CoverArt

from spotdl_cli.config import get_settings
from spotdl_cli.core import (
    APIError,
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

    TITLE = "Downloads"

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
        self._poll_tasks: dict[str, asyncio.Task[None]] = {}
        self._remote_downloads_enabled: bool | None = None
        self._active_filter: str = "all"

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

            # Filter tabs
            with Horizontal(id="queue-filter-tabs"):
                yield Button("All (0)", id="filter-all", classes="filter-btn active")
                yield Button("Active (0)", id="filter-active", classes="filter-btn")
                yield Button("Done (0)", id="filter-done", classes="filter-btn")
                yield Button("Failed (0)", id="filter-failed", classes="filter-btn")

            # Overall progress
            yield ProgressBar(id="overall-progress", total=100, show_eta=False)

            # Content split
            with Horizontal(id="queue-content"):
                with Vertical(id="queue-main"):
                    # Empty state
                    with Vertical(id="queue-empty-state", classes="empty-state hidden"):
                        yield Static("No downloads yet", classes="empty-title")
                        yield Static(
                            "Search for music and add tracks to the download queue.",
                            classes="empty-subtitle",
                        )
                        yield Button(
                            "Go to Search",
                            id="go-search-btn",
                            variant="primary",
                        )

                    # Complete notice
                    with Vertical(id="queue-complete-notice", classes="hidden"):
                        yield Static("", id="complete-notice-text")

                    with Vertical(id="queue-table-container"):
                        yield DataTable(id="queue-table")

                with Vertical(id="queue-sidebar"):
                    with Vertical(classes="card", id="queue-now-card"):
                        yield Static("Now Downloading", classes="card-title")
                        yield CoverArt(id="queue-cover", classes="cover-placeholder")
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
            "Platform",
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
        for task in self._poll_tasks.values():
            task.cancel()
        self._poll_tasks.clear()

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

    def _get_filtered_items(self) -> list:
        """Get queue items filtered by the active filter."""
        queue = self.spotdl_app.download_queue
        items = list(queue.items)

        active_statuses = {
            DownloadStatus.SEARCHING,
            DownloadStatus.DOWNLOADING,
            DownloadStatus.CONVERTING,
            DownloadStatus.EMBEDDING,
            DownloadStatus.PENDING,
        }

        if self._active_filter == "active":
            return [i for i in items if i.status in active_statuses]
        elif self._active_filter == "done":
            return [i for i in items if i.status == DownloadStatus.COMPLETED]
        elif self._active_filter == "failed":
            return [i for i in items if i.status == DownloadStatus.FAILED]
        return items

    def _get_platform_mapping(self, item) -> str:
        """Get platform mapping string for an item."""
        source = "SPOTIFY"
        target = "YOUTUBE"
        if item.result and item.result.platform:
            target = item.result.platform.value.upper()
        return f"{source} \u2192 {target}"

    def _update_table(self) -> None:
        """Update the queue table."""
        table = self.query_one("#queue-table", DataTable)
        table.clear()

        queue = self.spotdl_app.download_queue
        filtered = self._get_filtered_items()

        # Toggle empty state
        empty_state = self.query_one("#queue-empty-state")
        if not queue.items:
            empty_state.remove_class("hidden")
            table.add_class("hidden")
        else:
            empty_state.add_class("hidden")
            table.remove_class("hidden")

        for item in filtered:
            item_id = queue.get_item_id(item)
            progress = f"{item.progress:.0f}%" if item.progress > 0 else "-"
            status = self._format_status(item.status)
            eta = item.eta or "-"
            platform = self._get_platform_mapping(item)

            table.add_row(
                item.song.name,
                item.song.artist,
                platform,
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
            platform = self._get_platform_mapping(item)

            # Update cells (columns: Title, Artist, Platform, Status, Progress, Speed, ETA)
            table.update_cell_at((row_key, 2), platform)
            table.update_cell_at((row_key, 3), status)
            table.update_cell_at((row_key, 4), progress)
            table.update_cell_at((row_key, 5), item.speed or "-")
            table.update_cell_at((row_key, 6), eta)
        except Exception:
            # Row not found, refresh table
            self._update_table()

    def _update_stats(self) -> None:
        """Update queue statistics."""
        queue = self.spotdl_app.download_queue
        stats = self.query_one("#queue-stats", Static)
        summary = self.query_one("#queue-summary", Static)

        total = len(queue.items)
        pending = queue.pending_count
        active = queue.active_count
        completed = len(queue.completed_items)
        failed = len(queue.failed_items)
        active_total = pending + active

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

        # Update filter tab counts
        try:
            self.query_one("#filter-all", Button).label = f"All ({total})"
            self.query_one("#filter-active", Button).label = f"Active ({active_total})"
            self.query_one("#filter-done", Button).label = f"Done ({completed})"
            self.query_one("#filter-failed", Button).label = f"Failed ({failed})"
        except Exception:
            pass

        # Update overall progress bar
        try:
            overall = self.query_one("#overall-progress", ProgressBar)
            if total > 0:
                overall_pct = (completed / total) * 100
                overall.update(progress=overall_pct)
            else:
                overall.update(progress=0)
        except Exception:
            pass

        # Show/hide complete notice
        try:
            notice = self.query_one("#queue-complete-notice")
            notice_text = self.query_one("#complete-notice-text", Static)
            if total > 0 and active_total == 0 and completed > 0:
                settings = get_settings()
                notice_text.update(
                    f"All downloads complete! Files saved to: {settings.output_dir}"
                )
                notice.remove_class("hidden")
            else:
                notice.add_class("hidden")
        except Exception:
            pass

        if active == 0:
            current = self.query_one("#current-download", Static)
            cover = self.query_one("#queue-cover", CoverArt)
            progress = self.query_one("#download-progress", ProgressBar)
            meta = self.query_one("#current-meta", Static)
            current.update("Idle")
            cover.cover_url = None
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
        cover = self.query_one("#queue-cover", CoverArt)
        progress = self.query_one("#download-progress", ProgressBar)
        meta = self.query_one("#current-meta", Static)

        cover.cover_url = item.song.cover_url
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

    def _set_active_filter(self, filter_name: str) -> None:
        """Set the active filter tab."""
        self._active_filter = filter_name
        for btn_id in ("filter-all", "filter-active", "filter-done", "filter-failed"):
            btn = self.query_one(f"#{btn_id}", Button)
            if btn_id == f"filter-{filter_name}":
                btn.add_class("active")
            else:
                btn.remove_class("active")
        self._update_table()

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
        elif event.button.id == "go-search-btn":
            await self.app.push_screen("search")
        elif event.button.id == "filter-all":
            self._set_active_filter("all")
        elif event.button.id == "filter-active":
            self._set_active_filter("active")
        elif event.button.id == "filter-done":
            self._set_active_filter("done")
        elif event.button.id == "filter-failed":
            self._set_active_filter("failed")

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
        """Main download loop — dispatches concurrent download tasks."""
        settings = get_settings()
        semaphore = asyncio.Semaphore(settings.threads)
        queue = self.spotdl_app.download_queue

        while self._downloading:
            next_item = await queue.get_next_pending()
            if not next_item:
                if queue.pending_count == 0 and queue.active_count == 0:
                    break
                await self._sleep(0.5)
                continue

            item_id, item = next_item

            # Spawn a concurrent task under the semaphore
            asyncio.create_task(  # noqa: RUF006
                self._download_single(item_id, item, semaphore)
            )

        self.notify("Download loop stopped")

    async def _download_single(
        self,
        item_id: str,
        item: object,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Download a single item under concurrency control."""
        queue = self.spotdl_app.download_queue
        manager = self.spotdl_app.download_manager
        use_remote = await self._use_remote_downloads()

        result = await self._resolve_download_result(item_id, item)
        if not result:
            await queue.update_status(
                item_id,
                DownloadStatus.FAILED,
                error="No download source found",
            )
            return

        if use_remote:
            success = await self._start_remote_download(item_id, item, result)
            if success:
                return
            # Fall through to local download

        # Create status callback
        def status_callback(
            id_: str,
            status: DownloadStatus,
            progress: float,
            speed: str,
            eta: str,
            error: str | None,
        ) -> None:
            self.call_later(
                self._update_download_status,
                id_,
                status,
                progress,
                speed,
                eta,
                error,
            )

        async with semaphore:
            await manager.download_item(item_id, item, status_callback)

    async def _use_remote_downloads(self) -> bool:
        """Check if remote downloads are available."""
        if not self.spotdl_app.is_online:
            return False
        if self._remote_downloads_enabled is not None:
            return self._remote_downloads_enabled
        try:
            await self.spotdl_app.api_client.list_downloads()
            self._remote_downloads_enabled = True
        except APIError as e:
            if "disabled" in str(e).lower():
                self._remote_downloads_enabled = False
            else:
                self._remote_downloads_enabled = False
        return self._remote_downloads_enabled

    async def _resolve_download_result(
        self,
        item_id: str,
        item,
    ) -> DownloadResult | None:
        """Resolve a download result for an item."""
        queue = self.spotdl_app.download_queue
        result = item.result if item else None
        if result:
            return result

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
                result = await self._offline_matcher.get_best_match(item.song)
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

        return result

    async def _start_remote_download(
        self,
        item_id: str,
        item,
        result: DownloadResult,
    ) -> bool:
        """Start a remote backend download."""
        settings = get_settings()
        queue = self.spotdl_app.download_queue

        try:
            request = {
                "url": result.url,
                "title": item.song.name,
                "artist": ", ".join(item.song.artists),
                "album": item.song.album_name or None,
                "cover_url": item.song.cover_url or None,
                "duration": item.song.duration,
                "output_format": settings.audio_format,
                "quality": (
                    "320"
                    if settings.audio_quality == "best"
                    else settings.audio_quality.replace("k", "")
                ),
                "embed_metadata": settings.embed_metadata,
                "embed_lyrics": settings.embed_lyrics,
                "embed_cover": settings.embed_cover,
            }
            response = await self.spotdl_app.api_client.start_download(request)
            download_id = response.get("download_id")
            if not download_id:
                raise APIError("Download ID missing")

            item.download_id = download_id
            item.remote = True
            await queue.update_status(item_id, DownloadStatus.DOWNLOADING, progress=0.0)
            self._start_remote_poll(item_id, download_id)
            return True
        except APIError as e:
            logger.warning(f"Remote download unavailable: {e}")
            self._remote_downloads_enabled = False
            await queue.update_status(
                item_id, DownloadStatus.PENDING, error=str(e)
            )
            return False

    def _start_remote_poll(self, item_id: str, download_id: str) -> None:
        """Start polling a remote download."""
        if item_id in self._poll_tasks:
            self._poll_tasks[item_id].cancel()
        task = asyncio.create_task(
            self._poll_remote_download(item_id, download_id)
        )
        self._poll_tasks[item_id] = task

    async def _poll_remote_download(self, item_id: str, download_id: str) -> None:
        """Poll backend download status and update queue."""
        queue = self.spotdl_app.download_queue
        status_map = {
            "pending": DownloadStatus.SEARCHING,
            "downloading": DownloadStatus.DOWNLOADING,
            "processing": DownloadStatus.CONVERTING,
            "completed": DownloadStatus.COMPLETED,
            "failed": DownloadStatus.FAILED,
            "cancelled": DownloadStatus.CANCELLED,
        }

        while True:
            try:
                progress = await self.spotdl_app.api_client.get_download_status(
                    download_id
                )
            except APIError as e:
                await queue.update_status(
                    item_id, DownloadStatus.FAILED, error=str(e)
                )
                break

            status = progress.get("status", "pending")
            mapped = status_map.get(status, DownloadStatus.DOWNLOADING)
            await queue.update_status(
                item_id,
                mapped,
                progress=progress.get("progress", 0.0),
                speed=progress.get("speed") or "",
                eta=progress.get("eta") or "",
                error=progress.get("error"),
            )

            if status in ("completed", "failed", "cancelled"):
                if status == "completed":
                    await self._download_remote_file(item_id, download_id, progress)
                break

            await asyncio.sleep(1)

    async def _download_remote_file(
        self,
        item_id: str,
        download_id: str,
        progress: dict[str, Any],
    ) -> None:
        """Download file from backend after completion."""
        queue = self.spotdl_app.download_queue
        item = queue.get_item(item_id)
        if not item:
            return

        settings = get_settings()
        ext = settings.audio_format
        filename = progress.get("filename") or f"{item.song.display_name}.{ext}"
        output_path = Path(settings.output_dir) / filename
        try:
            await self.spotdl_app.api_client.download_file(download_id, output_path)
            item.output_path = output_path
            await queue.update_status(
                item_id, DownloadStatus.COMPLETED, progress=100.0
            )
        except APIError as e:
            await queue.update_status(
                item_id, DownloadStatus.FAILED, error=str(e)
            )

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
            item = queue.get_item(item_id)
            if item and item.download_id and item.status in (
                DownloadStatus.SEARCHING,
                DownloadStatus.DOWNLOADING,
                DownloadStatus.CONVERTING,
                DownloadStatus.EMBEDDING,
            ):
                try:
                    await self.spotdl_app.api_client.cancel_download(item.download_id)
                except APIError as e:
                    self.notify(f"Cancel failed: {e}", severity="error")
                    return
                if item_id in self._poll_tasks:
                    self._poll_tasks[item_id].cancel()
                    self._poll_tasks.pop(item_id, None)
                await queue.update_status(item_id, DownloadStatus.CANCELLED)
                self.notify("Download cancelled")
                return

            if await queue.remove(item_id):
                if item_id in self._poll_tasks:
                    self._poll_tasks[item_id].cancel()
                    self._poll_tasks.pop(item_id, None)
                self.notify("Item removed")
            else:
                self.notify("Cannot remove active download", severity="warning")
        except Exception as e:
            logger.warning(f"Failed to remove item: {e}")

    async def _clear_completed(self) -> None:
        """Clear completed downloads."""
        queue = self.spotdl_app.download_queue
        count = await queue.clear_completed()
        for item_id in list(self._poll_tasks.keys()):
            if queue.get_item(item_id) is None:
                self._poll_tasks[item_id].cancel()
                self._poll_tasks.pop(item_id, None)
        self.notify(f"Cleared {count} completed items")

    async def _retry_failed(self) -> None:
        """Retry failed downloads."""
        queue = self.spotdl_app.download_queue
        count = 0

        for item in queue.failed_items:
            item_id = queue.get_item_id(item)
            if item_id:
                item.download_id = None
                item.remote = False
                item.error = None
                item.progress = 0.0
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
