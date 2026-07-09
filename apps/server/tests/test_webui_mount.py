"""Plan 10: the bundled-SPA static mount (``spotdl_server.webui.mount_webui``).

Additive to ``apps/server`` — a new module plus one guarded ``create_app`` call;
it changes no existing route. The app is driven over ASGI with a temp ``webui/``
directory monkeypatched in, so nothing depends on the real UI being built.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import spotdl_server.webui as webui
from spotdl_server.app import create_app
from spotdl_server.settings import DeploymentMode, Settings

_INDEX_MARKER = "<div id=root></div>"


def _client(app: object) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def _embedded_app() -> object:
    # Embedded mode mounts no rate-limit middleware, so the app serves health /
    # config / the SPA without the lifespan-built state.
    return create_app(Settings(mode=DeploymentMode.EMBEDDED))


@pytest.fixture
def webui_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "webui"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(f"<!doctype html><title>spotDL</title>{_INDEX_MARKER}")
    (root / "assets" / "app-abc123.js").write_text("console.log('spa')")
    (root / "favicon.ico").write_bytes(b"\x00icon")
    monkeypatch.setattr(webui, "_webui_dir", lambda: root)
    return root


async def test_root_serves_index_html(webui_dir: Path) -> None:
    async with _client(_embedded_app()) as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert _INDEX_MARKER in resp.text
    assert resp.headers["content-type"].startswith("text/html")


async def test_spa_path_falls_back_to_index(webui_dir: Path) -> None:
    # A deep client-side route reloaded directly returns the SPA shell so the
    # router can take over — never a 404.
    async with _client(_embedded_app()) as client:
        resp = await client.get("/tracks/abc-123")
    assert resp.status_code == 200
    assert _INDEX_MARKER in resp.text


async def test_real_assets_are_served_verbatim(webui_dir: Path) -> None:
    async with _client(_embedded_app()) as client:
        js = await client.get("/assets/app-abc123.js")
        icon = await client.get("/favicon.ico")
    assert js.status_code == 200
    assert "console.log('spa')" in js.text
    assert icon.status_code == 200


async def test_api_route_is_json_not_html(webui_dir: Path) -> None:
    async with _client(_embedded_app()) as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_unknown_api_path_is_404_not_spa(webui_dir: Path) -> None:
    async with _client(_embedded_app()) as client:
        resp = await client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    assert _INDEX_MARKER not in resp.text


async def test_absent_dir_is_a_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    # No embedded UI: `/` is a plain 404 and the API is untouched.
    monkeypatch.setattr(webui, "_webui_dir", lambda: None)
    async with _client(_embedded_app()) as client:
        root = await client.get("/")
        health = await client.get("/api/v1/health")
    assert root.status_code == 404
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
