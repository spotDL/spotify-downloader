"""Plan 10: the SPA assets are force-included in the ``spotdl-server`` wheel.

Additive packaging check — writes a marker ``webui/index.html`` into the source
tree, builds the wheel, and asserts it ships at ``spotdl_server/webui/``. Changes
no existing route; the source ``webui/`` dir is git-ignored and restored after.
Slower than a unit test (it invokes the build backend), hence the marker.
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

_SERVER_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _SERVER_ROOT.parents[1]
_WEBUI = _SERVER_ROOT / "src" / "spotdl_server" / "webui"


@pytest.mark.packaging
def test_webui_is_force_included_in_wheel(tmp_path: Path) -> None:
    preexisting = _WEBUI.exists()
    _WEBUI.mkdir(parents=True, exist_ok=True)
    index = _WEBUI / "index.html"
    marker = "<!doctype html><title>packaged</title>"
    index.write_text(marker)
    try:
        subprocess.run(
            [
                "uv",
                "build",
                "--wheel",
                "--package",
                "spotdl-server",
                "--out-dir",
                str(tmp_path),
            ],
            cwd=_REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        wheels = list(tmp_path.glob("spotdl_server-*.whl"))
        assert wheels, "no spotdl-server wheel was built"
        with zipfile.ZipFile(wheels[0]) as wheel:
            names = set(wheel.namelist())
            assert "spotdl_server/webui/index.html" in names
            assert (
                wheel.read("spotdl_server/webui/index.html").decode() == marker
            )
    finally:
        # Restore the tree: the embed dir is a build artifact, never committed.
        if preexisting:
            index.unlink(missing_ok=True)
        else:
            shutil.rmtree(_WEBUI, ignore_errors=True)
