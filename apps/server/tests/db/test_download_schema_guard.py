"""Guard test: the Plan-7 queue schema amendments landed in Plan 5's models.

Plan 7 mounts the download queue **without a migration**, relying on three
amendments having been folded into Plan 5's ``db/models.py`` / ``db/enums.py`` /
migration ``0001`` (defined-now, used-in-Plan-7):

* Amendment A — a server-only ``BatchKind`` enum in ``db.enums``.
* Amendment B — a new ``download_batches`` table.
* Amendment C — four new ``download_jobs`` columns (``batch_id``,
  ``list_position``, ``skip_reason``, ``attempts``).

This test fails loudly if any of that is missing, *before* any queue code is
written on top of it. It builds the full schema into in-memory SQLite so a
``create_all`` regression (e.g. a bad column type that SQLite rejects) also trips
here.
"""

from __future__ import annotations

from typing import Any

import spotdl_server.db.models  # noqa: F401  (registers every table on Base.metadata)
from spotdl_server.db.base import Base
from spotdl_server.db.enums import BatchKind
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Integer, String
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool


async def test_full_schema_builds_in_sqlite() -> None:
    """The whole metadata (incl. the amendments) creates cleanly on SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


def test_download_batches_table_exists() -> None:
    assert "download_batches" in Base.metadata.tables


def test_batch_kind_enum_is_non_native_varchar() -> None:
    # Amendment A: the enum is importable ...
    assert {m.value for m in BatchKind} == {"single", "album", "playlist"}
    # ... and its column is a non-native (VARCHAR + CHECK) enum, cross-dialect.
    kind_col = Base.metadata.tables["download_batches"].c["kind"]
    assert isinstance(kind_col.type, SAEnum)
    assert kind_col.type.native_enum is False


def test_download_jobs_batch_id_fk_nullable_cascade() -> None:
    col = Base.metadata.tables["download_jobs"].c["batch_id"]
    assert col.nullable is True
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert fk.column.table.name == "download_batches"
    assert fk.column.name == "id"
    assert fk.ondelete == "CASCADE"


def test_download_jobs_list_position_column() -> None:
    col = Base.metadata.tables["download_jobs"].c["list_position"]
    assert isinstance(col.type, Integer)
    assert col.nullable is True


def test_download_jobs_skip_reason_column() -> None:
    col = Base.metadata.tables["download_jobs"].c["skip_reason"]
    assert isinstance(col.type, String)
    assert col.nullable is True


def test_download_jobs_attempts_column() -> None:
    col = Base.metadata.tables["download_jobs"].c["attempts"]
    assert isinstance(col.type, Integer)
    assert col.nullable is False
    default: Any = col.default
    assert default is not None
    assert default.arg == 0
