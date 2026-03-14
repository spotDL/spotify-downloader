"""Admin shared dependencies and helper functions."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select

from spotdl.api.v1.admin.schemas import AdminMatchResponse, AdminUserResponse
from spotdl.api.v1.auth import get_current_user
from spotdl.db.models.entity_unified import (
    Entity,
    EntityCanonical,
    EntityRelation,
    RelationVote,
)
from spotdl.db.models.metadata_report import MetadataReport
from spotdl.db.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Track server start time for uptime calculation
_server_start_time = time.time()


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


async def _get_user_contribution_counts(
    db: AsyncSession,
    user_id: UUID,
) -> tuple[int, int, int]:
    """Get matches_submitted, votes_cast, reports_submitted for a user."""
    # Relations where discovered_by matches the user's username
    # We use the user_id in relation_votes for votes_cast
    matches_submitted = (
        await db.execute(
            select(func.count())
            .select_from(EntityRelation)
            .where(EntityRelation.discovered_by == str(user_id))
        )
    ).scalar() or 0

    votes_cast = (
        await db.execute(
            select(func.count()).select_from(RelationVote).where(RelationVote.user_id == user_id)
        )
    ).scalar() or 0

    reports_submitted = (
        await db.execute(
            select(func.count())
            .select_from(MetadataReport)
            .where(MetadataReport.reporter_id == user_id)
        )
    ).scalar() or 0

    return matches_submitted, votes_cast, reports_submitted


async def _build_admin_user_response(
    db: AsyncSession,
    user: User,
) -> AdminUserResponse:
    """Build AdminUserResponse with contribution counts."""
    matches_submitted, votes_cast, reports_submitted = await _get_user_contribution_counts(
        db, user.id
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
        matches_submitted=matches_submitted,
        votes_cast=votes_cast,
        reports_submitted=reports_submitted,
    )


def _relation_to_admin_match(
    relation: EntityRelation,
    from_entity: Entity | None = None,
    to_entity: Entity | None = None,
    from_ec: EntityCanonical | None = None,
    to_ec: EntityCanonical | None = None,
) -> AdminMatchResponse:
    """Convert an EntityRelation to AdminMatchResponse."""
    # Try relationship-loaded canonical_data, then explicit ec, then empty
    if from_ec is None and from_entity is not None:
        from_ec = getattr(from_entity, "canonical_data", None)
    if to_ec is None and to_entity is not None:
        to_ec = getattr(to_entity, "canonical_data", None)
    from_canonical = (from_ec.canonical if from_ec else {}) or {}
    to_canonical = (to_ec.canonical if to_ec else {}) or {}

    # Map internal status to frontend-expected status
    status_map = {"suggested": "pending", "verified": "verified", "rejected": "rejected"}
    display_status = status_map.get(relation.status, relation.status)

    # Determine match_type from relation_data
    relation_data = relation.relation_data or {}
    match_type = "user" if relation_data.get("manual") else "system"

    return AdminMatchResponse(
        id=str(relation.id),
        source_url=str(from_canonical.get("url", "")),
        source_platform=str(from_canonical.get("platform", "unknown")),
        target_url=str(to_canonical.get("url", "")),
        target_platform=str(to_canonical.get("platform", "unknown")),
        score=relation.match_score,
        confidence=relation.relation_data.get("confidence", 0) if relation.relation_data else 0,
        match_type=match_type,
        status=display_status,
        upvotes=relation.upvotes,
        downvotes=relation.downvotes,
        net_votes=relation.net_votes,
        created_at=relation.created_at,
        discovered_by=relation.discovered_by,
    )
