"""Copy Plan 5's committed OpenAPI artifact into the docs tree at build time.

This is a **thin ``mkdocs-gen-files`` shim, not a generator.** The API reference
reuses ``apps/server/openapi.json`` — the build artifact Plan 5 produces via
``apps/server/scripts/export_openapi.py`` with ``Settings(mode=SELFHOST)`` (the
full surface, downloads/queue endpoints included) and keeps honest with its
own ``test_openapi_in_sync``. There is deliberately **one** exporter, **one**
committed artifact and **one** in-sync test; this script adds no second
exporter and no second drift guard. It only makes the file available to the
Swagger-UI page as ``api/openapi.json`` during ``mkdocs build``.

Run only under the mkdocs-gen-files plugin (imported by the docs build). When
imported outside a build (e.g. a test) it does nothing.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OPENAPI_SRC = _REPO_ROOT / "apps" / "server" / "openapi.json"
_DOC_RELPATH = "api/openapi.json"


def _under_gen_files_build() -> bool:
    try:
        from mkdocs_gen_files.editor import FilesEditor
    except ImportError:
        return False
    return FilesEditor._current is not None


def copy_openapi() -> None:
    """Write ``apps/server/openapi.json`` into the virtual docs tree."""
    import mkdocs_gen_files

    payload = _OPENAPI_SRC.read_text(encoding="utf-8")
    with mkdocs_gen_files.open(_DOC_RELPATH, "w") as f:
        f.write(payload)


if _under_gen_files_build():
    copy_openapi()
