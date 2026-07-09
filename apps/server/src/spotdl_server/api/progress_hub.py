"""``ProgressHub`` — the single WebSocket fan-out for download progress (CONTRACT 3).

One endpoint (``WS /ws/progress``) fans out **all** job events to **every**
connected client; clients filter by ``batch_id`` / ``job_id`` themselves (no
per-client downloader like v4). The hub owns the connected-client set and the
serialize-once / iterate-a-copy / drop-on-error broadcast loop.

**Why this lives in ``api/`` (not ``downloads/``):** it imports
:class:`fastapi.WebSocket` — it is HTTP glue, not domain logic. The worker pool
(in ``downloads/``) must not import ``api/``, so it depends on a structural
``Broadcaster`` Protocol (declared in ``downloads/worker.py``) that this concrete
hub satisfies. That keeps the ``downloads/`` package free of any ``api/`` import
while still letting the worker broadcast through the real hub at runtime.
"""

from __future__ import annotations

from collections.abc import Iterable

from fastapi import WebSocket

from spotdl_server.api.schemas import WsMessage


class ProgressHub:
    """Track connected WS clients and fan progress messages out to all of them."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def register(self, ws: WebSocket) -> None:
        """Accept the connection and start delivering broadcasts to it."""
        await ws.accept()
        self._clients.add(ws)

    def unregister(self, ws: WebSocket) -> None:
        """Stop delivering to ``ws`` (idempotent; safe if never registered)."""
        self._clients.discard(ws)

    async def broadcast(self, message: WsMessage) -> None:
        """Serialize once and send to every client; drop any that raises.

        Iterates a *copy* of the client set so a mid-broadcast removal is safe,
        and swallows a per-client send error (``WebSocketDisconnect`` /
        ``RuntimeError`` / anything) after removing that client — a dead client
        never blocks the broadcast or the job producing it (CONTRACT 3).
        """
        payload = message.model_dump_json()
        for ws in list(self._clients):
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001 - client-gone safety; drop and continue
                self._clients.discard(ws)

    async def snapshot_to(self, ws: WebSocket, messages: Iterable[WsMessage]) -> None:
        """Send ``messages`` to a single client (the on-connect state snapshot).

        Best-effort: a send failure removes that one client and stops (there is
        nothing more to deliver to a gone client).
        """
        for message in messages:
            try:
                await ws.send_text(message.model_dump_json())
            except Exception:  # noqa: BLE001 - client-gone safety
                self._clients.discard(ws)
                return
