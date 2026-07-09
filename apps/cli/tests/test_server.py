"""``spotdl server`` — selfhost uvicorn wiring.

``create_app`` / ``uvicorn.run`` / migrations are patched so the test asserts the
wiring (mode, host, port, migrations run, download-auth consistency checked at
startup) without building a real app or binding a socket.
"""

from __future__ import annotations

from typing import Any

import pytest
from spotdl_cli.__main__ import app
from spotdl_cli.commands import server as server_cmd
from spotdl_server.settings import DeploymentMode, Settings
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def patched(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {"run": None, "migrated": [], "create_settings": None, "checks": 0}

    def _run(app_obj: Any, **kwargs: Any) -> None:
        captured["run"] = (app_obj, kwargs)

    def _create_app(settings: Settings, **_: Any) -> object:
        captured["create_settings"] = settings
        return object()

    def _check(self: Settings) -> None:
        captured["checks"] += 1

    monkeypatch.setattr("uvicorn.run", _run)
    monkeypatch.setattr(server_cmd, "create_app", _create_app)
    monkeypatch.setattr(server_cmd, "_migrate", lambda s: captured["migrated"].append(s))
    monkeypatch.setattr(Settings, "require_download_auth_consistency", _check)
    return captured


def test_server_selfhost_wiring(patched: dict[str, Any]) -> None:
    result = runner.invoke(
        app, ["server", "--mode", "selfhost", "--host", "0.0.0.0", "--port", "9200"]
    )

    assert result.exit_code == 0
    # migrations ran on a selfhost Settings before the socket bound
    assert patched["migrated"][0].mode is DeploymentMode.SELFHOST
    # consistency was checked at startup
    assert patched["checks"] >= 1
    # create_app got selfhost Settings; uvicorn bound the requested host/port
    assert patched["create_settings"].mode is DeploymentMode.SELFHOST
    _app, kwargs = patched["run"]
    assert kwargs == {"host": "0.0.0.0", "port": 9200}


def test_server_defaults_to_selfhost(patched: dict[str, Any]) -> None:
    result = runner.invoke(app, ["server"])

    assert result.exit_code == 0
    assert patched["create_settings"].mode is DeploymentMode.SELFHOST
    _app, kwargs = patched["run"]
    assert kwargs == {"host": "127.0.0.1", "port": 8800}
