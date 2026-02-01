"""Alembic environment configuration for SQLAlchemy.

Uses synchronous SQLAlchemy for migrations since Alembic doesn't natively
support async. The async database URL is converted to sync automatically.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from spotdl.config import get_settings
from spotdl.db.models import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate support
target_metadata = Base.metadata


def get_sync_url() -> str:
    """Get synchronous database URL for migrations.

    Converts async drivers to sync equivalents:
    - sqlite+aiosqlite -> sqlite
    - postgresql+asyncpg -> postgresql+psycopg2
    """
    settings = get_settings()
    url = settings.database_url

    # Convert async URLs to sync
    if "+aiosqlite" in url:
        url = url.replace("+aiosqlite", "")
    elif "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg2")

    return url


# Set the database URL
config.set_main_option("sqlalchemy.url", get_sync_url())


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Enable batch mode for SQLite to support ALTER TABLE operations
        # SQLite doesn't support most ALTER TABLE statements natively
        is_sqlite = connection.dialect.name == "sqlite"

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,  # Enable batch mode for SQLite
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
