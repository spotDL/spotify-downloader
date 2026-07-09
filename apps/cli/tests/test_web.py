"""``spotdl web`` — embedded boot + browser handoff + SPA stub.

``uvicorn.run`` / ``webbrowser.open`` / migrations are patched so nothing binds a
socket; a separate ASGI check asserts ``/`` serves the Plan 10 stub (not a real
SPA) and that the download-capable embedded API is what boots.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from spotdl_cli.__main__ import app
from spotdl_cli.commands import web as web_cmd
from spotdl_server.settings import DeploymentMode, Settings
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def patched(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch the boot seams; capture what ``web`` would have launched/opened."""
    captured: dict[str, Any] = {"run": None, "opened": None, "migrated": []}

    def _run(app_obj: Any, **kwargs: Any) -> None:
        captured["run"] = (app_obj, kwargs)

    def _open(target: str, *args: Any, **kwargs: Any) -> bool:
        captured["opened"] = target
        return True

    monkeypatch.setattr("uvicorn.run", _run)
    monkeypatch.setattr("webbrowser.open", _open)
    monkeypatch.setattr(web_cmd, "_migrate", lambda s: captured["migrated"].append(s))
    return captured


def test_web_boots_embedded_and_opens_browser(patched: dict[str, Any]) -> None:
    result = runner.invoke(app, ["web", "--port", "9123"])

    assert result.exit_code == 0
    assert "the web UI ships in a later release" in result.output
    assert "http://127.0.0.1:9123/api/v1" in result.output
    # migrations ran on an embedded, download-capable server
    assert patched["migrated"][0].mode is DeploymentMode.EMBEDDED
    assert patched["migrated"][0].downloads_enabled() is True
    # browser opened at the loopback root; uvicorn bound the requested host/port
    assert patched["opened"] == "http://127.0.0.1:9123/"
    _app, kwargs = patched["run"]
    assert kwargs == {"host": "127.0.0.1", "port": 9123}


def test_web_no_open_skips_browser(patched: dict[str, Any]) -> None:
    result = runner.invoke(app, ["web", "--no-open", "--host", "0.0.0.0"])

    assert result.exit_code == 0
    assert patched["opened"] is None
    _app, kwargs = patched["run"]
    assert kwargs["host"] == "0.0.0.0"


async def test_stub_root_serves_notice_not_spa() -> None:
    web_app = web_cmd.build_web_app(
        Settings(mode=DeploymentMode.EMBEDDED), api_url="http://127.0.0.1:8800/api/v1"
    )
    transport = httpx.ASGITransport(app=web_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://web") as client:
        resp = await client.get("/")

    assert resp.status_code == 200
    assert "web UI ships in a later release" in resp.text
    assert "http://127.0.0.1:8800/api/v1" in resp.text
