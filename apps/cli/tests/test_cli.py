from __future__ import annotations

from pathlib import Path

import pytest
from spotdl_cli import __version__
from spotdl_cli.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def test_version_command_prints_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_version_flag_prints_version() -> None:
    """The global eager ``--version`` option (v4 shim SAME row) prints and exits."""
    for flag in ("--version", "-v"):
        result = runner.invoke(app, [flag])
        assert result.exit_code == 0, result.output
        assert __version__ in result.output


def test_status_reports_embedded_transport(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``status --offline`` forces the embedded server and reports it (no network)."""
    monkeypatch.setenv("SPOTDL_DATA_DIR", str(tmp_path))
    result = runner.invoke(app, ["status", "--offline"])
    assert result.exit_code == 0, result.output
    assert "server: ok (embedded)" in result.output
