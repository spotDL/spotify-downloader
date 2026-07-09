"""Deterministic OpenAPI export → ``apps/server/openapi.json`` (spec §3).

The schema is dumped with ``sort_keys=True`` so the bytes are stable across runs
and machines: Plan 8 generates its typed clients from this committed file and
diffs against it, and :mod:`apps.server.tests.test_openapi` fails CI on any drift.
The app is built in :data:`DeploymentMode.SELFHOST` so the full read surface
(every router) is present in the schema, and its ``version`` is pinned to the
already-stable ``spotdl_server.__version__``.

Usage::

    python apps/server/scripts/export_openapi.py            # write openapi.json
    python apps/server/scripts/export_openapi.py --check    # exit 1 on drift
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from spotdl_server.app import create_app
from spotdl_server.settings import DeploymentMode, Settings

# ``openapi.json`` lives next to ``apps/server/`` (the parent of ``scripts/``).
OPENAPI_PATH = Path(__file__).resolve().parent.parent / "openapi.json"


def build_openapi() -> dict[str, Any]:
    """Build the SELFHOST app and return its OpenAPI schema (full read surface)."""
    app = create_app(Settings(mode=DeploymentMode.SELFHOST))
    return app.openapi()


def render_openapi() -> str:
    """Render the schema to deterministic, byte-stable JSON text."""
    schema = build_openapi()
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write ``openapi.json`` (or, with ``--check``, verify it is in sync)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare against the committed openapi.json without writing (exit 1 on drift)",
    )
    args = parser.parse_args(argv)

    rendered = render_openapi()

    if args.check:
        committed = OPENAPI_PATH.read_text(encoding="utf-8") if OPENAPI_PATH.exists() else None
        if committed != rendered:
            print("openapi.json is out of date — run `make openapi`", file=sys.stderr)
            return 1
        return 0

    OPENAPI_PATH.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
