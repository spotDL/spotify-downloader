"""CONTRACT A5 — observability wired into ``create_app``.

``/metrics`` is served (or unmounted when disabled), the request middleware is
active on real API routes, and the counter advances for a live request.
"""

from __future__ import annotations

import httpx
from spotdl_server.app import create_app
from spotdl_server.observability import metrics
from spotdl_server.settings import Settings


def _client(settings: Settings | None = None) -> httpx.AsyncClient:
    app = create_app(settings)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_metrics_endpoint_served_and_lists_contract_names() -> None:
    async with _client() as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    for name in metrics.METRIC_NAMES:
        assert name in resp.text


async def test_request_gets_request_id_header_and_moves_counter() -> None:
    labels = {"method": "GET", "path": "/api/v1/health", "status": "200"}
    before = metrics.REGISTRY.get_sample_value("spotdl_http_requests_total", labels) or 0.0

    async with _client() as client:
        resp = await client.get("/api/v1/health")

    assert resp.status_code == 200
    assert resp.headers["x-request-id"]
    after = metrics.REGISTRY.get_sample_value("spotdl_http_requests_total", labels) or 0.0
    assert after == before + 1


async def test_metrics_disabled_returns_404() -> None:
    async with _client(Settings(metrics_enabled=False)) as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 404
