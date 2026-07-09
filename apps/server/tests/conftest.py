import os
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

# Import registers every §6.1 table on ``Base.metadata`` so the in-memory
# ``session`` fixture below can ``create_all`` the full schema.
import spotdl_server.db.models  # noqa: F401
from spotdl_core.download import (
    DownloadConfig,
    DownloadOutcome,
    DownloadRequest,
    ProgressCallback,
    ProgressEvent,
    ProgressPhase,
    SkipReason,
)
from spotdl_core.download.paths import build_output_path
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


async def precreate_schema(settings: Any) -> None:
    """Create the full schema on ``settings``' DB *before* the app's lifespan runs.

    Plan 7's download pool runs a crash-recovery query (``SELECT ... FROM
    download_jobs``) the instant the lifespan starts, so — for the selfhost/
    embedded apps the offline harnesses build — the tables must already exist,
    exactly as a real deployment migrates before boot. The community harnesses
    that previously created the schema *inside* the lifespan call this first.
    """
    from spotdl_server.db.engine import build_engine

    engine = build_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


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


# --------------------------------------------------------------------------
# Plan 7 download-queue seams (Task 6): a file-backed sessionmaker (so the
# worker pool's own sessions get independent connections + real isolation, as a
# single-container SQLite deployment does) and the ``FakeDownloadEngine`` — the
# offline seam that duck-types ``spotdl_core.download.DownloadEngine.download``.
# --------------------------------------------------------------------------


@pytest.fixture
async def download_sessionmaker(tmp_path: Path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """A file-SQLite ``async_sessionmaker`` with the full schema created.

    Unlike the in-memory ``session`` fixture (one shared connection via
    ``StaticPool``), this is file-backed so the worker pool, its progress pump,
    and the finalizer each open their **own** connection — the concurrency shape
    of the real single-container deployment. FK enforcement + a busy timeout keep
    cascade behaviour and brief write-contention robust across those connections.
    """
    db_path = tmp_path / "queue.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn: Any, _record: Any) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
        dbapi_conn.execute("PRAGMA busy_timeout=5000")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield maker
    finally:
        await engine.dispose()


DownloadScript = Callable[
    ["FakeDownloadEngine", DownloadRequest, ProgressCallback | None],
    "Any",
]


class FakeDownloadEngine:
    """Offline stand-in for ``spotdl_core.download.DownloadEngine`` (the plan seam).

    Duck-types ``async download(request, on_progress=None) -> DownloadOutcome``.
    With no ``script`` it runs the happy path: emit fetch/convert/embed/done
    progress, write a real file into ``config.output_dir`` at the planned output
    path, and return a ``DOWNLOADED`` outcome. A ``script`` (an async callable
    ``(engine, request, on_progress) -> DownloadOutcome``) overrides that — the
    hook tests use to emit scripted progress, await an ``asyncio.Event`` to open a
    cancellation/drain window, or return ``SKIPPED`` / ``FAILED``. Every request is
    recorded on :attr:`requests` so a test can assert the built request's fields.
    """

    def __init__(self, *, config: DownloadConfig, script: DownloadScript | None = None) -> None:
        self._config = config
        self._script = script
        self.requests: list[DownloadRequest] = []

    async def download(
        self, request: DownloadRequest, on_progress: ProgressCallback | None = None
    ) -> DownloadOutcome:
        self.requests.append(request)
        if self._script is not None:
            return await self._script(self, request, on_progress)
        self.emit(on_progress, ProgressPhase.FETCH, 100)
        self.emit(on_progress, ProgressPhase.CONVERT, 100)
        self.emit(on_progress, ProgressPhase.EMBED, 100)
        path = self.write_output(request)
        self.emit(on_progress, ProgressPhase.DONE, 100)
        return DownloadOutcome.downloaded(request.track, path)

    # --- helpers scripts reuse -------------------------------------------
    @staticmethod
    def emit(
        on_progress: ProgressCallback | None,
        phase: ProgressPhase,
        percent: int | None = None,
        message: str | None = None,
    ) -> None:
        if on_progress is not None:
            on_progress(ProgressEvent(phase=phase, percent=percent, message=message))

    def planned_path(self, request: DownloadRequest) -> Path:
        return build_output_path(request, self._config)

    def write_output(self, request: DownloadRequest) -> Path:
        path = self.planned_path(request)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake-audio-bytes")
        return path


# Re-export the skip reason so worker tests can script a specific skip.
__all__ = ["FakeDownloadEngine", "SkipReason"]
