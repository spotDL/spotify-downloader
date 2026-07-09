"""CONTRACT A3 — the correlation-id request middleware.

Exercised through a minimal app over ``httpx.ASGITransport`` so the access log,
the ``X-Request-ID`` echo/replace behaviour, and the route-template ``path``
label are all observed end to end.
"""

from __future__ import annotations

import io
import json

import httpx
import pytest
from fastapi import FastAPI
from spotdl_server.observability import metrics
from spotdl_server.observability.logging import configure_logging
from spotdl_server.observability.middleware import RequestObservabilityMiddleware
from spotdl_server.settings import Settings


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    application.add_middleware(RequestObservabilityMiddleware)

    @application.get("/api/v1/items/{item_id}")
    async def _item(item_id: str) -> dict[str, str]:
        return {"item_id": item_id}

    return application


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_response_carries_generated_request_id(app: FastAPI) -> None:
    async with _client(app) as client:
        resp = await client.get("/api/v1/items/42")
    assert resp.status_code == 200
    assert resp.headers["x-request-id"]


async def test_inbound_request_id_is_echoed(app: FastAPI) -> None:
    async with _client(app) as client:
        resp = await client.get("/api/v1/items/42", headers={"X-Request-ID": "abc-123"})
    assert resp.headers["x-request-id"] == "abc-123"


async def test_malformed_request_id_is_replaced(app: FastAPI) -> None:
    async with _client(app) as client:
        resp = await client.get("/api/v1/items/42", headers={"X-Request-ID": "bad id with spaces!"})
    assert resp.headers["x-request-id"] != "bad id with spaces!"
    assert resp.headers["x-request-id"]


async def test_access_log_line_carries_template_path_and_timing(app: FastAPI) -> None:
    stream = io.StringIO()
    configure_logging(Settings(), stream=stream)

    async with _client(app) as client:
        await client.get("/api/v1/items/42", headers={"X-Request-ID": "req-9"})

    records = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
    access = [r for r in records if r.get("path") == "/api/v1/items/{item_id}"]
    assert access, f"no access log with template path: {records}"
    line = access[-1]
    assert line["request_id"] == "req-9"
    assert line["method"] == "GET"
    assert line["status_code"] == 200
    assert isinstance(line["duration_ms"], int | float)


async def test_http_counter_uses_template_not_concrete_id(app: FastAPI) -> None:
    labels = {"method": "GET", "path": "/api/v1/items/{item_id}", "status": "200"}
    before = metrics.REGISTRY.get_sample_value("spotdl_http_requests_total", labels) or 0.0

    async with _client(app) as client:
        await client.get("/api/v1/items/7")
        await client.get("/api/v1/items/8")

    after = metrics.REGISTRY.get_sample_value("spotdl_http_requests_total", labels) or 0.0
    assert after == before + 2
    # The concrete id must never become its own label series.
    assert (
        metrics.REGISTRY.get_sample_value(
            "spotdl_http_requests_total",
            {"method": "GET", "path": "/api/v1/items/7", "status": "200"},
        )
        is None
    )
