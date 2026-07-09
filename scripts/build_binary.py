"""Freeze the standalone ``spotdl`` binary with PyInstaller (Plan 11, CONTRACT G).

Ports v4's ``scripts/build.py`` to the v5 monorepo layout. The onefile binary
bundles the **CLI + server + embedded SPA + Alembic migrations**: the CLI runs
the server in-process for offline use (spec §7), so the frozen executable needs
everything the ``spotdl-server`` wheel ships plus the built web UI. The entry
point is ``spotdl_cli/__main__.py``; because the CLI already launches the TUI on
a bare invocation in a TTY (Plan 8/9), the binary's **default action is the TUI**
with no extra flag (spec §12.7). ffmpeg is *not* bundled — first run offers
``spotdl ffmpeg download``.

Run ``make bundle-spa`` first so the SPA is embedded under
``spotdl_server/webui`` (this script asserts it is present).

PyInstaller quirks handled here — each ``--collect``/``--add-data`` below carries
a comment explaining why it is required. In short:

* **Embedded SPA + Alembic** — ``spotdl_server`` resolves both relative to its own
  ``__file__`` (``webui.py`` / ``bootstrap.py``). In an editable checkout they live
  *outside* the package dir (``webui`` is a build artifact; ``alembic`` sits at
  ``apps/server/``), so ``--collect-all`` alone would miss them. They are
  ``--add-data``'d into ``spotdl_server/webui`` + ``spotdl_server/alembic`` +
  ``spotdl_server/alembic.ini`` so ``Path(spotdl_server.__file__).parent`` finds
  them in the frozen tree exactly as it does in a wheel install.
* **Textual CSS** — the TUI's ``app.tcss`` (and Textual's built-in widget
  stylesheets) are package *data*, loaded via the class module path, so both
  ``spotdl_cli`` and ``textual`` are collected whole.
* **ytmusicapi locales / pykakasi dictionaries** — runtime data dirs loaded by
  path; collected whole.
* **yt-dlp lazy extractors** — collected via ``--collect-submodules`` *and*
  yt-dlp's own bundled PyInstaller hook (``__pyinstaller``), which wires up the
  lazy-extractor machinery.
* **platformdirs / uvicorn** — both use ``importlib.import_module`` to pick a
  platform/loop backend at runtime, which static analysis cannot follow, so their
  submodules are collected explicitly.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import PyInstaller.__main__
import spotdl_server
from spotdl_cli import __version__

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SERVER_PKG = Path(spotdl_server.__file__).resolve().parent

# The SPA is embedded under the server package by `make web-embed` (bundle-spa);
# without it the binary would ship an API-only server with no web UI.
_WEBUI = _SERVER_PKG / "webui"
# Alembic lives at apps/server/ in a source checkout (force-included beside the
# package only at wheel-build time). bootstrap.py looks for it next to the
# package, so we relocate it there in the frozen tree.
_ALEMBIC_DIR = _REPO_ROOT / "apps" / "server" / "alembic"
_ALEMBIC_INI = _REPO_ROOT / "apps" / "server" / "alembic.ini"


def _yt_dlp_hooks_dir() -> str:
    """Filesystem path to yt-dlp's bundled PyInstaller hooks (``__pyinstaller``).

    Located via the import spec rather than ``import yt_dlp`` so the build script
    stays free of the untyped yt-dlp module at type-check time.
    """
    spec = importlib.util.find_spec("yt_dlp")
    if spec is None or spec.origin is None:
        raise RuntimeError("yt_dlp is not installed; run `uv sync` first")
    return str(Path(spec.origin).parent / "__pyinstaller")


def _require(path: Path, hint: str) -> None:
    if not path.exists():
        raise SystemExit(f"missing {path}: {hint}")


def _add_data(src: Path, dest: str) -> list[str]:
    """A ``--add-data src{os.pathsep}dest`` pair (PyInstaller's platform syntax)."""
    return ["--add-data", f"{src}{os.pathsep}{dest}"]


def main() -> None:
    _require(_WEBUI / "index.html", "run `make bundle-spa` before building the binary")
    _require(_ALEMBIC_INI, "expected the Alembic config at apps/server/alembic.ini")
    _require(_ALEMBIC_DIR, "expected the Alembic scripts at apps/server/alembic")

    args = [
        "apps/cli/src/spotdl_cli/__main__.py",
        "--onefile",
        "--console",  # bare invocation still launches the TUI (spec §12.7)
        "--noconfirm",
        # Keep the generated .spec inside the git-ignored build/ dir (not repo root).
        "--specpath",
        "build",
        "--name",
        f"spotdl-{__version__}-{sys.platform}",
        # Embedded SPA + Alembic tree, relocated beside spotdl_server so its
        # __file__-relative loaders find them in the frozen bundle.
        *_add_data(_WEBUI, "spotdl_server/webui"),
        *_add_data(_ALEMBIC_DIR, "spotdl_server/alembic"),
        *_add_data(_ALEMBIC_INI, "spotdl_server"),
        # Our own packages, collected whole: submodules some of which are imported
        # lazily inside functions (CLI commands, TUI screens) plus data files
        # (spotdl_cli/tui/app.tcss).
        "--collect-all",
        "spotdl_cli",
        "--collect-all",
        "spotdl_server",
        "--collect-all",
        "spotdl_core",
        # Textual ships its built-in widget stylesheets as package data.
        "--collect-all",
        "textual",
        # Runtime data dirs loaded by path.
        "--collect-all",
        "ytmusicapi",  # locales/
        "--collect-all",
        "pykakasi",  # kanji dictionaries
        # yt-dlp resolves extractors lazily; collect them and let yt-dlp's own
        # hook wire up the lazy-import shim.
        "--collect-submodules",
        "yt_dlp",
        f"--additional-hooks-dir={_yt_dlp_hooks_dir()}",
        # importlib.import_module backend selection that static analysis misses.
        "--collect-submodules",
        "platformdirs",
        "--collect-submodules",
        "uvicorn",
        # SQLAlchemy imports the async SQLite DBAPI by name (the embedded server's
        # only database), so its dialect import isn't statically visible.
        "--collect-submodules",
        "aiosqlite",
    ]
    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    main()
