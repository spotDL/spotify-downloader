"""Alembic ``0002`` up/down round-trip, additive-only proof, and parity guard.

Parallels ``test_migrations.py`` (Plan 5's guard) for the six §6.1 community
tables added by migration ``0002_community_layer``. SQLite always runs (tmp-file
DB); Postgres runs only when ``SPOTDL_TEST_POSTGRES_URL`` is set (reuses the
``postgres_url`` fixture / marker from Plan 5).

The assertions mechanically enforce the Task 2 contract:

* ``upgrade head`` (runs ``0001`` then ``0002``) creates *every* table in
  ``Base.metadata`` and nothing else.
* ``downgrade -1`` (back to ``0001``) removes **exactly** the six NEW tables and
  leaves every Plan-5 table present.
* ``downgrade base`` leaves only Alembic's bookkeeping table.
* ``compare_metadata`` after ``upgrade head`` is empty — the migration mirrors
  ``models.py`` across both revisions (the anti-churn guarantee).
* The Plan-5 votable tables (``matches`` / ``lyrics`` / ``entity_links``) have
  byte-identical reflected columns at ``head`` and at ``0001`` — ``0002`` issues
  no ALTER against any pre-existing table (additive-only).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext

# Importing models populates Base.metadata with the full §6.1 + community schema.
from spotdl_server.db import models  # noqa: F401
from spotdl_server.db.base import Base
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

_APP_ROOT = Path(__file__).resolve().parents[2]  # apps/server/
_ALEMBIC_INI = _APP_ROOT / "alembic.ini"
_ALEMBIC_DIR = _APP_ROOT / "alembic"

# The six NEW tables introduced by migration ``0002`` (spec §6.1 deferred set).
NEW_TABLES = {
    "users",
    "oauth_identities",
    "refresh_tokens",
    "api_tokens",
    "votes",
    "reports",
}
# Every other application table belongs to Plan 5 and must survive ``downgrade -1``.
PLAN5_TABLES = set(Base.metadata.tables.keys()) - NEW_TABLES
# Pre-existing votable tables ``0002`` must never ALTER.
VOTABLE_TABLES = ("matches", "lyrics", "entity_links")


def _config(url: str) -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    cfg.attributes["db_url"] = url
    return cfg


def _run_async(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


async def _table_names(url: str) -> set[str]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
    finally:
        await engine.dispose()


def _column_descriptor(sync_conn: Connection, table: str) -> dict[str, tuple[str, bool]]:
    """Reflect ``table`` into a comparable ``{name: (type_str, nullable)}`` map."""
    insp = inspect(sync_conn)
    return {
        col["name"]: (str(col["type"]), bool(col["nullable"])) for col in insp.get_columns(table)
    }


async def _reflect_columns(url: str, tables: tuple[str, ...]) -> dict[str, dict]:  # type: ignore[type-arg]
    engine = create_async_engine(url)

    def _reflect(sync_conn: Connection) -> dict[str, dict]:  # type: ignore[type-arg]
        return {t: _column_descriptor(sync_conn, t) for t in tables}

    try:
        async with engine.connect() as conn:
            return await conn.run_sync(_reflect)
    finally:
        await engine.dispose()


async def _autogen_diff(url: str) -> list:  # type: ignore[type-arg]
    engine = create_async_engine(url)

    def _compare(sync_conn: Connection) -> list:  # type: ignore[type-arg]
        ctx = MigrationContext.configure(
            sync_conn,
            opts={
                "compare_type": True,
                "target_metadata": Base.metadata,
                "render_as_batch": sync_conn.dialect.name == "sqlite",
            },
        )
        return compare_metadata(ctx, Base.metadata)

    try:
        async with engine.connect() as conn:
            return await conn.run_sync(_compare)
    finally:
        await engine.dispose()


async def _drop_everything(url: str) -> None:
    """Reset a Postgres database to an empty public schema (test isolation)."""
    from sqlalchemy import text

    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
    finally:
        await engine.dispose()


@pytest.fixture(params=["sqlite", "postgres"])
def target_url(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    postgres_url: str | None,
) -> Iterator[str]:
    if request.param == "sqlite":
        yield f"sqlite+aiosqlite:///{tmp_path / 'migrations_0002.db'}"
        return
    if postgres_url is None:
        pytest.skip("no postgres (SPOTDL_TEST_POSTGRES_URL unset)")
    _run_async(_drop_everything(postgres_url))
    yield postgres_url
    _run_async(_drop_everything(postgres_url))


def test_upgrade_head_creates_all_tables(target_url: str) -> None:
    """``upgrade head`` runs ``0001`` then ``0002`` and yields the full schema."""
    command.upgrade(_config(target_url), "head")
    names = _run_async(_table_names(target_url))
    assert names == set(Base.metadata.tables.keys()) | {"alembic_version"}
    # Sanity: the six community tables are present after head.
    assert names >= NEW_TABLES


def test_downgrade_one_removes_only_new_tables(target_url: str) -> None:
    """``downgrade -1`` drops exactly the six ``0002`` tables; Plan-5 tables stay."""
    cfg = _config(target_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "-1")  # back to 0001
    names = _run_async(_table_names(target_url))
    # The six new tables are gone ...
    assert not (names & NEW_TABLES)
    # ... and every Plan-5 table remains intact.
    assert names >= PLAN5_TABLES
    assert names == PLAN5_TABLES | {"alembic_version"}


def test_downgrade_base_leaves_only_alembic_version(target_url: str) -> None:
    cfg = _config(target_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    names = _run_async(_table_names(target_url))
    assert names <= {"alembic_version"}
    assert not (names & set(Base.metadata.tables.keys()))


def test_upgrade_head_matches_models_no_autogenerate_diff(target_url: str) -> None:
    """After ``0001`` + ``0002`` the live schema equals ``Base.metadata`` — no drift."""
    command.upgrade(_config(target_url), "head")
    diff = _run_async(_autogen_diff(target_url))
    assert diff == [], f"schema drift between migrations and models: {diff}"


def test_downgrade_one_is_additive_on_plan5_votable_tables(target_url: str) -> None:
    """``0002`` issues no ALTER: votable columns are identical at head and at 0001."""
    cfg = _config(target_url)
    command.upgrade(cfg, "head")
    at_head = _run_async(_reflect_columns(target_url, VOTABLE_TABLES))
    command.downgrade(cfg, "-1")  # back to 0001
    at_0001 = _run_async(_reflect_columns(target_url, VOTABLE_TABLES))
    assert at_head == at_0001, (
        "0002 must not ALTER matches/lyrics/entity_links (additive-only contract)"
    )
