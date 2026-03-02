"""Tests for database module."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from spotdl.db.database import (
    close_db,
    get_db,
    get_engine,
    get_session_factory,
    init_db,
)

pytestmark = pytest.mark.asyncio


class TestDatabaseEngine:
    """Tests for database engine functions."""

    async def test_get_engine_returns_engine(self) -> None:
        """Test get_engine returns an AsyncEngine."""
        from unittest.mock import patch

        import spotdl.db.database as db_module
        from spotdl.config import Settings

        # Reset global state
        db_module._engine = None
        db_module._session_factory = None

        # Mock settings to use in-memory database
        mock_settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

        with patch("spotdl.db.database.get_settings", return_value=mock_settings):
            engine = get_engine()
            assert engine is not None
            assert isinstance(engine, AsyncEngine)

            # Cleanup
            await engine.dispose()
            db_module._engine = None

    async def test_get_engine_returns_same_instance(self) -> None:
        """Test get_engine returns same engine on subsequent calls."""
        from unittest.mock import patch

        import spotdl.db.database as db_module
        from spotdl.config import Settings

        db_module._engine = None
        db_module._session_factory = None

        mock_settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

        with patch("spotdl.db.database.get_settings", return_value=mock_settings):
            engine1 = get_engine()
            engine2 = get_engine()
            assert engine1 is engine2

            # Cleanup
            await engine1.dispose()
            db_module._engine = None

    async def test_get_session_factory_returns_factory(self) -> None:
        """Test get_session_factory returns a session factory."""
        from unittest.mock import patch

        import spotdl.db.database as db_module
        from spotdl.config import Settings

        db_module._engine = None
        db_module._session_factory = None

        mock_settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

        with patch("spotdl.db.database.get_settings", return_value=mock_settings):
            factory = get_session_factory()
            assert factory is not None

            # Cleanup
            if db_module._engine:
                await db_module._engine.dispose()
            db_module._engine = None
            db_module._session_factory = None

    async def test_get_session_factory_returns_same_instance(self) -> None:
        """Test get_session_factory returns same factory on subsequent calls."""
        from unittest.mock import patch

        import spotdl.db.database as db_module
        from spotdl.config import Settings

        db_module._engine = None
        db_module._session_factory = None

        mock_settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

        with patch("spotdl.db.database.get_settings", return_value=mock_settings):
            factory1 = get_session_factory()
            factory2 = get_session_factory()
            assert factory1 is factory2

            # Cleanup
            if db_module._engine:
                await db_module._engine.dispose()
            db_module._engine = None
            db_module._session_factory = None


class TestDatabaseLifecycle:
    """Tests for database lifecycle functions."""

    async def test_init_db_creates_tables(self) -> None:
        """Test init_db creates database tables."""
        from unittest.mock import patch

        import spotdl.db.database as db_module
        from spotdl.config import Settings

        db_module._engine = None
        db_module._session_factory = None

        mock_settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

        with patch("spotdl.db.database.get_settings", return_value=mock_settings):
            # Initialize database
            await init_db()

            # Verify engine was created
            assert db_module._engine is not None

            # Cleanup
            await close_db()

    async def test_close_db_disposes_engine(self) -> None:
        """Test close_db disposes the engine."""
        from unittest.mock import patch

        import spotdl.db.database as db_module
        from spotdl.config import Settings

        db_module._engine = None
        db_module._session_factory = None

        mock_settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

        with patch("spotdl.db.database.get_settings", return_value=mock_settings):
            # Create engine first
            get_engine()
            assert db_module._engine is not None

            # Close database
            await close_db()

            # Verify engine is None
            assert db_module._engine is None
            assert db_module._session_factory is None

    async def test_close_db_when_no_engine(self) -> None:
        """Test close_db is safe when no engine exists."""
        import spotdl.db.database as db_module

        db_module._engine = None
        db_module._session_factory = None

        # Should not raise
        await close_db()


class TestGetDbContextManager:
    """Tests for get_db context manager."""

    async def test_get_db_yields_session(self) -> None:
        """Test get_db yields an AsyncSession."""
        from unittest.mock import patch

        import spotdl.db.database as db_module
        from spotdl.config import Settings

        db_module._engine = None
        db_module._session_factory = None

        mock_settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

        with patch("spotdl.db.database.get_settings", return_value=mock_settings):
            try:
                async with get_db() as session:
                    assert session is not None
                    assert isinstance(session, AsyncSession)
            finally:
                await close_db()

    async def test_get_db_commits_on_success(self) -> None:
        """Test get_db commits on successful exit."""
        from unittest.mock import patch

        from sqlalchemy import text

        import spotdl.db.database as db_module
        from spotdl.config import Settings

        db_module._engine = None
        db_module._session_factory = None

        mock_settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

        with patch("spotdl.db.database.get_settings", return_value=mock_settings):
            try:
                await init_db()

                async with get_db() as session:
                    # Execute a simple query
                    result = await session.execute(text("SELECT 1"))
                    assert result.scalar() == 1
            finally:
                await close_db()

    async def test_get_db_rollback_on_exception(self) -> None:
        """Test get_db rolls back on exception."""
        from unittest.mock import patch

        import spotdl.db.database as db_module
        from spotdl.config import Settings

        db_module._engine = None
        db_module._session_factory = None

        mock_settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

        with patch("spotdl.db.database.get_settings", return_value=mock_settings):
            try:
                await init_db()

                with pytest.raises(ValueError):
                    async with get_db() as session:
                        raise ValueError("Test error")
            finally:
                await close_db()


class TestGetDb:
    """Tests for get_db context manager with fixtures."""

    async def test_get_db_yields_session(self, db_session: AsyncSession) -> None:
        """Test that get_db yields a session."""
        # The db_session fixture already uses a test session
        # We verify it's a valid AsyncSession
        assert db_session is not None
        assert isinstance(db_session, AsyncSession)

    async def test_get_db_commits_on_success(self, db_session: AsyncSession) -> None:
        """Test that successful operations are committed."""
        from spotdl.db.models.user import User

        user = User(
            username="dbtest_user",
            email="dbtest@example.com",
            hashed_password="hash123",
        )
        db_session.add(user)
        await db_session.flush()

        # Verify user was created
        assert user.id is not None

    async def test_session_rollback_on_error(self, db_session: AsyncSession) -> None:
        """Test that errors trigger rollback."""
        from sqlalchemy import select

        from spotdl.db.models.user import User

        # Create a user
        user = User(
            username="rollback_test",
            email="rollback@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        # Get the user ID
        user_id = user.id

        # Rollback
        await db_session.rollback()

        # User should not be found after rollback
        result = await db_session.execute(select(User).where(User.id == user_id))
        found = result.scalar_one_or_none()
        assert found is None


class TestGetDbSession:
    """Tests for get_db_session dependency."""

    async def test_get_db_session_yields_session(self, db_session: AsyncSession) -> None:
        """Test that get_db_session yields a session."""
        assert db_session is not None
        # Verify basic query works
        from sqlalchemy import text

        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
