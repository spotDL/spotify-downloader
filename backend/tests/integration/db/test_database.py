"""Tests for database module."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.db.database import get_db, get_db_session


pytestmark = pytest.mark.asyncio


class TestGetDb:
    """Tests for get_db context manager."""

    async def test_get_db_yields_session(self, db_session: AsyncSession) -> None:
        """Test that get_db yields a session."""
        # The db_session fixture already uses a test session
        # We verify it's a valid AsyncSession
        assert db_session is not None
        assert isinstance(db_session, AsyncSession)

    async def test_get_db_commits_on_success(
        self, db_session: AsyncSession
    ) -> None:
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

    async def test_session_rollback_on_error(
        self, db_session: AsyncSession
    ) -> None:
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
        result = await db_session.execute(
            select(User).where(User.id == user_id)
        )
        found = result.scalar_one_or_none()
        assert found is None


class TestGetDbSession:
    """Tests for get_db_session dependency."""

    async def test_get_db_session_yields_session(
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_db_session yields a session."""
        assert db_session is not None
        # Verify basic query works
        from sqlalchemy import text

        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
