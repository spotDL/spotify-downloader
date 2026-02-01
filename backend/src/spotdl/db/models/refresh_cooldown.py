"""Refresh cooldown tracking model."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from spotdl.db.models.base import Base, TimestampMixin
from spotdl.db.types import GUID


class RefreshCooldown(Base, TimestampMixin):
    """Tracks when entities were last refreshed by users.

    Used to enforce cooldown periods (e.g., 4 hours) between refreshes
    for non-admin users.
    """

    __tablename__ = "refresh_cooldowns"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default_factory=lambda: __import__('uuid').uuid4())

    # The entity being refreshed
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # song, album, artist, playlist
    entity_id: Mapped[UUID] = mapped_column(GUID(), nullable=False)

    # The user who refreshed (nullable for anonymous refreshes)
    user_id: Mapped[UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    # When the refresh happened
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "user_id", name="uq_refresh_cooldown_entity_user"),
    )
