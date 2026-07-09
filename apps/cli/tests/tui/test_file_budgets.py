"""CONTRACT B: per-file line budgets keep logic out of screens (spec §13).

The abandoned rewrite branch's TUI was **16,588 lines** — worst offenders
``core/api_client.py`` 1,738, ``screens/settings.py`` 1,605, ``screens/track.py``
1,285, ``screens/main.py`` 1,163. This plan's antidote is structural: all logic
lives in ``viewmodels/`` behind a client protocol, and this test fails the build if
any file balloons past its cap.

Phasing: the ``viewmodels/`` walk (≤300) is active from Task 1 so it gates the
view-model tasks; the ``tui/`` walk plus the single-``.tcss`` and ≤12-screens guards
land in Task 4.
"""

from __future__ import annotations

from pathlib import Path

import spotdl_cli

_SRC = Path(spotdl_cli.__file__).parent
_VIEWMODELS = _SRC / "viewmodels"
_TUI = _SRC / "tui"

VIEWMODEL_CAP = 300
# Per-tier ``tui/`` caps (§13): screens hold layout + message wiring only, widgets
# are dumber still, and the app-row files (app/router/messages) are pure shell.
SCREEN_CAP = 400
WIDGET_CAP = 250
APP_ROW_CAP = 300

# Structural gates that become the guard for every later screen task: exactly one
# stylesheet, and at most this many screen modules (screen sprawl was how the
# abandoned rewrite reached 16k lines).
MAX_SCREEN_MODULES = 12


def _nonblank_lines(path: Path) -> int:
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def _budget_message(path: Path, n: int, cap: int) -> str:
    return (
        f"{path}: {n} lines exceeds the {cap}-line budget — move logic into a "
        "view-model or split the widget (spec §13: TUI parity must not balloon)"
    )


def _breaches(root: Path, cap: int) -> list[str]:
    out: list[str] = []
    for path in sorted(root.rglob("*.py")):
        n = _nonblank_lines(path)
        if n > cap:
            out.append(_budget_message(path.relative_to(_SRC), n, cap))
    return out


def test_viewmodel_files_within_budget() -> None:
    breaches: list[str] = []
    for path in sorted(_VIEWMODELS.rglob("*.py")):
        n = _nonblank_lines(path)
        if n > VIEWMODEL_CAP:
            breaches.append(_budget_message(path.relative_to(_SRC), n, VIEWMODEL_CAP))
    assert not breaches, "\n".join(breaches)


def test_tui_files_within_budget() -> None:
    breaches: list[str] = []
    breaches += _breaches(_TUI / "screens", SCREEN_CAP)
    breaches += _breaches(_TUI / "widgets", WIDGET_CAP)
    for path in sorted(_TUI.glob("*.py")):  # app-row: top-level tui/ modules
        n = _nonblank_lines(path)
        if n > APP_ROW_CAP:
            breaches.append(_budget_message(path.relative_to(_SRC), n, APP_ROW_CAP))
    assert not breaches, "\n".join(breaches)


def test_single_stylesheet() -> None:
    sheets = sorted(p.relative_to(_SRC) for p in _TUI.rglob("*.tcss"))
    assert len(sheets) == 1, f"the TUI must ship exactly one stylesheet, found: {sheets}"


def test_screen_module_count_bounded() -> None:
    modules = sorted(
        p.relative_to(_SRC) for p in (_TUI / "screens").glob("*.py") if p.name != "__init__.py"
    )
    assert len(modules) <= MAX_SCREEN_MODULES, (
        f"{len(modules)} screen modules exceeds the {MAX_SCREEN_MODULES} cap "
        f"(one screen per concept, no sprawl): {modules}"
    )
