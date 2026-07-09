"""CONTRACT I (AST guard): the view-model layer is framework- and client-free.

Belt-and-suspenders alongside import-linter's ``viewmodels_framework_free`` contract:
a source-level AST walk so a forbidden import fails even if ``lint-imports`` is
skipped. The ``tui/`` walk is added in Task 4 when that package exists.
"""

from __future__ import annotations

import ast
from pathlib import Path

import spotdl_cli

_SRC = Path(spotdl_cli.__file__).parent
_VIEWMODELS = _SRC / "viewmodels"

# View-models may import only stdlib + views/errors/config. These roots are banned.
_VM_FORBIDDEN = (
    "textual",
    "httpx",
    "httpx_ws",
    "httpcore",
    "spotdl_server",
    "uvicorn",
    "spotdl_cli._generated",
    "spotdl_cli.client",
    "spotdl_cli.transport",
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            modules.add(node.module)
    return modules


def _hits(module: str, forbidden: tuple[str, ...]) -> str | None:
    for root in forbidden:
        if module == root or module.startswith(root + "."):
            return root
    return None


def test_viewmodels_package_exists() -> None:
    assert _VIEWMODELS.is_dir()
    assert list(_VIEWMODELS.glob("*.py"))


def test_viewmodels_import_no_framework_or_client() -> None:
    violations: list[str] = []
    for path in sorted(_VIEWMODELS.rglob("*.py")):
        for module in _imported_modules(path):
            root = _hits(module, _VM_FORBIDDEN)
            if root is not None:
                violations.append(f"{path.relative_to(_SRC)} imports forbidden {module!r} ({root})")
    assert not violations, "view-models must stay framework/client-free:\n" + "\n".join(violations)
