"""``SpotdlClient`` download methods + WS ``progress()`` (Plan 8 Task 7).

HTTP download methods are driven over ``RemoteTransport`` + respx (the embedded
transport is a sibling track); ``progress()`` is driven over a fake transport
implementing the ``ws_connect`` half of the ``Transport`` seam.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import httpx
import pytest
import respx
from httpx_ws import WebSocketDisconnect
from spotdl_cli._generated.ws_models import WsHello, WsMessage, WsProgress
from spotdl_cli.client import (
    WS_PROTOCOL_VERSION,
    RemoteTransport,
    SpotdlClient,
    UnsupportedProtocol,
)
from spotdl_cli.views import BatchView, DownloadSubmit

BASE = "https://api.test"
BATCH_ID = UUID("22222222-2222-2222-2222-222222222222")
JOB_ID = UUID("33333333-3333-3333-3333-333333333333")

BATCH_JSON = {
    "batch_id": str(BATCH_ID),
    "kind": "single",
    "finalized": False,
    "total_jobs": 1,
    "counts": {"queued": 1},
    "jobs": [],
    "name": None,
}
SAVE_FILE_JSON = {
    "version": 2,
    "kind": "single",
    "name": "mix",
    "source": None,
    "created_at": "2020-01-01T00:00:00",
    "matcher_version": None,
    "songs": [],
}


@pytest.fixture
async def http_client() -> AsyncIterator[SpotdlClient]:
    transport = RemoteTransport(BASE)
    try:
        yield SpotdlClient(resolution=transport, downloads=transport)
    finally:
        await transport.aclose()


async def test_submit_download_maps_request_and_batch(http_client: SpotdlClient) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        route = router.post("/api/v1/downloads").mock(
            return_value=httpx.Response(201, json={"batch": BATCH_JSON})
        )
        batch = await http_client.submit_download(
            DownloadSubmit(query="https://x/track", output_format="flac", overwrite="force")
        )
    assert route.called
    import json

    body = json.loads(route.calls.last.request.read())
    assert body["output_format"] == "flac"
    assert body["overwrite"] == "force"
    assert body["query"] == "https://x/track"
    assert isinstance(batch, BatchView)
    assert batch.batch_id == str(BATCH_ID)


async def test_fetch_save_file_parses_typed_model(http_client: SpotdlClient) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get(f"/api/v1/downloads/batches/{BATCH_ID}/save-file").mock(
            return_value=httpx.Response(200, json=SAVE_FILE_JSON)
        )
        save = await http_client.fetch_save_file(BATCH_ID)
    assert save.version == 2
    assert save.kind == "single"
    assert save.name == "mix"


async def test_get_batch_and_list_downloads(http_client: SpotdlClient) -> None:
    page_json = {"jobs": [], "total": 0, "limit": 50, "offset": 0}
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get(f"/api/v1/downloads/batches/{BATCH_ID}").mock(
            return_value=httpx.Response(200, json=BATCH_JSON)
        )
        router.get("/api/v1/downloads").mock(return_value=httpx.Response(200, json=page_json))
        batch = await http_client.get_batch(BATCH_ID)
        page = await http_client.list_downloads(status="queued", limit=10)
    assert batch.batch_id == str(BATCH_ID)
    assert page.total == 0


# --- progress() over a fake WS transport --------------------------------------


class _FakeSession:
    def __init__(self, texts: list[str]) -> None:
        self._it = iter(texts)

    async def receive_text(self) -> str:
        try:
            return next(self._it)
        except StopIteration:
            raise WebSocketDisconnect(code=1000) from None


class _FakeTransport:
    def __init__(self, texts: list[str]) -> None:
        self._texts = texts

    @property
    def http_base(self) -> str:
        return "http://embedded"

    @property
    def ws_base(self) -> str:
        return "ws://embedded"

    def http_client(self) -> Any:
        raise AssertionError("progress() must not touch the HTTP client")

    @asynccontextmanager
    async def ws_connect(self, path: str) -> AsyncIterator[_FakeSession]:
        assert path == "/ws/progress"
        yield _FakeSession(self._texts)

    async def aclose(self) -> None:
        return None


def _progress_frame() -> str:
    return WsMessage(
        root=WsProgress(job_id=JOB_ID, batch_id=BATCH_ID, overall=0.5, percent=50, phase="download")
    ).model_dump_json()


async def test_progress_swallows_hello_and_yields_events() -> None:
    hello = WsMessage(root=WsHello(protocol_version=WS_PROTOCOL_VERSION)).model_dump_json()
    transport = _FakeTransport([hello, _progress_frame()])
    client = SpotdlClient(resolution=transport, downloads=transport)  # type: ignore[arg-type]

    received: list[Any] = []
    async with client.progress() as stream:
        async for message in stream:
            received.append(message.root)
    assert len(received) == 1
    assert isinstance(received[0], WsProgress)
    assert received[0].overall == 0.5


async def test_progress_rejects_mismatched_protocol() -> None:
    hello = WsMessage(root=WsHello(protocol_version=WS_PROTOCOL_VERSION + 1)).model_dump_json()
    transport = _FakeTransport([hello])
    client = SpotdlClient(resolution=transport, downloads=transport)  # type: ignore[arg-type]

    with pytest.raises(UnsupportedProtocol):
        async with client.progress() as stream:
            async for _ in stream:
                pass
