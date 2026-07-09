"""``spotdl_server.bootstrap.upgrade_to_head`` — Plan 8's programmatic seam.

Offline (SQLite tmp files). Proves the initial schema is applied, the call is
idempotent, and the Alembic config is located relative to the installed package
(works from any CWD / a wheel install), never relative to the CWD.
"""

from __future__ import annotations

from pathlib import Path

from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from spotdl_server.bootstrap import _locate_alembic, upgrade_to_head
from spotdl_server.db import models  # noqa: F401
from spotdl_server.db.base import Base
from spotdl_server.settings import Settings
from sqlalchemy import create_engine, inspect


def _reflect(db_file: Path) -> set[str]:
    engine = create_engine(f"sqlite:///{db_file}")
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _current_revision(db_file: Path) -> str | None:
    engine = create_engine(f"sqlite:///{db_file}")
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()


def _head_revision() -> str:
    ini, scripts = _locate_alembic()
    script_dir = ScriptDirectory(str(scripts))
    head = script_dir.get_current_head()
    assert head is not None
    return head


def test_upgrade_to_head_creates_schema(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    upgrade_to_head(settings)

    db_file = tmp_path / "spotdl.db"
    assert db_file.is_file()
    names = _reflect(db_file)
    assert names == set(Base.metadata.tables.keys()) | {"alembic_version"}
    assert _current_revision(db_file) == _head_revision()


def test_upgrade_to_head_is_idempotent(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    upgrade_to_head(settings)
    before = _reflect(tmp_path / "spotdl.db")
    # Second call is a no-op (already at head) and must not raise.
    upgrade_to_head(settings)
    after = _reflect(tmp_path / "spotdl.db")
    assert before == after
    assert _current_revision(tmp_path / "spotdl.db") == _head_revision()


def test_upgrade_to_head_runs_from_any_cwd(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    data_dir = tmp_path / "data"
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    settings = Settings(data_dir=data_dir)
    upgrade_to_head(settings)

    names = _reflect(data_dir / "spotdl.db")
    assert names == set(Base.metadata.tables.keys()) | {"alembic_version"}
