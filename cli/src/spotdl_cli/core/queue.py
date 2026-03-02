"""Download queue management for SpotDL CLI."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from spotdl_cli.core.types import (
    DownloadItem,
    DownloadResult,
    DownloadStatus,
    Song,
)

logger = logging.getLogger(__name__)


@dataclass
class QueueEvent:
    """Event emitted by the queue."""

    type: str
    item_id: str
    data: dict[str, Any] | None = None


class DownloadQueue:
    """
    Manages the download queue.

    Features:
    - Add/remove items
    - Priority queue (can reorder)
    - Event callbacks for UI updates
    - Concurrent download limit
    """

    def __init__(self, max_concurrent: int = 4) -> None:
        """
        Initialize the download queue.

        Args:
            max_concurrent: Maximum concurrent downloads
        """
        self._items: dict[str, DownloadItem] = {}
        self._order: list[str] = []  # Item IDs in order
        self._max_concurrent = max_concurrent
        self._active_downloads: set[str] = set()
        self._callbacks: list[Callable[[QueueEvent], None]] = []
        self._lock = asyncio.Lock()

    @property
    def items(self) -> list[DownloadItem]:
        """Get all items in queue order."""
        return [self._items[id_] for id_ in self._order if id_ in self._items]

    @property
    def pending_items(self) -> list[DownloadItem]:
        """Get pending items."""
        return [
            item for item in self.items
            if item.status == DownloadStatus.PENDING
        ]

    @property
    def active_items(self) -> list[DownloadItem]:
        """Get currently downloading items."""
        return [
            item for item in self.items
            if item.status in (
                DownloadStatus.SEARCHING,
                DownloadStatus.DOWNLOADING,
                DownloadStatus.CONVERTING,
                DownloadStatus.EMBEDDING,
            )
        ]

    @property
    def completed_items(self) -> list[DownloadItem]:
        """Get completed items."""
        return [
            item for item in self.items
            if item.status == DownloadStatus.COMPLETED
        ]

    @property
    def failed_items(self) -> list[DownloadItem]:
        """Get failed items."""
        return [
            item for item in self.items
            if item.status == DownloadStatus.FAILED
        ]

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._items) == 0

    @property
    def total_count(self) -> int:
        """Get total item count."""
        return len(self._items)

    @property
    def pending_count(self) -> int:
        """Get pending item count."""
        return len(self.pending_items)

    @property
    def active_count(self) -> int:
        """Get active download count."""
        return len(self._active_downloads)

    def add_callback(self, callback: Callable[[QueueEvent], None]) -> None:
        """Add an event callback."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[QueueEvent], None]) -> None:
        """Remove an event callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _emit(self, event: QueueEvent) -> None:
        """Emit an event to all callbacks."""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def add(
        self,
        song: Song,
        result: DownloadResult | None = None,
        priority: bool = False,
    ) -> str:
        """
        Add a song to the queue.

        Args:
            song: Song to download
            result: Pre-matched download result (optional)
            priority: Add to front of queue

        Returns:
            Item ID
        """
        async with self._lock:
            item_id = str(uuid4())

            item = DownloadItem(
                song=song,
                result=result,
                status=DownloadStatus.PENDING,
                created_at=datetime.now(),
            )

            self._items[item_id] = item

            if priority:
                self._order.insert(0, item_id)
            else:
                self._order.append(item_id)

            self._emit(QueueEvent("added", item_id, {"song": song.display_name}))
            logger.info(f"Added to queue: {song.display_name}")

            return item_id

    async def add_many(self, songs: list[Song]) -> list[str]:
        """
        Add multiple songs to the queue.

        Args:
            songs: Songs to add

        Returns:
            List of item IDs
        """
        item_ids = []
        for song in songs:
            item_id = await self.add(song)
            item_ids.append(item_id)
        return item_ids

    async def remove(self, item_id: str) -> bool:
        """
        Remove an item from the queue.

        Args:
            item_id: Item ID to remove

        Returns:
            True if removed
        """
        async with self._lock:
            if item_id not in self._items:
                return False

            # Don't remove active downloads
            if item_id in self._active_downloads:
                logger.warning(f"Cannot remove active download: {item_id}")
                return False

            item = self._items.pop(item_id)
            if item_id in self._order:
                self._order.remove(item_id)

            self._emit(QueueEvent("removed", item_id))
            logger.info(f"Removed from queue: {item.song.display_name}")

            return True

    async def clear_completed(self) -> int:
        """
        Remove all completed items.

        Returns:
            Number of items removed
        """
        removed = 0
        for item in self.completed_items:
            item_id = next(
                (id_ for id_, i in self._items.items() if i is item),
                None,
            )
            if item_id and await self.remove(item_id):
                removed += 1
        return removed

    async def clear_failed(self) -> int:
        """
        Remove all failed items.

        Returns:
            Number of items removed
        """
        removed = 0
        for item in self.failed_items:
            item_id = next(
                (id_ for id_, i in self._items.items() if i is item),
                None,
            )
            if item_id and await self.remove(item_id):
                removed += 1
        return removed

    async def clear_all(self) -> None:
        """Clear all non-active items."""
        async with self._lock:
            # Keep only active downloads
            active_items = {
                id_: item for id_, item in self._items.items()
                if id_ in self._active_downloads
            }
            self._items = active_items
            self._order = [id_ for id_ in self._order if id_ in active_items]

            self._emit(QueueEvent("cleared", ""))

    def get_item(self, item_id: str) -> DownloadItem | None:
        """Get an item by ID."""
        return self._items.get(item_id)

    def get_item_id(self, item: DownloadItem) -> str | None:
        """Get the ID for an item."""
        for id_, i in self._items.items():
            if i is item:
                return id_
        return None

    async def update_status(
        self,
        item_id: str,
        status: DownloadStatus,
        progress: float | None = None,
        speed: str | None = None,
        eta: str | None = None,
        error: str | None = None,
    ) -> None:
        """
        Update item status.

        Args:
            item_id: Item ID
            status: New status
            progress: Download progress (0-100)
            speed: Download speed string
            eta: ETA string
            error: Error message (for failed status)
        """
        item = self._items.get(item_id)
        if not item:
            return

        item.status = status

        if progress is not None:
            item.progress = progress
        if speed is not None:
            item.speed = speed
        if eta is not None:
            item.eta = eta
        if error is not None:
            item.error = error

        # Track active downloads
        if status in (
            DownloadStatus.SEARCHING,
            DownloadStatus.DOWNLOADING,
            DownloadStatus.CONVERTING,
            DownloadStatus.EMBEDDING,
        ):
            if item.started_at is None:
                item.started_at = datetime.now()
            self._active_downloads.add(item_id)
        elif status in (DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED):
            item.completed_at = datetime.now()
            self._active_downloads.discard(item_id)

        self._emit(QueueEvent(
            "status_changed",
            item_id,
            {"status": status.value, "progress": item.progress},
        ))

    async def set_result(self, item_id: str, result: DownloadResult) -> None:
        """Set the download result for an item."""
        item = self._items.get(item_id)
        if item:
            item.result = result
            self._emit(QueueEvent("result_set", item_id))

    async def get_next_pending(self) -> tuple[str, DownloadItem] | None:
        """
        Get the next pending item to download.

        Marks the item as SEARCHING immediately to prevent double-dispatch.
        Concurrency is controlled by the caller via semaphore.

        Returns:
            Tuple of (item_id, item) or None if no pending items
        """
        async with self._lock:
            for item_id in self._order:
                item = self._items.get(item_id)
                if item and item.status == DownloadStatus.PENDING:
                    item.status = DownloadStatus.SEARCHING
                    self._active_downloads.add(item_id)
                    return (item_id, item)

        return None

    async def move_to_top(self, item_id: str) -> bool:
        """Move an item to the top of the queue."""
        async with self._lock:
            if item_id not in self._order:
                return False

            self._order.remove(item_id)
            self._order.insert(0, item_id)

            self._emit(QueueEvent("reordered", item_id))
            return True

    async def move_to_bottom(self, item_id: str) -> bool:
        """Move an item to the bottom of the queue."""
        async with self._lock:
            if item_id not in self._order:
                return False

            self._order.remove(item_id)
            self._order.append(item_id)

            self._emit(QueueEvent("reordered", item_id))
            return True
