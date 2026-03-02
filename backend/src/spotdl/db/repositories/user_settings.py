"""User settings repository for database operations."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.db.models.user_settings import UserSettings


class UserSettingsRepository:
    """Repository for user settings database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserSettings | None:
        """Get settings for a specific user."""
        result = await self.session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: uuid.UUID, **kwargs: Any) -> UserSettings:
        """Create new settings for a user."""
        settings = UserSettings(user_id=user_id, **kwargs)
        self.session.add(settings)
        await self.session.commit()
        await self.session.refresh(settings)
        return settings

    async def update(self, settings: UserSettings, **kwargs: Any) -> UserSettings:
        """Update existing settings."""
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        await self.session.commit()
        await self.session.refresh(settings)
        return settings

    async def get_or_create(self, user_id: uuid.UUID, **defaults: Any) -> tuple[UserSettings, bool]:
        """Get existing settings or create new ones with defaults."""
        settings = await self.get_by_user_id(user_id)
        if settings:
            return settings, False
        settings = await self.create(user_id, **defaults)
        return settings, True

    async def delete(self, settings: UserSettings) -> None:
        """Delete user settings (reset to defaults)."""
        await self.session.delete(settings)
        await self.session.commit()

    async def reset_to_defaults(self, user_id: uuid.UUID) -> UserSettings:
        """Reset settings to defaults by deleting and recreating."""
        settings = await self.get_by_user_id(user_id)
        if settings:
            await self.delete(settings)
        return await self.create(user_id)
