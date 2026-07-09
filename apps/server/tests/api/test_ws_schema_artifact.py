"""Task 2 — the committed ``ws-protocol.json`` artifact is in sync (CONTRACT 3).

FastAPI's OpenAPI export cannot describe WS routes, so the ``WsMessage`` union is
exported as a committed JSON-Schema build artifact (mirroring ``openapi.json``).
Plan 8 generates its WS client types from this file, so drift must fail CI.
"""

from __future__ import annotations

# Import the export helpers from the script (kept alongside export_openapi.py).
import importlib.util
import json
from pathlib import Path

from spotdl_server.api.schemas import WS_PROTOCOL_VERSION

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "export_ws_schema.py"
_spec = importlib.util.spec_from_file_location("export_ws_schema", _SCRIPT)
assert _spec is not None and _spec.loader is not None
export_ws_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(export_ws_schema)

_ARTIFACT = Path(__file__).resolve().parents[2] / "ws-protocol.json"

_MESSAGE_TYPES = [
    "hello",
    "job_queued",
    "job_started",
    "progress",
    "job_finished",
    "job_failed",
    "job_cancelled",
    "batch_finished",
]


def test_ws_schema_in_sync() -> None:
    rendered = export_ws_schema.render_ws_schema()
    committed = _ARTIFACT.read_text(encoding="utf-8") if _ARTIFACT.exists() else None
    assert committed == rendered, "run `make ws-schema`"


def test_ws_schema_contains_all_message_types() -> None:
    doc = json.loads(_ARTIFACT.read_text(encoding="utf-8"))
    assert doc["ws_protocol_version"] == WS_PROTOCOL_VERSION
    text = _ARTIFACT.read_text(encoding="utf-8")
    for message_type in _MESSAGE_TYPES:
        assert f'"{message_type}"' in text, message_type
