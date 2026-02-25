"""WebSocket endpoints for real-time updates."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from spotdl.core.services.download import DownloadProgress, get_download_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            if client_id not in self.active_connections:
                self.active_connections[client_id] = []
            self.active_connections[client_id].append(websocket)
        logger.info(f"WebSocket connected: {client_id}")

    async def disconnect(self, websocket: WebSocket, client_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if client_id in self.active_connections:
                try:
                    self.active_connections[client_id].remove(websocket)
                    if not self.active_connections[client_id]:
                        del self.active_connections[client_id]
                except ValueError:
                    pass
        logger.info(f"WebSocket disconnected: {client_id}")

    async def send_personal_message(self, message: dict[str, Any], client_id: str) -> None:
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)

            # Clean up disconnected
            for conn in disconnected:
                await self.disconnect(conn, client_id)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        for client_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, client_id)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
    """
    WebSocket endpoint for real-time updates.

    Clients connect with a unique client_id and receive:
    - Download progress updates
    - Download completion/failure notifications
    """
    await manager.connect(websocket, client_id)
    download_manager = get_download_service()

    # Track which downloads this client is watching
    watched_downloads: set[str] = set()

    def create_progress_callback(download_id: str) -> Callable[[Any], None]:
        """Create a callback for download progress updates."""

        async def send_update(progress: DownloadProgress) -> None:
            """Send progress update to client."""
            await manager.send_personal_message(
                {
                    "type": "download_progress",
                    "data": progress.to_dict(),
                },
                client_id,
            )

        def callback(progress: DownloadProgress) -> None:
            """Sync callback that schedules async send."""
            asyncio.create_task(send_update(progress))

        return callback

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "watch_download":
                # Client wants to watch a specific download
                download_id = data.get("download_id")
                if download_id and download_id not in watched_downloads:
                    callback = create_progress_callback(download_id)
                    download_manager.register_callback(download_id, callback)
                    watched_downloads.add(download_id)

                    # Send current status immediately
                    progress = download_manager.get_progress(download_id)
                    if progress:
                        await manager.send_personal_message(
                            {
                                "type": "download_progress",
                                "data": progress.to_dict(),
                            },
                            client_id,
                        )

            elif message_type == "unwatch_download":
                # Client no longer wants updates for this download
                download_id = data.get("download_id")
                if download_id and download_id in watched_downloads:
                    watched_downloads.discard(download_id)

            elif message_type == "list_downloads":
                # Client wants list of all downloads
                downloads = download_manager.get_all_downloads()
                await manager.send_personal_message(
                    {
                        "type": "download_list",
                        "data": [d.to_dict() for d in downloads],
                    },
                    client_id,
                )

            elif message_type == "ping":
                # Keep-alive ping
                await manager.send_personal_message({"type": "pong"}, client_id)

    except WebSocketDisconnect:
        await manager.disconnect(websocket, client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, client_id)
