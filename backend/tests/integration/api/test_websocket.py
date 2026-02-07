"""Tests for WebSocket endpoints."""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from spotdl.api.v1.websocket import ConnectionManager, manager
from spotdl.core.services.download import (
    DownloadManager,
    DownloadProgress,
    DownloadStatus,
)
from spotdl.main import app


@pytest.fixture
def mock_download_manager():
    """Create a mock download manager."""
    manager = MagicMock(spec=DownloadManager)
    manager.get_progress = MagicMock(return_value=None)
    manager.get_all_downloads = MagicMock(return_value=[])
    manager.register_callback = MagicMock()
    manager.unregister_callback = MagicMock()
    return manager


@pytest.fixture
def sample_progress():
    """Create a sample download progress."""
    return DownloadProgress(
        download_id="test-download-123",
        status=DownloadStatus.DOWNLOADING,
        progress=50.0,
        speed="1.5 MB/s",
        eta="00:30",
        filename="Artist - Song.mp3",
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_progress_completed():
    """Create a completed download progress."""
    return DownloadProgress(
        download_id="test-download-123",
        status=DownloadStatus.COMPLETED,
        progress=100.0,
        filename="Artist - Song.mp3",
        created_at=datetime.now(),
        completed_at=datetime.now(),
    )


@pytest.fixture
def sample_progress_failed():
    """Create a failed download progress."""
    return DownloadProgress(
        download_id="test-download-456",
        status=DownloadStatus.FAILED,
        progress=25.0,
        error="Failed to download audio",
        filename="Artist - Failed Song.mp3",
        created_at=datetime.now(),
    )


class TestConnectionManager:
    """Test ConnectionManager class."""

    @pytest.mark.asyncio
    async def test_connect_new_client(self):
        """Test connecting a new client."""
        conn_manager = ConnectionManager()
        websocket = MagicMock()
        websocket.accept = AsyncMock()

        await conn_manager.connect(websocket, "client-1")

        websocket.accept.assert_awaited_once()
        assert "client-1" in conn_manager.active_connections
        assert websocket in conn_manager.active_connections["client-1"]

    @pytest.mark.asyncio
    async def test_connect_multiple_connections_same_client(self):
        """Test multiple connections for the same client."""
        conn_manager = ConnectionManager()
        websocket1 = MagicMock()
        websocket1.accept = AsyncMock()
        websocket2 = MagicMock()
        websocket2.accept = AsyncMock()

        await conn_manager.connect(websocket1, "client-1")
        await conn_manager.connect(websocket2, "client-1")

        assert len(conn_manager.active_connections["client-1"]) == 2
        assert websocket1 in conn_manager.active_connections["client-1"]
        assert websocket2 in conn_manager.active_connections["client-1"]

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self):
        """Test disconnecting removes the connection."""
        conn_manager = ConnectionManager()
        websocket = MagicMock()
        websocket.accept = AsyncMock()

        await conn_manager.connect(websocket, "client-1")
        await conn_manager.disconnect(websocket, "client-1")

        assert "client-1" not in conn_manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_multiple_connections(self):
        """Test disconnecting one of multiple connections."""
        conn_manager = ConnectionManager()
        websocket1 = MagicMock()
        websocket1.accept = AsyncMock()
        websocket2 = MagicMock()
        websocket2.accept = AsyncMock()

        await conn_manager.connect(websocket1, "client-1")
        await conn_manager.connect(websocket2, "client-1")
        await conn_manager.disconnect(websocket1, "client-1")

        assert "client-1" in conn_manager.active_connections
        assert len(conn_manager.active_connections["client-1"]) == 1
        assert websocket2 in conn_manager.active_connections["client-1"]
        assert websocket1 not in conn_manager.active_connections["client-1"]

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self):
        """Test disconnecting a connection that doesn't exist."""
        conn_manager = ConnectionManager()
        websocket = MagicMock()

        # Should not raise an exception
        await conn_manager.disconnect(websocket, "client-1")

    @pytest.mark.asyncio
    async def test_send_personal_message(self):
        """Test sending a message to a specific client."""
        conn_manager = ConnectionManager()
        websocket = MagicMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()

        await conn_manager.connect(websocket, "client-1")
        message = {"type": "test", "data": "hello"}
        await conn_manager.send_personal_message(message, "client-1")

        websocket.send_json.assert_awaited_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_nonexistent_client(self):
        """Test sending a message to a non-existent client."""
        conn_manager = ConnectionManager()
        message = {"type": "test", "data": "hello"}

        # Should not raise an exception
        await conn_manager.send_personal_message(message, "nonexistent")

    @pytest.mark.asyncio
    async def test_send_personal_message_handles_failed_connection(self):
        """Test that failed connections are cleaned up when sending messages."""
        conn_manager = ConnectionManager()
        websocket = MagicMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock(side_effect=Exception("Connection failed"))

        await conn_manager.connect(websocket, "client-1")
        message = {"type": "test", "data": "hello"}
        await conn_manager.send_personal_message(message, "client-1")

        # Connection should be removed after failure
        assert "client-1" not in conn_manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_to_all_clients(self):
        """Test broadcasting a message to all connected clients."""
        conn_manager = ConnectionManager()
        websocket1 = MagicMock()
        websocket1.accept = AsyncMock()
        websocket1.send_json = AsyncMock()
        websocket2 = MagicMock()
        websocket2.accept = AsyncMock()
        websocket2.send_json = AsyncMock()

        await conn_manager.connect(websocket1, "client-1")
        await conn_manager.connect(websocket2, "client-2")

        message = {"type": "broadcast", "data": "hello all"}
        await conn_manager.broadcast(message)

        websocket1.send_json.assert_awaited_once_with(message)
        websocket2.send_json.assert_awaited_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_connections(self):
        """Test broadcasting when no clients are connected."""
        conn_manager = ConnectionManager()
        message = {"type": "broadcast", "data": "hello all"}

        # Should not raise an exception
        await conn_manager.broadcast(message)


class TestWebSocketEndpoint:
    """Test WebSocket endpoint."""

    def test_websocket_connection_establishment(
        self, mock_download_manager: MagicMock
    ):
        """Test basic WebSocket connection establishment."""
        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            with TestClient(app) as client:
                with client.websocket_connect("/api/v1/ws/test-client-1") as ws:
                    # Connection should be established
                    assert ws is not None

                    # Send ping and expect pong
                    ws.send_json({"type": "ping"})
                    response = ws.receive_json()
                    assert response["type"] == "pong"

    @pytest.mark.asyncio
    async def test_websocket_with_unique_client_id(self, mock_download_manager: MagicMock):
        """Test WebSocket connection with unique client ID."""
        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect(
                    "/api/v1/ws/unique-client-123"
                ) as ws:
                    await ws.send_json({"type": "ping"})
                    response = await ws.receive_json()
                    assert response["type"] == "pong"

    @pytest.mark.asyncio
    async def test_watch_download(self, mock_download_manager: MagicMock, sample_progress):
        """Test watching a download."""
        mock_download_manager.get_progress.return_value = sample_progress

        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    # Watch a download
                    await ws.send_json(
                        {"type": "watch_download", "download_id": "test-download-123"}
                    )

                    # Should receive current progress
                    response = await ws.receive_json()
                    assert response["type"] == "download_progress"
                    assert response["data"]["download_id"] == "test-download-123"
                    assert response["data"]["status"] == "downloading"
                    assert response["data"]["progress"] == 50.0

                    # Verify callback was registered
                    mock_download_manager.register_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_watch_download_nonexistent(self, mock_download_manager: MagicMock):
        """Test watching a download that doesn't exist."""
        mock_download_manager.get_progress.return_value = None

        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    # Watch a non-existent download
                    await ws.send_json(
                        {"type": "watch_download", "download_id": "nonexistent"}
                    )

                    # Should still register callback but not send progress
                    mock_download_manager.register_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_watch_download_without_id(self, mock_download_manager: MagicMock):
        """Test watch_download message without download_id."""
        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    # Send watch_download without download_id
                    await ws.send_json({"type": "watch_download"})

                    # Should not register callback
                    mock_download_manager.register_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_unwatch_download(self, mock_download_manager: MagicMock, sample_progress):
        """Test unwatching a download."""
        mock_download_manager.get_progress.return_value = sample_progress

        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    # First watch a download
                    await ws.send_json(
                        {"type": "watch_download", "download_id": "test-download-123"}
                    )
                    await ws.receive_json()  # Consume the progress message

                    # Now unwatch it
                    await ws.send_json(
                        {"type": "unwatch_download", "download_id": "test-download-123"}
                    )

                    # No response expected for unwatch
                    # Verify the download is no longer watched
                    mock_download_manager.register_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_downloads(
        self, mock_download_manager: MagicMock, sample_progress, sample_progress_failed
    ):
        """Test listing all downloads."""
        mock_download_manager.get_all_downloads.return_value = [
            sample_progress,
            sample_progress_failed,
        ]

        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    # Request download list
                    await ws.send_json({"type": "list_downloads"})

                    # Should receive list of downloads
                    response = await ws.receive_json()
                    assert response["type"] == "download_list"
                    assert len(response["data"]) == 2
                    assert response["data"][0]["download_id"] == "test-download-123"
                    assert response["data"][1]["download_id"] == "test-download-456"

    @pytest.mark.asyncio
    async def test_list_downloads_empty(self, mock_download_manager: MagicMock):
        """Test listing downloads when there are none."""
        mock_download_manager.get_all_downloads.return_value = []

        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    await ws.send_json({"type": "list_downloads"})
                    response = await ws.receive_json()
                    assert response["type"] == "download_list"
                    assert response["data"] == []

    @pytest.mark.asyncio
    async def test_ping_pong(self, mock_download_manager: MagicMock):
        """Test ping-pong keep-alive mechanism."""
        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    # Send multiple pings
                    for _ in range(3):
                        await ws.send_json({"type": "ping"})
                        response = await ws.receive_json()
                        assert response["type"] == "pong"

    @pytest.mark.asyncio
    async def test_unknown_message_type(self, mock_download_manager: MagicMock):
        """Test handling unknown message type."""
        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    # Send unknown message type
                    await ws.send_json({"type": "unknown_type"})

                    # Should not crash, but no response expected
                    # Send a ping to verify connection is still alive
                    await ws.send_json({"type": "ping"})
                    response = await ws.receive_json()
                    assert response["type"] == "pong"

    @pytest.mark.asyncio
    async def test_connection_closure(self, mock_download_manager: MagicMock):
        """Test WebSocket connection closure."""
        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    await ws.send_json({"type": "ping"})
                    await ws.receive_json()

                # Connection closed automatically by context manager
                # Verify client is removed from manager
                assert "test-client" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(self, mock_download_manager: MagicMock):
        """Test multiple concurrent WebSocket connections."""
        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                # Open multiple connections
                async with (
                    client.websocket_connect("/api/v1/ws/client-1") as ws1,
                    client.websocket_connect("/api/v1/ws/client-2") as ws2,
                    client.websocket_connect("/api/v1/ws/client-3") as ws3,
                ):
                    # All connections should work independently
                    await ws1.send_json({"type": "ping"})
                    await ws2.send_json({"type": "ping"})
                    await ws3.send_json({"type": "ping"})

                    response1 = await ws1.receive_json()
                    response2 = await ws2.receive_json()
                    response3 = await ws3.receive_json()

                    assert response1["type"] == "pong"
                    assert response2["type"] == "pong"
                    assert response3["type"] == "pong"

    @pytest.mark.asyncio
    async def test_progress_callback_triggered(
        self, mock_download_manager: MagicMock, sample_progress
    ):
        """Test that progress callbacks are properly triggered."""
        mock_download_manager.get_progress.return_value = sample_progress
        callback_captured = None

        def capture_callback(download_id: str, callback):
            nonlocal callback_captured
            callback_captured = callback

        mock_download_manager.register_callback.side_effect = capture_callback

        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    # Watch a download
                    await ws.send_json(
                        {"type": "watch_download", "download_id": "test-download-123"}
                    )
                    await ws.receive_json()  # Consume initial progress

                    # Verify callback was captured
                    assert callback_captured is not None

                    # Simulate progress update
                    updated_progress = DownloadProgress(
                        download_id="test-download-123",
                        status=DownloadStatus.DOWNLOADING,
                        progress=75.0,
                        speed="2.0 MB/s",
                        eta="00:15",
                        filename="Artist - Song.mp3",
                        created_at=datetime.now(),
                    )

                    # Trigger the callback
                    callback_captured(updated_progress)

                    # Give the async task time to execute
                    await asyncio.sleep(0.1)

                    # Receive the progress update
                    response = await ws.receive_json()
                    assert response["type"] == "download_progress"
                    assert response["data"]["progress"] == 75.0
                    assert response["data"]["speed"] == "2.0 MB/s"

    @pytest.mark.asyncio
    async def test_completed_download_notification(
        self, mock_download_manager: MagicMock, sample_progress_completed
    ):
        """Test receiving notification for completed download."""
        mock_download_manager.get_progress.return_value = sample_progress_completed

        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    await ws.send_json(
                        {"type": "watch_download", "download_id": "test-download-123"}
                    )

                    response = await ws.receive_json()
                    assert response["type"] == "download_progress"
                    assert response["data"]["status"] == "completed"
                    assert response["data"]["progress"] == 100.0
                    assert response["data"]["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_failed_download_notification(
        self, mock_download_manager: MagicMock, sample_progress_failed
    ):
        """Test receiving notification for failed download."""
        mock_download_manager.get_progress.return_value = sample_progress_failed

        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    await ws.send_json(
                        {"type": "watch_download", "download_id": "test-download-456"}
                    )

                    response = await ws.receive_json()
                    assert response["type"] == "download_progress"
                    assert response["data"]["status"] == "failed"
                    assert response["data"]["error"] == "Failed to download audio"
                    assert response["data"]["progress"] == 25.0

    @pytest.mark.asyncio
    async def test_watch_same_download_twice(
        self, mock_download_manager: MagicMock, sample_progress
    ):
        """Test watching the same download twice doesn't register callback twice."""
        mock_download_manager.get_progress.return_value = sample_progress

        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    # Watch the same download twice
                    await ws.send_json(
                        {"type": "watch_download", "download_id": "test-download-123"}
                    )
                    await ws.receive_json()

                    await ws.send_json(
                        {"type": "watch_download", "download_id": "test-download-123"}
                    )

                    # Callback should only be registered once
                    assert mock_download_manager.register_callback.call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_clients_same_id(self, mock_download_manager: MagicMock):
        """Test multiple connections with the same client ID."""
        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                # Open two connections with the same client ID
                async with (
                    client.websocket_connect("/api/v1/ws/same-client") as ws1,
                    client.websocket_connect("/api/v1/ws/same-client") as ws2,
                ):
                    # Both should receive messages
                    await ws1.send_json({"type": "ping"})
                    await ws2.send_json({"type": "ping"})

                    response1 = await ws1.receive_json()
                    response2 = await ws2.receive_json()

                    assert response1["type"] == "pong"
                    assert response2["type"] == "pong"

    @pytest.mark.asyncio
    async def test_malformed_json_message(self, mock_download_manager: MagicMock):
        """Test handling of malformed JSON messages."""
        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    # Send text instead of JSON
                    await ws.send_text("not json")

                    # Connection should be closed due to error
                    # Wait a bit for the error to be processed
                    await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_message_without_type_field(self, mock_download_manager: MagicMock):
        """Test handling of messages without type field."""
        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    # Send message without type field
                    await ws.send_json({"data": "some data"})

                    # Should not crash
                    # Verify connection is still alive with ping
                    await ws.send_json({"type": "ping"})
                    response = await ws.receive_json()
                    assert response["type"] == "pong"

    @pytest.mark.asyncio
    async def test_download_progress_serialization(
        self, mock_download_manager: MagicMock, sample_progress
    ):
        """Test that download progress is properly serialized."""
        mock_download_manager.get_progress.return_value = sample_progress

        with patch(
            "spotdl.api.v1.websocket.get_download_manager",
            return_value=mock_download_manager,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.websocket_connect("/api/v1/ws/test-client") as ws:
                    await ws.send_json(
                        {"type": "watch_download", "download_id": "test-download-123"}
                    )

                    response = await ws.receive_json()

                    # Verify all expected fields are present
                    data = response["data"]
                    assert "download_id" in data
                    assert "status" in data
                    assert "progress" in data
                    assert "speed" in data
                    assert "eta" in data
                    assert "filename" in data
                    assert "created_at" in data
                    assert "completed_at" in data

                    # Verify types
                    assert isinstance(data["progress"], (int, float))
                    assert isinstance(data["status"], str)
