"""Alembic environment — async, dual-dialect (SQLite + Postgres).

URL resolution order:
  1. ``-x db_url=...`` (CLI: ``alembic -x db_url=... upgrade head``)
  2. ``config.attributes["db_url"]`` (programmatic: bootstrap.upgrade_to_head)
  3. ``Settings().effective_database_url()`` (SQLAlchemy env override honoured
     via ``SPOTDL_DATABASE_URL`` — Settings reads it through its env prefix)

Migrations run through an **async** engine; ``connection.run_sync`` bridges to
Alembic's synchronous migration runner. ``render_as_batch`` is enabled on SQLite
so any future ALTER migration is emitted as a batch table-rebuild (SQLite-safe).
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import create_async_engine

# Importing the models module registers every §6.1 table on ``Base.metadata``,
# which is what autogenerate and ``--autogenerate`` parity checks compare against.
from spotdl_server.db import models  # noqa: F401
from spotdl_server.db.base import Base
from spotdl_server.settings import Settings

config = context.config

if config.config_file_name is not None:
    if not config.attributes.get("skip_logging_config", False):
        fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    x_args = context.get_x_argument(as_dictionary=True)
    if x_args.get("db_url"):
        return x_args["db_url"]
    attr_url = config.attributes.get("db_url")
    if attr_url:
        return str(attr_url)
    return Settings().effective_database_url()


def _is_sqlite(url: str) -> bool:
    return make_url(url).get_backend_name() == "sqlite"


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(_database_url())
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_is_sqlite(url),
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
