"""Deterministic OpenAPI export → ``apps/server/openapi.json`` (spec §3).

The schema is dumped with ``sort_keys=True`` so the bytes are stable across runs
and machines: Plan 8 generates its typed clients from this committed file and
diffs against it, and :mod:`apps.server.tests.test_openapi` fails CI on any drift.

The app is built with a **fully-enabled** settings profile (Task 12): the
community routers mount only when a feature is active — auth/voting/tokens/votes/
submissions/reports/admin require ``auth_active()``, and the OAuth router
additionally requires at least one configured provider (id + secret). Building in
``SELFHOST`` with ``auth_enabled=True``, ``voting_enabled=True`` and both GitHub +
Discord credentials set therefore materialises **every** community route in the
committed ``openapi.json`` (the client generators need the whole surface, not just
the modes a given deployment happens to enable). The credentials are inert
placeholders — no network is ever touched at schema-build time. ``version`` is
pinned to the already-stable ``spotdl_server.__version__``.

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

from pydantic import SecretStr
from spotdl_server.app import create_app
from spotdl_server.settings import DeploymentMode, Settings

# ``openapi.json`` lives next to ``apps/server/`` (the parent of ``scripts/``).
OPENAPI_PATH = Path(__file__).resolve().parent.parent / "openapi.json"

# A fully-enabled profile so *every* community router mounts and appears in the
# exported schema (see the module docstring). All secrets are inert placeholders;
# building the schema never opens a socket.
_FULL_SURFACE_SETTINGS = Settings(
    mode=DeploymentMode.SELFHOST,
    auth_enabled=True,
    voting_enabled=True,
    auth_secret_key=SecretStr("openapi-export-placeholder-secret"),
    github_client_id="openapi-export-placeholder",
    github_client_secret=SecretStr("openapi-export-placeholder"),
    discord_client_id="openapi-export-placeholder",
    discord_client_secret=SecretStr("openapi-export-placeholder"),
)


def build_openapi() -> dict[str, Any]:
    """Build the fully-enabled app and return its OpenAPI schema (full surface)."""
    app = create_app(_FULL_SURFACE_SETTINGS)
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
