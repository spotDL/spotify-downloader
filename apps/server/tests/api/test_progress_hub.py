"""Task 5 — ``ProgressHub`` WS fan-out (accept / broadcast / client-gone / snapshot)."""

from __future__ import annotations

from uuid import uuid4

from spotdl_server.api.progress_hub import ProgressHub
from spotdl_server.api.schemas import WsHello, WsJobStarted


class FakeWebSocket:
    """An async ``WebSocket`` stub recording ``send_text`` and optionally failing."""

    def __init__(self, *, fail_send: bool = False) -> None:
        self.sent: list[str] = []
        self.accepted = False
        self._fail = fail_send

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, text: str) -> None:
        if self._fail:
            raise RuntimeError("client gone")
        self.sent.append(text)


async def test_register_accepts_and_tracks() -> None:
    hub = ProgressHub()
    ws = FakeWebSocket()
    await hub.register(ws)  # type: ignore[arg-type]
    assert ws.accepted
    await hub.broadcast(WsHello())
    assert len(ws.sent) == 1


async def test_broadcast_reaches_all_clients() -> None:
    hub = ProgressHub()
    a, b = FakeWebSocket(), FakeWebSocket()
    await hub.register(a)  # type: ignore[arg-type]
    await hub.register(b)  # type: ignore[arg-type]

    await hub.broadcast(WsHello())

    assert len(a.sent) == 1
    assert len(b.sent) == 1
    assert '"type":"hello"' in a.sent[0]


async def test_broadcast_drops_dead_client_and_keeps_serving() -> None:
    hub = ProgressHub()
    good = FakeWebSocket()
    dead = FakeWebSocket(fail_send=True)
    await hub.register(good)  # type: ignore[arg-type]
    await hub.register(dead)  # type: ignore[arg-type]

    await hub.broadcast(WsHello())
    assert len(good.sent) == 1  # a raising client never blocks the broadcast

    # the dead client was removed; a second broadcast still reaches the good one
    await hub.broadcast(WsHello())
    assert len(good.sent) == 2


async def test_unregister_removes_client() -> None:
    hub = ProgressHub()
    ws = FakeWebSocket()
    await hub.register(ws)  # type: ignore[arg-type]
    hub.unregister(ws)  # type: ignore[arg-type]
    await hub.broadcast(WsHello())
    assert ws.sent == []


async def test_snapshot_to_targets_one_client_only() -> None:
    hub = ProgressHub()
    a, b = FakeWebSocket(), FakeWebSocket()
    await hub.register(a)  # type: ignore[arg-type]
    await hub.register(b)  # type: ignore[arg-type]

    messages = [WsJobStarted(job_id=uuid4(), batch_id=None)]
    await hub.snapshot_to(a, messages)  # type: ignore[arg-type]

    assert len(a.sent) == 1
    assert b.sent == []
