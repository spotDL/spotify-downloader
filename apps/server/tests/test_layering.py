"""Belt-and-suspenders layering guards for the ``apps/server`` stack (spec §6).

``.importlinter`` already enforces the same rules across the whole import graph
(the ``server_layers``, ``routers_no_orm`` and ``services_no_fastapi`` contracts);
these tests are a second, source-level line of defence that reads each module's
*direct* imports with :mod:`ast` and fails with a precise, per-file message the
moment a layering rule is crossed — no need to run ``lint-imports`` to see it.

The guards asserted here:

* **Routers are a thin HTTP shell.** No file under ``api/routers/`` may import
  SQLAlchemy or the ORM models directly (``routers_no_orm``); each router file
  stays ≤200 lines (the single home for the line-count rule).
* **Services hold no HTTP types.** No file under ``services/`` may import
  ``fastapi`` directly (``services_no_fastapi``).
* **Leaf utility packages stay leaves.** No file under ``auth/``, ``ratelimit/``
  or ``policies/`` may import ``fastapi``, the ``services``/``repositories``
  layers, or SQLAlchemy — they sit *below* services and are importable by both
  services and ``api`` without a layering violation (external deps such as
  ``redis``/``httpx``/``jwt`` are fine).
* **Layer direction holds.** Repositories never import services or routers;
  services never import routers; the ``db`` layer imports none of the above
  (``server_layers``).

``api.deps`` / ``api.errors`` / ``api.schemas`` are HTTP glue that sit *outside*
the four layers by design and are intentionally not checked here — they legally
import both FastAPI and services (see the ``.importlinter`` comment).
"""

from __future__ import annotations

import ast
from pathlib import Path

import spotdl_server.api.routers as routers_pkg
import spotdl_server.auth as auth_pkg
import spotdl_server.db as db_pkg
import spotdl_server.policies as policies_pkg
import spotdl_server.ratelimit as ratelimit_pkg
import spotdl_server.repositories as repositories_pkg
import spotdl_server.services as services_pkg

_ROUTERS_DIR = Path(routers_pkg.__file__).parent
_SERVICES_DIR = Path(services_pkg.__file__).parent
_REPOSITORIES_DIR = Path(repositories_pkg.__file__).parent
_DB_DIR = Path(db_pkg.__file__).parent
_LEAF_UTIL_DIRS = (
    Path(auth_pkg.__file__).parent,
    Path(ratelimit_pkg.__file__).parent,
    Path(policies_pkg.__file__).parent,
)


def _imported_modules(path: Path) -> set[str]:
    """Return the set of top-level dotted module names *directly* imported.

    Covers both ``import a.b`` and ``from a.b import c`` (recording ``a.b``).
    Relative imports (``from . import x``) have no module and are skipped.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
    return modules


def _imports_any(modules: set[str], *prefixes: str) -> set[str]:
    """The subset of ``modules`` equal to, or a dotted child of, any prefix."""
    hits: set[str] = set()
    for module in modules:
        for prefix in prefixes:
            if module == prefix or module.startswith(prefix + "."):
                hits.add(module)
    return hits


def _py_files(directory: Path) -> list[Path]:
    files = sorted(directory.glob("*.py"))
    assert files, f"expected python modules under {directory}"
    return files


# --------------------------------------------------------------------------
# Routers: thin HTTP shell — no ORM, ≤200 lines
# --------------------------------------------------------------------------


def test_routers_do_not_import_sqlalchemy_or_orm() -> None:
    """No ``api/routers/*.py`` imports SQLAlchemy or ``db.models`` directly."""
    for path in _py_files(_ROUTERS_DIR):
        offenders = _imports_any(_imported_modules(path), "sqlalchemy", "spotdl_server.db.models")
        assert not offenders, f"{path.name} imports forbidden ORM modules: {sorted(offenders)}"


def test_routers_under_200_lines() -> None:
    """Cheap mechanical guard for the layering rule: each router file stays a
    thin HTTP shell (≤200 lines, no business logic). Single home for this rule."""
    for path in _py_files(_ROUTERS_DIR):
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        assert line_count <= 200, f"{path.name} is {line_count} lines (>200)"


# --------------------------------------------------------------------------
# Services: orchestration only — no FastAPI
# --------------------------------------------------------------------------


def test_services_do_not_import_fastapi() -> None:
    """No ``services/*.py`` imports ``fastapi`` directly."""
    for path in _py_files(_SERVICES_DIR):
        offenders = _imports_any(_imported_modules(path), "fastapi")
        assert not offenders, f"{path.name} imports FastAPI: {sorted(offenders)}"


# --------------------------------------------------------------------------
# Leaf utility packages: auth / ratelimit / policies stay leaves
# --------------------------------------------------------------------------


def test_leaf_utility_packages_import_no_framework_or_upper_layers() -> None:
    """No ``auth``/``ratelimit``/``policies`` file imports FastAPI, the
    ``services``/``repositories`` layers, or SQLAlchemy — they are leaves below
    ``services`` (external deps like ``redis``/``httpx``/``jwt`` are allowed)."""
    for directory in _LEAF_UTIL_DIRS:
        for path in _py_files(directory):
            offenders = _imports_any(
                _imported_modules(path),
                "fastapi",
                "spotdl_server.services",
                "spotdl_server.repositories",
                "sqlalchemy",
            )
            assert not offenders, f"{path.name} imports a forbidden module: {sorted(offenders)}"


# --------------------------------------------------------------------------
# Layer direction: lower layers never import higher ones
# --------------------------------------------------------------------------


def test_repositories_do_not_import_services_or_routers() -> None:
    """Repositories are below services/routers — they must not reach up."""
    for path in _py_files(_REPOSITORIES_DIR):
        offenders = _imports_any(
            _imported_modules(path),
            "spotdl_server.services",
            "spotdl_server.api",
        )
        assert not offenders, f"{path.name} imports a higher layer: {sorted(offenders)}"


def test_services_do_not_import_routers() -> None:
    """Services are below routers — they must not import the HTTP router layer."""
    for path in _py_files(_SERVICES_DIR):
        offenders = _imports_any(_imported_modules(path), "spotdl_server.api.routers")
        assert not offenders, f"{path.name} imports the router layer: {sorted(offenders)}"


def test_db_layer_does_not_import_repositories_services_or_api() -> None:
    """The ``db`` schema layer is the bottom — it imports none of the layers above."""
    for path in _py_files(_DB_DIR):
        offenders = _imports_any(
            _imported_modules(path),
            "spotdl_server.repositories",
            "spotdl_server.services",
            "spotdl_server.api",
        )
        assert not offenders, f"{path.name} imports a higher layer: {sorted(offenders)}"
