"""The committed ``openapi.json`` is a build artifact, kept honest by a test.

``scripts/export_openapi.py`` renders the schema deterministically
(``sort_keys=True`` → byte-stable across machines) so Plan 8 can diff generated
clients against a stable file. :func:`test_openapi_in_sync` re-renders the schema
in-memory and asserts it matches the committed bytes exactly, failing with
``run `make openapi``` on any drift. :func:`test_error_envelope_documented` locks
the stable §10 error envelope into the schema's components and onto the resolve
route so the generated clients surface typed errors.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "export_openapi.py"
_OPENAPI_PATH = Path(__file__).resolve().parent.parent / "openapi.json"


def _load_export_module() -> ModuleType:
    """Import ``scripts/export_openapi.py`` by path (it is not on ``sys.path``)."""
    spec = importlib.util.spec_from_file_location("export_openapi", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_openapi_in_sync() -> None:
    """The committed ``openapi.json`` must equal the freshly rendered schema."""
    export = _load_export_module()
    rendered = export.render_openapi()
    committed = _OPENAPI_PATH.read_text(encoding="utf-8")
    assert rendered == committed, "openapi.json is stale — run `make openapi`"


def test_openapi_is_deterministic() -> None:
    """Rendering twice yields identical bytes (``sort_keys`` guarantees stability)."""
    export = _load_export_module()
    assert export.render_openapi() == export.render_openapi()


def test_error_envelope_documented() -> None:
    """``ErrorEnvelope`` is a component schema and documents the resolve route."""
    export = _load_export_module()
    schema = export.build_openapi()

    assert "ErrorEnvelope" in schema["components"]["schemas"]

    resolve_responses = schema["paths"]["/api/v1/resolve"]["post"]["responses"]
    assert "ErrorEnvelope" in json.dumps(resolve_responses)


def test_community_routes_documented() -> None:
    """Every Plan 6 community surface is present in the fully-enabled export.

    The export builds a fully-enabled app (auth + voting + both OAuth providers),
    so one representative route from each new router — auth, votes, submissions,
    reports, admin, PATs — must appear in the committed schema, and the closed
    ``ErrorCode`` vocabulary must document every new community code so Plan 8's
    generated clients surface them as typed errors.
    """
    export = _load_export_module()
    schema = export.build_openapi()
    paths = schema["paths"]

    for path in (
        "/api/v1/auth/login",  # Task 5 — auth router
        "/api/v1/auth/tokens",  # Task 7 — PAT router
        "/api/v1/matches/{match_id}/vote",  # Task 8 — votes router
        "/api/v1/tracks/{id}/matches",  # Task 9 — submissions router (POST)
        "/api/v1/reports",  # Task 9 — reports router
        "/api/v1/admin/stats",  # Task 10 — admin router
    ):
        assert path in paths, f"missing community path: {path}"
    # The submission endpoint shares its path with the Plan 5 GET; the POST is new.
    assert "post" in paths["/api/v1/tracks/{id}/matches"]
    # Both OAuth providers materialise in the fully-enabled export.
    assert "/api/v1/auth/oauth/{provider}/authorize" in paths

    # The closed error-code vocabulary is documented as an enum, and every new
    # community code appears in it (the Plan 6 additions to spec §10).
    error_codes = set(schema["components"]["schemas"]["ErrorCode"]["enum"])
    assert {
        "authentication_required",
        "invalid_credentials",
        "invalid_token",
        "token_expired",
        "forbidden",
        "email_taken",
        "oauth_email_required",
        "not_an_audio_target",
    } <= error_codes
