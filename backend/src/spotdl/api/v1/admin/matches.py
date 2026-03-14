"""Admin match management endpoints."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import selectinload

from spotdl.api.v1.admin.deps import _relation_to_admin_match, require_admin
from spotdl.api.v1.admin.schemas import (
    AdminMatchListResponse,
    AdminMatchResponse,
    UpdateMatchStatusRequest,
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


@router.get("/matches", response_model=AdminMatchListResponse)
async def list_matches(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    match_status: Annotated[str | None, Query(alias="status")] = None,
    match_type: Annotated[str | None, Query()] = None,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminMatchListResponse:
    """List entity relations as matches for admin moderation."""
    query = (
        select(EntityRelation)
        .where(EntityRelation.relation_type == "audio_match")
        .options(
            selectinload(EntityRelation.from_entity).selectinload(Entity.canonical_data),
            selectinload(EntityRelation.to_entity).selectinload(Entity.canonical_data),
        )
    )

    if match_status:
        # Map frontend "pending" to backend "suggested"
        status_map = {"pending": "suggested", "verified": "verified", "rejected": "rejected"}
        backend_status = status_map.get(match_status, match_status)
        query = query.where(EntityRelation.status == backend_status)

    if match_type:
        if match_type == "user":
            query = query.where(EntityRelation.relation_data["manual"].as_boolean() == True)  # noqa: E712
        elif match_type == "system":
            query = query.where(
                or_(
                    EntityRelation.relation_data["manual"].as_boolean() == False,  # noqa: E712
                    ~EntityRelation.relation_data.has_key("manual"),
                )
            )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    total_pages = (total + per_page - 1) // per_page

    query = query.order_by(EntityRelation.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    relations = result.scalars().all()

    matches = [_relation_to_admin_match(r, r.from_entity, r.to_entity) for r in relations]

    return AdminMatchListResponse(
        matches=matches,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.patch("/matches/{match_id}")
async def update_match_status(
    match_id: str,
    request: UpdateMatchStatusRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminMatchResponse:
    """Update a match's (entity relation) status."""
    try:
        relation_uuid = UUID(match_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid match ID: {match_id}",
        ) from e

    result = await db.execute(
        select(EntityRelation)
        .where(EntityRelation.id == relation_uuid)
        .options(
            selectinload(EntityRelation.from_entity).selectinload(Entity.canonical_data),
            selectinload(EntityRelation.to_entity).selectinload(Entity.canonical_data),
        )
    )
    relation = result.scalar_one_or_none()

    if not relation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    # Map frontend status to backend status
    status_map = {"pending": "suggested", "verified": "verified", "rejected": "rejected"}
    relation.status = status_map.get(request.status, request.status)

    await db.flush()

    return _relation_to_admin_match(relation, relation.from_entity, relation.to_entity)


@router.delete("/matches/unverified")
async def purge_unverified_matches(
    confirm: Annotated[bool, Query()] = False,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Purge unverified (suggested/rejected) entity relations."""
    pending_count = (
        await db.execute(
            select(func.count()).where(
                EntityRelation.status == "suggested",
                EntityRelation.relation_type == "audio_match",
            )
        )
    ).scalar() or 0

    rejected_count = (
        await db.execute(
            select(func.count()).where(
                EntityRelation.status == "rejected",
                EntityRelation.relation_type == "audio_match",
            )
        )
    ).scalar() or 0

    total = pending_count + rejected_count

    if not confirm:
        return {
            "message": f"Found {total} unverified matches to delete. Pass confirm=true to proceed.",
            "pending_matches": pending_count,
            "rejected_matches": rejected_count,
            "total_to_delete": total,
        }

    await db.execute(
        delete(EntityRelation).where(
            EntityRelation.status.in_(["suggested", "rejected"]),
            EntityRelation.relation_type == "audio_match",
        )
    )
    await db.flush()

    logger.info("Admin purged %d unverified matches", total)

    return {
        "message": f"Deleted {total} unverified matches.",
        "deleted": total,
    }
