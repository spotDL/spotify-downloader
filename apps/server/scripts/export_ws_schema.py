"""Deterministic WS-protocol export → ``apps/server/ws-protocol.json`` (CONTRACT 3).

FastAPI's OpenAPI export does not describe WebSocket routes, so the ``WsMessage``
discriminated union is exported as a committed JSON-Schema build artifact,
mirroring the ``openapi.json`` pattern: Plan 8's TS/Python clients generate their
WS message types from this file and diff against it, and
:mod:`apps.server.tests.api.test_ws_schema_artifact` fails CI on any drift.

The document wraps the union schema as
``{"ws_protocol_version": WS_PROTOCOL_VERSION, "message": <schema>}`` and is dumped
with ``sort_keys=True`` so the bytes are stable across runs and machines.

Usage::

    python apps/server/scripts/export_ws_schema.py            # write ws-protocol.json
    python apps/server/scripts/export_ws_schema.py --check    # exit 1 on drift
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter
from spotdl_server.api.schemas import WS_PROTOCOL_VERSION, WsMessage

# ``ws-protocol.json`` lives next to ``apps/server/`` (the parent of ``scripts/``).
WS_PROTOCOL_PATH = Path(__file__).resolve().parent.parent / "ws-protocol.json"


def build_ws_schema() -> dict[str, Any]:
    """Build the wrapped WS-protocol document (version envelope + union schema)."""
    message_schema = TypeAdapter(WsMessage).json_schema()
    return {"ws_protocol_version": WS_PROTOCOL_VERSION, "message": message_schema}


def render_ws_schema() -> str:
    """Render the WS-protocol document to deterministic, byte-stable JSON text."""
    return json.dumps(build_ws_schema(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write ``ws-protocol.json`` (or, with ``--check``, verify it is in sync)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare against the committed ws-protocol.json without writing (exit 1 on drift)",
    )
    args = parser.parse_args(argv)

    rendered = render_ws_schema()

    if args.check:
        committed = (
            WS_PROTOCOL_PATH.read_text(encoding="utf-8") if WS_PROTOCOL_PATH.exists() else None
        )
        if committed != rendered:
            print("ws-protocol.json is out of date — run `make ws-schema`", file=sys.stderr)
            return 1
        return 0

    WS_PROTOCOL_PATH.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
