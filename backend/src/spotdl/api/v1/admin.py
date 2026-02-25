"""Admin API endpoints."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.api.v1.auth import get_current_user
from spotdl.db.database import get_db_session
from spotdl.db.models.user import User
from spotdl.db.models.entity_unified import Entity, EntityRelation

logger = logging.getLogger(__name__)

# Track server start time for uptime calculation
_server_start_time = time.time()

router = APIRouter(prefix="/admin")


# ====== Response Models ======


class AdminUserResponse(BaseModel):
    """Admin view of a user."""

    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    reputation_score: int
    last_login: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    """Paginated list of users for admin."""

    users: list[AdminUserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class EntityCountsResponse(BaseModel):
    """Entity counts for dashboard."""

    songs: int
    artists: int
    albums: int
    playlists: int
    relations: int
    users: int


class GrowthStatsResponse(BaseModel):
    """Growth statistics."""

    entities_today: int
    entities_this_week: int
    relations_today: int
    relations_this_week: int
    new_users_today: int
    new_users_this_week: int


class SystemStatsResponse(BaseModel):
    """Complete system statistics."""

    entities: EntityCountsResponse
    growth: GrowthStatsResponse
    uptime_seconds: int


# ====== Request Models ======


class UpdateUserRequest(BaseModel):
    """Request to update a user's admin-editable fields."""

    is_active: bool | None = None
    is_admin: bool | None = None
    reputation_score: int | None = None


# ====== Admin Dependency ======


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require admin access for endpoint."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ====== User Management Endpoints ======


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
    is_admin: Annotated[bool | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    sort_by: Annotated[str, Query()] = "created_at",
    sort_order: Annotated[str, Query()] = "desc",
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminUserListResponse:
    """
    List all users with filters (admin only).

    Supports pagination, search, and filtering by admin/active status.
    """
    # Build base query
    query = select(User)

    # Apply filters
    if search:
        search_filter = or_(
            User.username.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if is_admin is not None:
        query = query.where(User.is_admin == is_admin)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    total_pages = (total + per_page - 1) // per_page

    # Apply sorting
    sort_column = getattr(User, sort_by, User.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    users = result.scalars().all()

    user_responses = []
    for user in users:
        user_responses.append(
            AdminUserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                reputation_score=user.reputation_score,
                last_login=getattr(user, "last_login", None),
                created_at=user.created_at,
            )
        )

    return AdminUserListResponse(
        users=user_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: str,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminUserResponse:
    """
    Get detailed user information (admin only).
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID: {user_id}",
        ) from e

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return AdminUserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        reputation_score=user.reputation_score,
        last_login=getattr(user, "last_login", None),
        created_at=user.created_at,
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminUserResponse:
    """
    Update user admin-editable fields (admin only).

    Can update: is_active, is_admin, reputation_score
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID: {user_id}",
        ) from e

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-demotion from admin
    if user.id == admin.id and request.is_admin is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin status",
        )

    # Update fields
    if request.is_active is not None:
        user.is_active = request.is_active
    if request.is_admin is not None:
        user.is_admin = request.is_admin
    if request.reputation_score is not None:
        user.reputation_score = request.reputation_score

    await db.commit()
    await db.refresh(user)

    logger.info(
        "Admin %s updated user %s: is_active=%s, is_admin=%s, reputation=%s",
        admin.username,
        user.username,
        request.is_active,
        request.is_admin,
        request.reputation_score,
    )

    return AdminUserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        reputation_score=user.reputation_score,
        last_login=getattr(user, "last_login", None),
        created_at=user.created_at,
    )


# ====== Statistics Endpoints ======


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> SystemStatsResponse:
    """
    Get system statistics (admin only).
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # Go back to start of week (Monday)
    from datetime import timedelta

    week_start = week_start - timedelta(days=week_start.weekday())

    # Entity counts
    songs_count = (await db.execute(select(func.count()).where(Entity.entity_type == 'track'))).scalar() or 0
    artists_count = (await db.execute(select(func.count()).where(Entity.entity_type == 'artist'))).scalar() or 0
    albums_count = (await db.execute(select(func.count()).where(Entity.entity_type == 'album'))).scalar() or 0
    playlists_count = (await db.execute(select(func.count()).where(Entity.entity_type == 'playlist'))).scalar() or 0
    relations_count = (await db.execute(select(func.count()).select_from(EntityRelation))).scalar() or 0
    users_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0

    # Growth stats
    entities_today = (
        await db.execute(
            select(func.count()).where(Entity.created_at >= today_start)
        )
    ).scalar() or 0

    entities_this_week = (
        await db.execute(
            select(func.count()).where(Entity.created_at >= week_start)
        )
    ).scalar() or 0

    relations_today = (
        await db.execute(
            select(func.count()).where(EntityRelation.created_at >= today_start)
        )
    ).scalar() or 0

    relations_this_week = (
        await db.execute(
            select(func.count()).where(EntityRelation.created_at >= week_start)
        )
    ).scalar() or 0

    users_today = (
        await db.execute(
            select(func.count()).where(User.created_at >= today_start)
        )
    ).scalar() or 0

    users_this_week = (
        await db.execute(
            select(func.count()).where(User.created_at >= week_start)
        )
    ).scalar() or 0

    # Calculate actual uptime
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
