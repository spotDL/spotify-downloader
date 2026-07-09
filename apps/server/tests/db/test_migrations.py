"""Alembic dual-dialect up/down round-trip and models-parity guard.

SQLite always runs (tmp-file DB). Postgres runs only when
``SPOTDL_TEST_POSTGRES_URL`` is set (CI provides it; skipped locally). The
autogenerate-parity assertion is the primary anti-churn guarantee: after
``upgrade head`` the live schema must match ``Base.metadata`` with **zero**
diff, which mechanically proves ``0001_initial_schema.py`` mirrors ``models.py``
(including the Plan-7-reserved ``download_batches`` / ``download_jobs`` pieces).
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

# Importing models populates Base.metadata with the full §6.1 schema.
from spotdl_server.db import models  # noqa: F401
from spotdl_server.db.base import Base
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

_APP_ROOT = Path(__file__).resolve().parents[2]  # apps/server/
_ALEMBIC_INI = _APP_ROOT / "alembic.ini"
_ALEMBIC_DIR = _APP_ROOT / "alembic"


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
        yield f"sqlite+aiosqlite:///{tmp_path / 'migrations.db'}"
        return
    if postgres_url is None:
        pytest.skip("no postgres (SPOTDL_TEST_POSTGRES_URL unset)")
    _run_async(_drop_everything(postgres_url))
    yield postgres_url
    _run_async(_drop_everything(postgres_url))


def test_upgrade_head_creates_every_table(target_url: str) -> None:
    command.upgrade(_config(target_url), "head")
    names = _run_async(_table_names(target_url))
    assert names == set(Base.metadata.tables.keys()) | {"alembic_version"}


def test_downgrade_base_removes_application_tables(target_url: str) -> None:
    cfg = _config(target_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    names = _run_async(_table_names(target_url))
    # Only Alembic's own bookkeeping table may remain (or nothing).
    assert names <= {"alembic_version"}
    assert not (names & set(Base.metadata.tables.keys()))


def test_upgrade_matches_models_no_autogenerate_diff(target_url: str) -> None:
    """The migration mirrors models.py exactly — the anti-churn contract."""
    command.upgrade(_config(target_url), "head")
    diff = _run_async(_autogen_diff(target_url))
    assert diff == [], f"schema drift between migration and models: {diff}"
