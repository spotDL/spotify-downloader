"""Admin user management endpoints."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select

from spotdl.api.v1.admin.deps import (
    _build_admin_user_response,
    require_admin,
)
from spotdl.api.v1.admin.schemas import (
    AdminUserListResponse,
    AdminUserResponse,
    UpdateUserRequest,
)
from spotdl.db.database import get_db_session
from spotdl.db.models.entity_unified import (
    EntityRelation,
    RelationVote,
)
from spotdl.db.models.metadata_report import MetadataReport
from spotdl.db.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


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
    """List all users with filters (admin only)."""
    query = select(User)

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

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    total_pages = (total + per_page - 1) // per_page

    allowed_sort_columns = {"created_at", "username", "email", "reputation_score", "last_login"}
    if sort_by not in allowed_sort_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by: {sort_by}. Allowed: {', '.join(sorted(allowed_sort_columns))}",
        )
    sort_column = getattr(User, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    users = list(result.scalars().all())

    # Batch-load contribution counts to avoid N+1 queries
    user_ids = [u.id for u in users]
    matches_map: dict[UUID, int] = {}
    votes_map: dict[UUID, int] = {}
    reports_map: dict[UUID, int] = {}

    if user_ids:
        # Matches submitted (grouped by user)
        matches_result = await db.execute(
            select(EntityRelation.discovered_by, func.count())
            .where(EntityRelation.discovered_by.in_([str(uid) for uid in user_ids]))
            .group_by(EntityRelation.discovered_by)
        )
        for discovered_by, count in matches_result.all():
            try:
                matches_map[UUID(discovered_by)] = count
            except ValueError:
                pass

        # Votes cast (grouped by user)
        votes_result = await db.execute(
            select(RelationVote.user_id, func.count())
            .where(RelationVote.user_id.in_(user_ids))
            .group_by(RelationVote.user_id)
        )
        for uid, count in votes_result.all():
            votes_map[uid] = count

        # Reports submitted (grouped by user)
        reports_result = await db.execute(
            select(MetadataReport.reporter_id, func.count())
            .where(MetadataReport.reporter_id.in_(user_ids))
            .group_by(MetadataReport.reporter_id)
        )
        for uid, count in reports_result.all():
            reports_map[uid] = count

    user_responses = [
        AdminUserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            reputation_score=user.reputation_score,
            last_login=getattr(user, "last_login", None),
            created_at=user.created_at,
            matches_submitted=matches_map.get(user.id, 0),
            votes_cast=votes_map.get(user.id, 0),
            reports_submitted=reports_map.get(user.id, 0),
        )
        for user in users
    ]

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
    """Get detailed user information (admin only)."""
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

    return await _build_admin_user_response(db, user)


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminUserResponse:
    """Update user admin-editable fields (admin only)."""
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

    if user.id == admin.id and request.is_admin is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin status",
        )

    if request.is_active is not None:
        user.is_active = request.is_active
    if request.is_admin is not None:
        user.is_admin = request.is_admin
    if request.reputation_score is not None:
        user.reputation_score = request.reputation_score

    await db.flush()

    logger.info(
        "Admin %s updated user %s: is_active=%s, is_admin=%s, reputation=%s",
        admin.username,
        user.username,
        request.is_active,
        request.is_admin,
        request.reputation_score,
    )

    return await _build_admin_user_response(db, user)
