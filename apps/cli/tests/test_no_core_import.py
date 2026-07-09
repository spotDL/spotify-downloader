"""Architecture guard: ``spotdl_cli`` never imports ``spotdl_core`` directly.

Belt-and-suspenders alongside the import-linter ``no_cli_core`` forbidden
contract. Walks **every** module under the installed ``spotdl_cli`` package
(including the checked-in ``_generated`` client tree) and parses each with
:mod:`ast`, asserting no ``import spotdl_core`` / ``from spotdl_core ...``
statement appears. Indirect reaches (``cli -> server -> core``, an allowed
layer edge) are intentionally not flagged — only *direct* CLI->core imports,
matching spec §3 and the ``no_cli_core`` contract's ``allow_indirect_imports``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import spotdl_cli

PACKAGE_ROOT = Path(spotdl_cli.__file__).parent


def _iter_modules() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def _imports_spotdl_core(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "spotdl_core" or alias.name.startswith("spotdl_core."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "spotdl_core" or module.startswith("spotdl_core."):
                return True
    return False


def test_generated_tree_exists() -> None:
    """The checked-in generated client must be present (RED until Task 1 runs)."""
    assert (PACKAGE_ROOT / "_generated" / "api").is_dir()
    assert (PACKAGE_ROOT / "_generated" / "ws_models.py").is_file()


def test_no_module_imports_spotdl_core_directly() -> None:
    offenders = [
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in _iter_modules()
        if _imports_spotdl_core(path.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"spotdl_cli modules import spotdl_core directly: {offenders}"
