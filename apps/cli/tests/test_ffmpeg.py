"""``spotdl ffmpeg download`` — static-binary bootstrap into the data dir.

The network fetch is patched: the injected :func:`_fetch` writes a fake binary,
so the test asserts the install path, the ``0o755`` mode, idempotency, and that
``resolve_ffmpeg_path`` then points the download command at the bootstrapped
binary — all without touching the network.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from spotdl_cli.__main__ import app
from spotdl_cli.commands import ffmpeg as ffmpeg_cmd
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def fake_fetch(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Path]]:
    """Replace the network fetch with one that writes a stub binary."""
    calls: list[tuple[str, Path]] = []

    def _fetch(url: str, dest: Path) -> None:
        calls.append((url, dest))
        dest.write_bytes(b"#!/bin/sh\necho ffmpeg\n")

    monkeypatch.setattr(ffmpeg_cmd, "_fetch", _fetch)
    return calls


def test_download_installs_and_reports_path(
    fake_fetch: list[tuple[str, Path]], tmp_path: Path
) -> None:
    result = runner.invoke(app, ["ffmpeg", "download", "--dir", str(tmp_path)])

    assert result.exit_code == 0
    dest = tmp_path / ffmpeg_cmd._binary_name()
    assert dest.exists()
    assert str(dest) in result.output
    assert len(fake_fetch) == 1
    # installed as an executable (0o755)
    mode = stat.S_IMODE(dest.stat().st_mode)
    assert mode == 0o755
    assert os.access(dest, os.X_OK)


def test_download_is_idempotent(fake_fetch: list[tuple[str, Path]], tmp_path: Path) -> None:
    dest = tmp_path / ffmpeg_cmd._binary_name()
    dest.write_bytes(b"existing")

    result = runner.invoke(app, ["ffmpeg", "download", "--dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "already present" in result.output
    assert fake_fetch == []  # no re-fetch


def test_download_force_refetches(fake_fetch: list[tuple[str, Path]], tmp_path: Path) -> None:
    dest = tmp_path / ffmpeg_cmd._binary_name()
    dest.write_bytes(b"existing")

    result = runner.invoke(app, ["ffmpeg", "download", "--dir", str(tmp_path), "--force"])

    assert result.exit_code == 0
    assert len(fake_fetch) == 1


def test_resolve_ffmpeg_path_prefers_bootstrapped(tmp_path: Path) -> None:
    # absent → bare command name off PATH
    assert ffmpeg_cmd.resolve_ffmpeg_path(tmp_path) == "ffmpeg"

    binary = ffmpeg_cmd.ffmpeg_dir(tmp_path) / ffmpeg_cmd._binary_name()
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"x")

    assert ffmpeg_cmd.resolve_ffmpeg_path(tmp_path) == str(binary)


def test_download_uses_data_dir_by_default(
    fake_fetch: list[tuple[str, Path]], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ffmpeg_cmd, "default_data_dir", lambda: tmp_path)

    result = runner.invoke(app, ["ffmpeg", "download"])

    assert result.exit_code == 0
    expected = tmp_path / "ffmpeg" / ffmpeg_cmd._binary_name()
    assert expected.exists()
    assert fake_fetch[0][1] == expected
