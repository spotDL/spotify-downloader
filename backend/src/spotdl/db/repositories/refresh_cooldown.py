"""Repository for refresh cooldown tracking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select

from spotdl.db.models.refresh_cooldown import RefreshCooldown
from spotdl.db.repositories.base import BaseRepository

# Cooldown period: 4 hours
COOLDOWN_HOURS = 4


class RefreshCooldownRepository(BaseRepository[RefreshCooldown]):
    """Repository for RefreshCooldown model operations."""

    model = RefreshCooldown

    async def get_cooldown(
        self,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID | None,
    ) -> RefreshCooldown | None:
        """Get the cooldown record for an entity/user combination."""
        query = select(RefreshCooldown).where(
            and_(
                RefreshCooldown.entity_type == entity_type,
                RefreshCooldown.entity_id == entity_id,
                RefreshCooldown.user_id == user_id if user_id else RefreshCooldown.user_id.is_(None),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def is_on_cooldown(
        self,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID | None,
    ) -> tuple[bool, int]:
        """
        Check if an entity is on cooldown for a user.

        Returns:
            Tuple of (is_on_cooldown, remaining_seconds)
        """
        cooldown = await self.get_cooldown(entity_type, entity_id, user_id)

        if not cooldown:
            return False, 0

        now = datetime.now(UTC)

        # Handle both naive and aware datetimes from database
        refreshed_at = cooldown.refreshed_at
        if refreshed_at.tzinfo is None:
            # Assume naive datetime is UTC
            refreshed_at = refreshed_at.replace(tzinfo=UTC)

        cooldown_end = refreshed_at + timedelta(hours=COOLDOWN_HOURS)

        if now >= cooldown_end:
            return False, 0

        remaining = (cooldown_end - now).total_seconds()
        return True, int(remaining)

    async def record_refresh(
        self,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID | None,
    ) -> RefreshCooldown:
        """Record a refresh action, updating or creating the cooldown record."""
        cooldown = await self.get_cooldown(entity_type, entity_id, user_id)

        if cooldown:
            # Update existing record
            cooldown.refreshed_at = datetime.now(UTC)
        else:
            # Create new record
            cooldown = RefreshCooldown(
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                refreshed_at=datetime.now(UTC),
            )
            self.session.add(cooldown)

        await self.session.flush()
        return cooldown
