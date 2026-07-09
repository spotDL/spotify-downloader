import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
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


class FakeClock:
    """A controllable :class:`~spotdl_server.auth.clock.Clock` for tests.

    Holds a mutable tz-aware UTC ``datetime`` that only moves when a test calls
    :meth:`advance`. It is the single time-control seam for the whole community
    layer: token ``iat``/``exp``, refresh-token rotation/expiry, PAT expiry, and
    rate-limit windows all read time through an injected ``Clock``, so a test
    can make any of them expire deterministically without ``sleep`` or patching
    :func:`datetime.now`.
    """

    def __init__(self, start: datetime | None = None) -> None:
        if start is None:
            start = datetime(2026, 1, 1, tzinfo=UTC)
        if start.tzinfo is None:
            raise ValueError("FakeClock requires a tz-aware datetime")
        self._now = start.astimezone(UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        """Move the clock forward by ``seconds`` (may be fractional)."""
        self._now += timedelta(seconds=seconds)


@pytest.fixture
def clock() -> FakeClock:
    """A fresh :class:`FakeClock` anchored at 2026-01-01T00:00:00Z."""
    return FakeClock()


@pytest.fixture(autouse=True)
def _isolate_spotdl_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip SPOTDL_-prefixed env vars so tests relying on Settings() defaults
    are hermetic regardless of the developer's ambient shell environment."""
    for key in list(os.environ):
        if key.startswith("SPOTDL_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def download_settings(tmp_path: Any) -> Any:
    """A SELFHOST :class:`Settings` with library/temp dirs under ``tmp_path``.

    The single seam for download tests that need real (throwaway) on-disk
    ``effective_library_path()`` / ``effective_temp_dir()`` roots without
    touching the developer's home directory.
    """
    from spotdl_server.settings import DeploymentMode, Settings

    return Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=tmp_path,
        library_path=tmp_path / "music",
        download_temp_dir=tmp_path / "temp",
    )


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
