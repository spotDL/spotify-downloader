"""Database connection and session management."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from spotdl.config import get_settings

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine."""
    global _engine

    if _engine is None:
        settings = get_settings()
        pool_kwargs: dict = {"pool_pre_ping": True}
        if not settings.database_is_sqlite:
            pool_kwargs.update(
                pool_size=5,
                max_overflow=10,
                pool_recycle=3600,
            )
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            **pool_kwargs,
        )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory."""
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    return _session_factory


def run_migrations() -> None:
    """Run Alembic migrations to upgrade database to the latest version."""
    settings = get_settings()

    # Find alembic.ini - check multiple possible locations
    # When installed as a package, alembic.ini is bundled next to the spotdl package
    import importlib.resources

    possible_paths = [
        Path("alembic.ini"),  # Current directory (Docker)
        Path(__file__).parent.parent.parent.parent / "alembic.ini",  # From source
        Path("/app/alembic.ini"),  # Docker absolute path
    ]

    # Also check inside the installed package data
    try:
        pkg_root = importlib.resources.files("spotdl")
        pkg_alembic = Path(str(pkg_root)).parent / "alembic.ini"
        if pkg_alembic not in possible_paths:
            possible_paths.append(pkg_alembic)
    except (TypeError, FileNotFoundError, ModuleNotFoundError) as exc:
        logger.debug("Could not resolve package alembic.ini: %s", exc)

    alembic_ini = None
    for path in possible_paths:
        if path.exists():
            alembic_ini = path
            break

    if alembic_ini is None:
        logger.warning("alembic.ini not found, skipping migrations")
        return

    logger.info(f"Running database migrations from {alembic_ini}")

    # Create Alembic configuration
    alembic_cfg = Config(str(alembic_ini))

    # Override the database URL from settings
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    # Set the script location relative to alembic.ini
    script_location = alembic_ini.parent / "alembic"
    if script_location.exists():
        alembic_cfg.set_main_option("script_location", str(script_location))

    try:
        # Run upgrade to head (latest migration)
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise


async def init_db() -> None:
    """
    Initialize the database by running migrations.

    This ensures the database schema is up-to-date with the latest
    migrations on every startup. Safe to run multiple times - Alembic
    tracks which migrations have already been applied.
    """
    # Run migrations synchronously (Alembic doesn't support async natively)
    run_migrations()

    # Verify connection works
    engine = get_engine()
    async with engine.connect() as conn:
        from sqlalchemy import text

        await conn.execute(text("SELECT 1"))

    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Close the database connection."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    Get a database session as an async context manager.

    Usage:
        async with get_db() as session:
            result = await session.execute(query)
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with get_db() as session:
        yield session
