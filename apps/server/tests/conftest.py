import os
from collections.abc import AsyncIterator
from typing import Any

import pytest

# Import registers every §6.1 table on ``Base.metadata`` so the in-memory
# ``session`` fixture below can ``create_all`` the full schema.
import spotdl_server.db.models  # noqa: F401
from spotdl_server.db.base import Base
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Captured at import time — BEFORE the autouse env-stripping fixture below runs —
# so the Postgres DSN survives the SPOTDL_-prefix scrub. Unset locally (Postgres
# tests skip); CI's `python` job exports it so the dual-dialect migration tests run.
_POSTGRES_URL = os.environ.get("SPOTDL_TEST_POSTGRES_URL")


@pytest.fixture(autouse=True)
def _isolate_spotdl_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip SPOTDL_-prefixed env vars so tests relying on Settings() defaults
    are hermetic regardless of the developer's ambient shell environment."""
    for key in list(os.environ):
        if key.startswith("SPOTDL_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def postgres_url() -> str | None:
    """Async Postgres DSN for dual-dialect DB tests, or ``None`` to skip.

    Read from ``SPOTDL_TEST_POSTGRES_URL`` (captured before env isolation). When
    ``None``, Postgres-parametrized cases call ``pytest.skip`` so a developer
    without a Postgres server still gets a fully green ``make check``.
    """
    return _POSTGRES_URL


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """A fresh in-memory SQLite ``AsyncSession`` with the full schema created.

    Uses a ``StaticPool`` so every checkout shares one connection (an in-memory
    SQLite DB lives for the lifetime of a single connection). Foreign-key
    enforcement is turned on so cascade/set-null behaviour matches Postgres.
    The unit of work is the caller's: the fixture never commits — it rolls back
    and disposes the engine on teardown.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_conn: Any, _record: Any) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db_session:
        try:
            yield db_session
        finally:
            await db_session.rollback()
    await engine.dispose()
