"""Tests for download queue."""

import pytest
from unittest.mock import MagicMock

from spotdl_cli.core.queue import DownloadQueue, QueueEvent
from spotdl_cli.core.types import (
    DownloadItem,
    DownloadResult,
    DownloadStatus,
    Song,
    TargetPlatform,
)


class TestDownloadQueue:
    """Tests for DownloadQueue class."""

    @pytest.fixture
    def queue(self) -> DownloadQueue:
        """Create a test queue."""
        return DownloadQueue(max_concurrent=2)

    @pytest.mark.asyncio
    async def test_add_song(self, queue: DownloadQueue, sample_song: Song) -> None:
        """Test adding a song to the queue."""
        item_id = await queue.add(sample_song)

        assert item_id is not None
        assert queue.total_count == 1
        assert queue.pending_count == 1

        item = queue.get_item(item_id)
        assert item is not None
        assert item.song == sample_song
        assert item.status == DownloadStatus.PENDING

    @pytest.mark.asyncio
    async def test_add_with_priority(self, queue: DownloadQueue, sample_song: Song) -> None:
        """Test adding a song with priority."""
        # Add first song
        id1 = await queue.add(sample_song)

        # Create second song
        song2 = Song(
            name="Priority Song",
            artists=["Artist"],
            artist="Artist",
            duration=100,
            platform=sample_song.platform,
            platform_id="priority123",
            url="https://example.com/priority",
        )

        # Add with priority
        id2 = await queue.add(song2, priority=True)

        # Priority song should be first
        items = queue.items
        assert items[0].song.name == "Priority Song"
        assert items[1].song.name == sample_song.name

    @pytest.mark.asyncio
    async def test_add_many(self, queue: DownloadQueue) -> None:
        """Test adding multiple songs."""
        songs = [
            Song(
                name=f"Song {i}",
                artists=["Artist"],
                artist="Artist",
                duration=100 + i,
                platform=_platform.SPOTIFY,
                platform_id=f"song{i}",
                url=f"https://example.com/song{i}",
            )
            for i in range(5)
        ]

        item_ids = await queue.add_many(songs)

        assert len(item_ids) == 5
        assert queue.total_count == 5

    @pytest.mark.asyncio
    async def test_remove_song(self, queue: DownloadQueue, sample_song: Song) -> None:
        """Test removing a song from queue."""
        item_id = await queue.add(sample_song)
        assert queue.total_count == 1

        removed = await queue.remove(item_id)
        assert removed is True
        assert queue.total_count == 0

    @pytest.mark.asyncio
    async def test_cannot_remove_active_download(
        self, queue: DownloadQueue, sample_song: Song
    ) -> None:
        """Test that active downloads cannot be removed."""
        item_id = await queue.add(sample_song)
        await queue.update_status(item_id, DownloadStatus.DOWNLOADING)

        removed = await queue.remove(item_id)
        assert removed is False
        assert queue.total_count == 1

    @pytest.mark.asyncio
    async def test_update_status(self, queue: DownloadQueue, sample_song: Song) -> None:
        """Test updating item status."""
        item_id = await queue.add(sample_song)

        await queue.update_status(
            item_id,
            DownloadStatus.DOWNLOADING,
            progress=50.0,
            speed="1.5 MB/s",
            eta="00:30",
        )

        item = queue.get_item(item_id)
        assert item is not None
        assert item.status == DownloadStatus.DOWNLOADING
        assert item.progress == 50.0
        assert item.speed == "1.5 MB/s"
        assert item.eta == "00:30"
        assert item.started_at is not None

    @pytest.mark.asyncio
    async def test_update_status_completed(
        self, queue: DownloadQueue, sample_song: Song
    ) -> None:
        """Test updating to completed status."""
        item_id = await queue.add(sample_song)
        await queue.update_status(item_id, DownloadStatus.DOWNLOADING)
        await queue.update_status(item_id, DownloadStatus.COMPLETED)

        item = queue.get_item(item_id)
        assert item is not None
        assert item.status == DownloadStatus.COMPLETED
        assert item.completed_at is not None
        assert queue.active_count == 0

    @pytest.mark.asyncio
    async def test_get_next_pending(self, queue: DownloadQueue, sample_song: Song) -> None:
        """Test getting next pending item."""
        item_id = await queue.add(sample_song)

        result = await queue.get_next_pending()
        assert result is not None
        assert result[0] == item_id

    @pytest.mark.asyncio
    async def test_get_next_pending_respects_max_concurrent(
        self, queue: DownloadQueue, sample_song: Song
    ) -> None:
        """Test that get_next_pending respects max concurrent limit."""
        # Add 3 songs
        ids = []
        for i in range(3):
            song = Song(
                name=f"Song {i}",
                artists=["Artist"],
                artist="Artist",
                duration=100,
                platform=sample_song.platform,
                platform_id=f"song{i}",
                url=f"https://example.com/song{i}",
            )
            ids.append(await queue.add(song))

        # Mark 2 as downloading (max_concurrent=2)
        await queue.update_status(ids[0], DownloadStatus.DOWNLOADING)
        await queue.update_status(ids[1], DownloadStatus.DOWNLOADING)

        # Should return None since at max concurrent
        result = await queue.get_next_pending()
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_completed(self, queue: DownloadQueue, sample_song: Song) -> None:
        """Test clearing completed items."""
        item_id = await queue.add(sample_song)
        await queue.update_status(item_id, DownloadStatus.COMPLETED)

        count = await queue.clear_completed()
        assert count == 1
        assert queue.total_count == 0

    @pytest.mark.asyncio
    async def test_clear_failed(self, queue: DownloadQueue, sample_song: Song) -> None:
        """Test clearing failed items."""
        item_id = await queue.add(sample_song)
        await queue.update_status(item_id, DownloadStatus.FAILED, error="Test error")

        count = await queue.clear_failed()
        assert count == 1
        assert queue.total_count == 0

    @pytest.mark.asyncio
    async def test_event_callbacks(self, queue: DownloadQueue, sample_song: Song) -> None:
        """Test event callbacks are called."""
        events: list[QueueEvent] = []
        queue.add_callback(lambda e: events.append(e))

        item_id = await queue.add(sample_song)

        assert len(events) == 1
        assert events[0].type == "added"
        assert events[0].item_id == item_id

    @pytest.mark.asyncio
    async def test_move_to_top(self, queue: DownloadQueue) -> None:
        """Test moving item to top of queue."""
        songs = [
            Song(
                name=f"Song {i}",
                artists=["Artist"],
                artist="Artist",
                duration=100,
                platform=_platform.SPOTIFY,
                platform_id=f"song{i}",
                url=f"https://example.com/song{i}",
            )
            for i in range(3)
        ]

        ids = await queue.add_many(songs)

        # Move last to top
        await queue.move_to_top(ids[2])

        items = queue.items
        assert items[0].song.name == "Song 2"
        assert items[1].song.name == "Song 0"
        assert items[2].song.name == "Song 1"

    @pytest.mark.asyncio
    async def test_properties(self, queue: DownloadQueue, sample_song: Song) -> None:
        """Test queue properties."""
        assert queue.is_empty is True

        item_id = await queue.add(sample_song)
        assert queue.is_empty is False
        assert queue.total_count == 1
        assert queue.pending_count == 1
        assert queue.active_count == 0

        await queue.update_status(item_id, DownloadStatus.DOWNLOADING)
        assert queue.active_count == 1

        await queue.update_status(item_id, DownloadStatus.COMPLETED)
        assert len(queue.completed_items) == 1


# Import Platform for test helper
from spotdl_cli.core.types import Platform as _platform
