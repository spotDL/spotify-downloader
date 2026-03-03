"""User repository for user data access."""

from __future__ import annotations

import uuid

from sqlalchemy import exists, select, update

from spotdl.db.models.user import User
from spotdl.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    model = User

    async def get_by_username(self, username: str) -> User | None:
        """Get a user by username."""
        query = select(User).where(User.username == username)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email."""
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def username_exists(self, username: str) -> bool:
        """Check if username already exists."""
        result = await self.session.execute(
            select(exists().where(User.username == username))
        )
        return result.scalar() or False

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        result = await self.session.execute(
            select(exists().where(User.email == email))
        )
        return result.scalar() or False

    async def update_reputation(self, user_id: uuid.UUID, delta: int) -> User | None:
        """Update user reputation score atomically."""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(reputation_score=User.reputation_score + delta)
        )
        await self.session.flush()
        return await self.get_by_id(user_id)
