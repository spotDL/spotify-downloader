from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from spotdl_server.settings import Settings

# The single-container SQLite deployment runs many connections at once — the
# download worker pool, its progress pump, the batch finalizer, and every API
# request each open their own connection. Two pragmas make that safe:
#   * ``journal_mode=WAL`` — readers never block the writer and a read
#     transaction never deadlocks when it upgrades to a write, so a job's
#     terminal transition (e.g. cancel's read-then-write) cannot trip an
#     un-retryable ``database is locked`` snapshot conflict against a concurrent
#     session. WAL is persisted on the file, so it only needs setting once but is
#     cheap to re-assert per connection.
#   * ``busy_timeout`` — serializes the (WAL) single writer: a second writer
#     waits up to the timeout instead of failing instantly on contention.
_SQLITE_BUSY_TIMEOUT_MS = 5000


def build_engine(settings: Settings) -> AsyncEngine:
    """Build a fresh async engine from settings.

    No module-level singleton: callers own the engine's lifecycle (the FastAPI
    lifespan builds one and disposes it on shutdown). For the SQLite default the
    parent ``data_dir`` is created so the file can be opened, and every SQLite
    connection gets FK enforcement (cascade parity with Postgres) plus WAL +
    busy-timeout pragmas so the multi-connection download pool never trips a
    "database is locked" under concurrent progress/terminal writes (see below).
    """
    if settings.database_url is None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(
        settings.effective_database_url(),
        echo=settings.db_echo,
        future=True,
    )
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def _sqlite_pragmas(dbapi_conn: Any, _record: Any) -> None:
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
            dbapi_conn.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
            # WAL is a no-op (returns "memory") for a shared in-memory DB; harmless.
            dbapi_conn.execute("PRAGMA journal_mode=WAL")

    return engine


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
