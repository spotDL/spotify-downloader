"""Tests for the v4→v5 migration-guide generator (Plan 11 Task 7).

The generator renders ``docs/migration/v4-to-v5.md`` from the CLI compat-shim
table. Until Plan 8 lands its ``spotdl_cli.shim.V4_FLAG_TABLE``, the generator
runs off a clearly-marked placeholder; :func:`test_activates_with_real_flag_table`
is skipped until that table is importable, then verifies the documented
interface still holds.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "gen_migration_guide.py"
_COMMITTED = Path(__file__).resolve().parents[3] / "docs" / "migration" / "v4-to-v5.md"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gen_migration_guide", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec so ``@dataclass`` can resolve ``cls.__module__`` in
    # sys.modules (required on Python 3.14 with ``from __future__ import
    # annotations``).
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


def test_render_covers_every_kind() -> None:
    """Every row-kind heading is present (SAME/RENAME/SOFT-DROP/DROP)."""
    md = _load().render_markdown()
    for heading in (
        "Unchanged flags (SAME)",
        "Renamed flags (RENAME)",
        "Obsolete no-ops (SOFT-DROP)",
        "Removed flags (DROP)",
    ):
        assert heading in md


def test_playlist_retain_track_cover_note_verbatim() -> None:
    """CONTRACT F requires the behavior-gap note rendered verbatim."""
    md = _load().render_markdown()
    assert "`--retain-track-cover` — **documented behavior gap:**" in md
    assert "also* set each track's album name to the playlist name" in md
    assert "combine with `--playlist-numbering`" in md


def test_savefile_migration_section() -> None:
    """The `.spotdl` v4→v2 auto-migration section is rendered from the field table."""
    md = _load().render_markdown()
    assert "`.spotdl` file auto-migration" in md
    # A representative, load-bearing field mapping (seconds → milliseconds).
    assert "seconds" in md and "milliseconds" in md


def test_committed_guide_is_in_sync() -> None:
    """The committed guide equals a fresh render — the drift guard (`make docs-check`)."""
    module = _load()
    assert _COMMITTED.read_text(encoding="utf-8") == module.render_markdown()


def test_check_mode_returns_zero_when_in_sync() -> None:
    module = _load()
    assert module.main(["--check"]) == 0


def test_generated_banner_present() -> None:
    """The committed file is marked GENERATED so nobody hand-edits it."""
    assert "GENERATED FILE — do not edit by hand" in _COMMITTED.read_text(encoding="utf-8")


def _real_flag_table_available() -> bool:
    import importlib

    try:
        shim = importlib.import_module("spotdl_cli.shim")
    except ImportError:
        return False
    table = getattr(shim, "V4_FLAG_TABLE", None)
    return table is not None and bool(list(table))


@pytest.mark.skipif(
    not _real_flag_table_available(),
    reason="Plan 8's spotdl_cli.shim.V4_FLAG_TABLE not landed yet — generator runs off the "
    "placeholder; this test activates automatically once the real table is importable.",
)
def test_activates_with_real_flag_table() -> None:
    """When Plan 8 lands, the generator must consume the real table successfully.

    Verifies the documented interface (``v4_flag``/``kind``/``v5_form`` per row)
    normalizes without error and produces a non-trivial guide, and that the
    generator is no longer running off the placeholder.
    """
    module = _load()
    flag_rows, using_placeholder = module.load_flag_table()
    assert using_placeholder is False
    assert len(flag_rows) >= 25  # CONTRACT F: ≥25 common flags plus the long tail
    kinds = {r.kind.upper() for r in flag_rows}
    assert {"SAME", "RENAME", "DROP"} <= kinds
    md = module.render_markdown()
    assert "# Migrating from spotDL v4" in md
    assert "PLACEHOLDER tables baked into" not in md
