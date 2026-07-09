from pathlib import Path

import pytest
from spotdl_server.db.engine import build_engine, build_sessionmaker
from spotdl_server.settings import Settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


def test_default_url_is_sqlite_aiosqlite(tmp_path: Path) -> None:
    url = Settings(data_dir=tmp_path).effective_database_url()
    assert url.startswith("sqlite+aiosqlite:///")
    assert str(tmp_path) in url
    assert url.endswith("spotdl.db")


def test_explicit_postgres_url_passthrough() -> None:
    url = "postgresql+asyncpg://u@h/db"
    assert Settings(database_url=url).effective_database_url() == url


def test_explicit_url_must_name_async_driver() -> None:
    with pytest.raises(AssertionError):
        Settings(database_url="postgresql://u@h/db").effective_database_url()


async def test_build_engine_and_sessionmaker_roundtrip(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    engine = build_engine(settings)
    assert isinstance(engine, AsyncEngine)
    maker = build_sessionmaker(engine)
    assert isinstance(maker, async_sessionmaker)
    try:
        async with maker() as session:
            result = await session.execute(text("select 1"))
            assert result.scalar_one() == 1
        assert (tmp_path / "spotdl.db").exists()
    finally:
        await engine.dispose()


def test_build_engine_creates_missing_data_dir(tmp_path: Path) -> None:
    nested = tmp_path / "does" / "not" / "exist"
    settings = Settings(data_dir=nested)
    engine = build_engine(settings)
    try:
        assert nested.is_dir()
    finally:
        # engine.dispose is async; sync close of the sync-facing pool is enough here
        engine.sync_engine.dispose()
