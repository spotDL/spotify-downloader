"""In-sync guard: the checked-in generated client matches ``make clients``.

Sibling of the server's ``test_openapi.py`` / ``test_ws_schema_artifact.py``
drift guards. Regenerates both outputs into a temp dir with the identical
commands ``make clients`` runs, ``ruff format``s them, and byte-compares each
generated file against the checked-in ``_generated`` tree. On drift it fails
with the actionable ``run `make clients``` pointer, guaranteeing the artifact is
deterministic and never hand-edited.

Marked ``codegen`` (a slow, tool-spawning integration guard); it still runs in
the default ``make check`` suite.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import spotdl_cli

PACKAGE_ROOT = Path(spotdl_cli.__file__).parent
GENERATED = PACKAGE_ROOT / "_generated"


def _repo_root() -> Path:
    path = PACKAGE_ROOT
    for candidate in [path, *path.parents]:
        if (candidate / "Makefile").is_file() and (candidate / "apps").is_dir():
            return candidate
    raise RuntimeError("could not locate the workspace root from spotdl_cli")


REPO_ROOT = _repo_root()
OPENAPI_JSON = REPO_ROOT / "apps" / "server" / "openapi.json"
WS_PROTOCOL_JSON = REPO_ROOT / "apps" / "server" / "ws-protocol.json"
GENERATOR_CONFIG = REPO_ROOT / "scripts" / "openapi-python-client.yaml"


def _run(cmd: list[str], *, stdin: str | None = None) -> None:
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        input=stdin,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def _regenerate(tmp_path: Path) -> Path:
    api_out = tmp_path / "api"
    ws_out = tmp_path / "ws_models.py"
    _run(
        [
            sys.executable,
            "-m",
            "openapi_python_client",
            "generate",
            "--path",
            str(OPENAPI_JSON),
            "--meta",
            "none",
            "--output-path",
            str(api_out),
            "--config",
            str(GENERATOR_CONFIG),
            "--overwrite",
        ]
    )
    # WS models: datamodel-codegen is fed the ``message`` sub-schema (the
    # WsMessage union) via **stdin** — the committed ws-protocol.json wraps that
    # schema in a ``{"message": ..., "ws_protocol_version": ...}`` envelope whose
    # root has no schema keywords, so feeding the file directly yields a useless
    # ``RootModel[Any]``. Stdin also keeps the generated ``filename: <stdin>``
    # header deterministic (a temp-file path would leak into the output). Mirrors
    # the ``clients`` Makefile target exactly.
    message_schema = json.dumps(json.loads(WS_PROTOCOL_JSON.read_text(encoding="utf-8"))["message"])
    _run(
        [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            "--input-file-type",
            "jsonschema",
            "--output",
            str(ws_out),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.13",
            "--use-standard-collections",
            "--use-union-operator",
            "--class-name",
            "WsMessage",
            "--disable-timestamp",
        ],
        stdin=message_schema,
    )
    # Normalize identically to ``make clients``: stabilize import order (the
    # generator's TYPE_CHECKING import emission is unordered), then format. Both
    # steps use the repo's ruff config explicitly — ``make clients`` normalizes the
    # checked-in tree in place where ruff discovers the root pyproject.toml
    # (line-length 100), whereas this regeneration lands in a tmp dir outside the
    # repo where ruff would otherwise fall back to its default line-length (88).
    config = str(REPO_ROOT / "pyproject.toml")
    _run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--select",
            "I",
            "--fix",
            "--config",
            config,
            str(tmp_path),
        ]
    )
    _run([sys.executable, "-m", "ruff", "format", "--config", config, str(tmp_path)])
    return tmp_path


def _tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.py"))
    }


@pytest.mark.codegen
def test_generated_client_in_sync(tmp_path: Path) -> None:
    assert OPENAPI_JSON.is_file(), "apps/server/openapi.json missing — run `make openapi`"
    assert WS_PROTOCOL_JSON.is_file(), "apps/server/ws-protocol.json missing — run `make ws-schema`"

    regenerated = _regenerate(tmp_path)

    # Compare the openapi-python-client tree.
    expected_api = _tree(GENERATED / "api")
    actual_api = _tree(regenerated / "api")
    assert actual_api.keys() == expected_api.keys(), (
        "generated client is stale — run `make clients` "
        f"(file set differs: added={sorted(actual_api.keys() - expected_api.keys())}, "
        f"removed={sorted(expected_api.keys() - actual_api.keys())})"
    )
    for rel, expected_src in expected_api.items():
        assert actual_api[rel] == expected_src, (
            f"generated client is stale — run `make clients` (drift in api/{rel})"
        )

    # Compare the datamodel-code-generator WS models module.
    expected_ws = (GENERATED / "ws_models.py").read_text(encoding="utf-8")
    actual_ws = (regenerated / "ws_models.py").read_text(encoding="utf-8")
    assert actual_ws == expected_ws, (
        "generated client is stale — run `make clients` (drift in ws_models.py)"
    )
