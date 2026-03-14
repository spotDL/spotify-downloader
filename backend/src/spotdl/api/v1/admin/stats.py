"""Admin statistics endpoints."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from spotdl.api.v1.admin.deps import _server_start_time, require_admin
from spotdl.api.v1.admin.schemas import (
    EntityCountsResponse,
    GrowthStatsResponse,
    SystemStatsResponse,
)
from spotdl.db.database import get_db_session
from spotdl.db.models.entity_unified import (
    Entity,
    EntityRelation,
)
from spotdl.db.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> SystemStatsResponse:
    """Get system statistics (admin only)."""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = week_start - timedelta(days=week_start.weekday())

    songs_count = (
        await db.execute(select(func.count()).where(Entity.entity_type == "track"))
    ).scalar() or 0
    artists_count = (
        await db.execute(select(func.count()).where(Entity.entity_type == "artist"))
    ).scalar() or 0
    albums_count = (
        await db.execute(select(func.count()).where(Entity.entity_type == "album"))
    ).scalar() or 0
    playlists_count = (
        await db.execute(select(func.count()).where(Entity.entity_type == "playlist"))
    ).scalar() or 0
    relations_count = (
        await db.execute(select(func.count()).select_from(EntityRelation))
    ).scalar() or 0
    users_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0

    entities_today = (
        await db.execute(select(func.count()).where(Entity.created_at >= today_start))
    ).scalar() or 0

    entities_this_week = (
        await db.execute(select(func.count()).where(Entity.created_at >= week_start))
    ).scalar() or 0

    relations_today = (
        await db.execute(select(func.count()).where(EntityRelation.created_at >= today_start))
    ).scalar() or 0

    relations_this_week = (
        await db.execute(select(func.count()).where(EntityRelation.created_at >= week_start))
    ).scalar() or 0

    users_today = (
        await db.execute(select(func.count()).where(User.created_at >= today_start))
    ).scalar() or 0

    users_this_week = (
        await db.execute(select(func.count()).where(User.created_at >= week_start))
    ).scalar() or 0

    uptime = int(time.time() - _server_start_time)

    return SystemStatsResponse(
        entities=EntityCountsResponse(
            songs=songs_count,
            artists=artists_count,
            albums=albums_count,
            playlists=playlists_count,
            relations=relations_count,
            users=users_count,
        ),
        growth=GrowthStatsResponse(
            entities_today=entities_today,
            entities_this_week=entities_this_week,
            relations_today=relations_today,
            relations_this_week=relations_this_week,
            new_users_today=users_today,
            new_users_this_week=users_this_week,
        ),
        uptime_seconds=uptime,
    )
