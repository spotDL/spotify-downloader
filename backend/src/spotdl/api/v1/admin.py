"""Admin API endpoints."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import selectinload

from spotdl.api.v1.auth import get_current_user
from spotdl.db.database import get_db_session
from spotdl.db.models.entity_unified import (
    Entity,
    EntityCanonical,
    EntityFieldProvenance,
    EntityRelation,
    EntitySnapshot,
    RelationVote,
)
from spotdl.db.models.lyrics import Lyrics
from spotdl.db.models.metadata_report import MetadataReport
from spotdl.db.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

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
    matches_submitted: int = 0
    votes_cast: int = 0
    reports_submitted: int = 0

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


class AdminMatchResponse(BaseModel):
    """Admin view of a match (entity relation)."""

    id: str
    source_url: str
    source_platform: str
    target_url: str
    target_platform: str
    score: float | None
    confidence: float
    match_type: str
    status: str
    upvotes: int
    downvotes: int
    net_votes: int
    created_at: datetime
    discovered_by: str | None


class AdminMatchListResponse(BaseModel):
    """Paginated list of matches for admin."""

    matches: list[AdminMatchResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class MatchExportResponse(BaseModel):
    """Export response for matches."""

    exported_at: str
    count: int
    filter_status: str
    matches: list[AdminMatchResponse]


class UserExportItem(BaseModel):
    """Single user in export."""

    id: str
    username: str
    is_admin: bool
    is_active: bool
    reputation_score: int
    matches_submitted: int
    votes_cast: int
    reports_submitted: int
    created_at: str


class UserExportResponse(BaseModel):
    """Export response for users."""

    exported_at: str
    count: int
    users: list[UserExportItem]


class StatisticsExportResponse(BaseModel):
    """Export response for statistics."""

    exported_at: str
    entities: EntityCountsResponse
    growth: GrowthStatsResponse
    uptime_seconds: int
    matches_by_status: dict[str, int]
    users_by_reputation_tier: dict[str, int]


# ====== Request Models ======


class UpdateUserRequest(BaseModel):
    """Request to update a user's admin-editable fields."""

    is_active: bool | None = None
    is_admin: bool | None = None
    reputation_score: int | None = None


class UpdateMatchStatusRequest(BaseModel):
    """Request to update a match's status."""

    status: str


class ImportMatchItem(BaseModel):
    """Single match import item."""

    source_url: str
    source_platform: str | None = None
    target_url: str
    target_platform: str | None = None
    score: float | None = None
    match_type: str | None = None
    status: str | None = None


class ImportMatchesRequest(BaseModel):
    """Request to import matches."""

    matches: list[ImportMatchItem]


class BulkUrlImportRequest(BaseModel):
    """Request to import URLs."""

    urls: list[str]


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


# ====== Helper Functions ======


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


# ====== Statistics Endpoints ======


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


# ====== Match Management Endpoints ======


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


# ====== Danger Zone Endpoints ======


@router.delete("/matches/unverified")
async def purge_unverified_matches(
    confirm: Annotated[bool, Query()] = False,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Purge unverified (suggested/rejected) entity relations."""
    pending_count = (
        await db.execute(select(func.count()).where(EntityRelation.status == "suggested"))
    ).scalar() or 0

    rejected_count = (
        await db.execute(select(func.count()).where(EntityRelation.status == "rejected"))
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
        delete(EntityRelation).where(EntityRelation.status.in_(["suggested", "rejected"]))
    )
    await db.flush()

    logger.info("Admin purged %d unverified matches", total)

    return {
        "message": f"Deleted {total} unverified matches.",
        "deleted": total,
    }


@router.delete("/reset-database")
async def reset_database(
    confirm: Annotated[str, Query()] = "",
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Reset all entity data. Users are preserved. Pass confirm=RESET to execute."""
    entities_count = (await db.execute(select(func.count()).select_from(Entity))).scalar() or 0
    relations_count = (
        await db.execute(select(func.count()).select_from(EntityRelation))
    ).scalar() or 0
    users_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0

    if confirm != "RESET":
        return {
            "message": "This will delete ALL entity data. Pass confirm=RESET to proceed.",
            "entities_to_delete": entities_count,
            "relations_to_delete": relations_count,
            "users_preserved": True,
            "users_count": users_count,
        }

    # Delete in order respecting FK constraints
    await db.execute(delete(RelationVote))
    await db.execute(delete(EntityRelation))
    await db.execute(delete(EntityFieldProvenance))
    await db.execute(delete(EntitySnapshot))
    await db.execute(delete(EntityCanonical))
    await db.execute(delete(Lyrics))
    await db.execute(delete(MetadataReport))
    await db.execute(delete(Entity))
    await db.flush()

    logger.warning(
        "Admin reset database: deleted %d entities, %d relations",
        entities_count,
        relations_count,
    )

    return {
        "message": "Database reset complete. All entity data deleted.",
        "entities_deleted": entities_count,
        "relations_deleted": relations_count,
        "users_preserved": True,
    }


# ====== Import Endpoints ======


@router.post("/import/matches")
async def import_matches(
    request: ImportMatchesRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Import matches from source/target URL pairs."""
    from spotdl.core.services.entity_unified import UnifiedEntityService

    service = UnifiedEntityService(db)
    imported = 0
    skipped = 0
    errors: list[str] = []

    for item in request.matches:
        try:
            # Discover source entity
            source_result = await service.discover(value=item.source_url, limit=1)
            if not source_result.entities:
                errors.append(f"Could not resolve source URL: {item.source_url}")
                skipped += 1
                continue

            # Discover target entity
            target_result = await service.discover(value=item.target_url, limit=1)
            if not target_result.entities:
                errors.append(f"Could not resolve target URL: {item.target_url}")
                skipped += 1
                continue

            source_entity = source_result.entities[0]
            target_entity = target_result.entities[0]

            # Check for existing relation
            existing = await db.execute(
                select(EntityRelation).where(
                    EntityRelation.from_entity_id == source_entity.id,
                    EntityRelation.to_entity_id == target_entity.id,
                    EntityRelation.relation_type == "audio_match",
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            # Create relation
            relation = EntityRelation(
                from_entity_id=source_entity.id,
                to_entity_id=target_entity.id,
                relation_type="audio_match",
                match_score=item.score,
                status=item.status or "suggested",
                discovered_by="admin_import",
                relation_data={"manual": True, "import": True},
            )
            db.add(relation)
            imported += 1

        except Exception as e:
            errors.append(f"Error importing {item.source_url} -> {item.target_url}: {e!s}")
            skipped += 1

    if imported > 0:
        await db.flush()

    return {
        "message": f"Imported {imported} matches, skipped {skipped}.",
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
    }


@router.post("/import/urls")
async def import_urls(
    request: BulkUrlImportRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Bulk import URLs by discovering entities for each."""
    from spotdl.core.services.entity_unified import UnifiedEntityService

    service = UnifiedEntityService(db)
    resolved = 0
    skipped = 0
    errors: list[str] = []

    for url in request.urls:
        try:
            result = await service.discover(value=url, limit=20)
            if result.entities:
                resolved += 1
            else:
                errors.append(f"No entities found for URL: {url}")
                skipped += 1
        except Exception as e:
            errors.append(f"Error resolving {url}: {e!s}")
            skipped += 1

    return {
        "message": f"Resolved {resolved} URLs, skipped {skipped}.",
        "resolved": resolved,
        "skipped": skipped,
        "errors": errors,
    }


# ====== Export Endpoints ======


@router.get("/export/matches", response_model=MatchExportResponse)
async def export_matches(
    match_status: Annotated[str | None, Query(alias="status")] = None,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> MatchExportResponse:
    """Export all matches (entity relations) as JSON."""
    query = (
        select(EntityRelation)
        .where(EntityRelation.relation_type == "audio_match")
        .options(
            selectinload(EntityRelation.from_entity).selectinload(Entity.canonical_data),
            selectinload(EntityRelation.to_entity).selectinload(Entity.canonical_data),
        )
        .order_by(EntityRelation.created_at.desc())
    )

    if match_status:
        status_map = {"pending": "suggested", "verified": "verified", "rejected": "rejected"}
        backend_status = status_map.get(match_status, match_status)
        query = query.where(EntityRelation.status == backend_status)

    result = await db.execute(query)
    relations = result.scalars().all()

    matches = [_relation_to_admin_match(r, r.from_entity, r.to_entity) for r in relations]

    return MatchExportResponse(
        exported_at=datetime.now(UTC).isoformat(),
        count=len(matches),
        filter_status=match_status or "all",
        matches=matches,
    )


@router.get("/export/users", response_model=UserExportResponse)
async def export_users(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> UserExportResponse:
    """Export all users as JSON."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    user_items = []
    for user in users:
        matches_submitted, votes_cast, reports_submitted = await _get_user_contribution_counts(
            db, user.id
        )
        user_items.append(
            UserExportItem(
                id=str(user.id),
                username=user.username,
                is_admin=user.is_admin,
                is_active=user.is_active,
                reputation_score=user.reputation_score,
                matches_submitted=matches_submitted,
                votes_cast=votes_cast,
                reports_submitted=reports_submitted,
                created_at=user.created_at.isoformat(),
            )
        )

    return UserExportResponse(
        exported_at=datetime.now(UTC).isoformat(),
        count=len(user_items),
        users=user_items,
    )


@router.get("/export/statistics", response_model=StatisticsExportResponse)
async def export_statistics(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> StatisticsExportResponse:
    """Export system statistics as JSON."""
    stats = await get_system_stats(_admin=_admin, db=db)

    # Matches by status
    status_counts: dict[str, int] = {}
    for status_val in ["suggested", "verified", "rejected"]:
        count = (
            await db.execute(select(func.count()).where(EntityRelation.status == status_val))
        ).scalar() or 0
        # Map to frontend terminology
        display_status = "pending" if status_val == "suggested" else status_val
        status_counts[display_status] = count

    # Users by reputation tier
    tier_counts: dict[str, int] = {}
    for tier_name, low, high in [
        ("newcomer", 0, 9),
        ("contributor", 10, 49),
        ("trusted", 50, 199),
        ("expert", 200, 999),
        ("admin", 1000, 999999),
    ]:
        count = (
            await db.execute(
                select(func.count()).where(
                    User.reputation_score >= low,
                    User.reputation_score <= high,
                )
            )
        ).scalar() or 0
        tier_counts[tier_name] = count

    return StatisticsExportResponse(
        exported_at=datetime.now(UTC).isoformat(),
        entities=stats.entities,
        growth=stats.growth,
        uptime_seconds=stats.uptime_seconds,
        matches_by_status=status_counts,
        users_by_reputation_tier=tier_counts,
    )
