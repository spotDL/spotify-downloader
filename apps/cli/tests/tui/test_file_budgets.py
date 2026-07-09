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

VIEWMODEL_CAP = 300


def _nonblank_lines(path: Path) -> int:
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def _budget_message(path: Path, n: int, cap: int) -> str:
    return (
        f"{path}: {n} lines exceeds the {cap}-line budget — move logic into a "
        "view-model or split the widget (spec §13: TUI parity must not balloon)"
    )


def test_viewmodel_files_within_budget() -> None:
    breaches: list[str] = []
    for path in sorted(_VIEWMODELS.rglob("*.py")):
        n = _nonblank_lines(path)
        if n > VIEWMODEL_CAP:
            breaches.append(_budget_message(path.relative_to(_SRC), n, VIEWMODEL_CAP))
    assert not breaches, "\n".join(breaches)
