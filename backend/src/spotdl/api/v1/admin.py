"""Admin API endpoints."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from spotdl.api.v1.auth import get_current_user
from spotdl.core.reputation import ReputationReward
from spotdl.core.services.song import get_song_service, UnsupportedURLError, SongServiceError
from spotdl.db.database import get_db_session
from spotdl.db.models.match import Match
from spotdl.db.models.metadata_report import MetadataReport
from spotdl.db.models.user import User
from spotdl.db.models.vote import Vote
from spotdl.db.models.song import Song
from spotdl.db.models.artist import Artist
from spotdl.db.models.album import Album
from spotdl.db.models.playlist import Playlist
from spotdl.db.repositories.user import UserRepository

logger = logging.getLogger(__name__)

# Track server start time for uptime calculation
_server_start_time = time.time()

router = APIRouter(prefix="/admin")


class MatchStatus(StrEnum):
    """Match moderation status."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


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
    matches_submitted: int
    votes_cast: int
    reports_submitted: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    """Paginated list of users for admin."""

    users: list[AdminUserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class AdminMatchResponse(BaseModel):
    """Admin view of a match."""

    id: str
    source_url: str
    source_platform: str
    target_url: str
    target_platform: str
    score: float | None  # Renamed from match_score to match frontend expectations
    match_type: str
    status: str
    upvotes: int
    downvotes: int
    net_votes: int
    submitted_by: str | None
    submitted_by_username: str | None
    verified_by: str | None
    verified_by_username: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminMatchListResponse(BaseModel):
    """Paginated list of matches for admin."""

    matches: list[AdminMatchResponse]
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
    matches: int
    users: int


class GrowthStatsResponse(BaseModel):
    """Growth statistics."""

    songs_today: int
    songs_this_week: int
    matches_today: int
    matches_this_week: int
    new_users_today: int
    new_users_this_week: int


class CacheStatsResponse(BaseModel):
    """Cache statistics (placeholder)."""

    hit_rate: float
    size_mb: float
    entries: int


class SystemStatsResponse(BaseModel):
    """Complete system statistics."""

    entities: EntityCountsResponse
    growth: GrowthStatsResponse
    cache: CacheStatsResponse
    uptime_seconds: int


# ====== Request Models ======


class UpdateUserRequest(BaseModel):
    """Request to update a user's admin-editable fields."""

    is_active: bool | None = None
    is_admin: bool | None = None
    reputation_score: int | None = None


class UpdateMatchStatusRequest(BaseModel):
    """Request to update a match's status."""

    status: MatchStatus


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

    # Get counts for each user
    user_responses = []
    for user in users:
        # Count matches submitted
        matches_count = (
            await db.execute(
                select(func.count()).where(Match.submitted_by == user.id)
            )
        ).scalar() or 0

        # Count votes
        votes_count = (
            await db.execute(
                select(func.count()).where(Vote.user_id == user.id)
            )
        ).scalar() or 0

        # Count reports
        reports_count = (
            await db.execute(
                select(func.count()).where(MetadataReport.reporter_id == user.id)
            )
        ).scalar() or 0

        user_responses.append(
            AdminUserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                reputation_score=user.reputation_score,
                last_login=getattr(user, "last_login", None),
                matches_submitted=matches_count,
                votes_cast=votes_count,
                reports_submitted=reports_count,
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

    # Get counts
    matches_count = (
        await db.execute(
            select(func.count()).where(Match.submitted_by == user.id)
        )
    ).scalar() or 0

    votes_count = (
        await db.execute(
            select(func.count()).where(Vote.user_id == user.id)
        )
    ).scalar() or 0

    reports_count = (
        await db.execute(
            select(func.count()).where(MetadataReport.reporter_id == user.id)
        )
    ).scalar() or 0

    return AdminUserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        reputation_score=user.reputation_score,
        last_login=getattr(user, "last_login", None),
        matches_submitted=matches_count,
        votes_cast=votes_count,
        reports_submitted=reports_count,
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

    # Get counts
    matches_count = (
        await db.execute(
            select(func.count()).where(Match.submitted_by == user.id)
        )
    ).scalar() or 0

    votes_count = (
        await db.execute(
            select(func.count()).where(Vote.user_id == user.id)
        )
    ).scalar() or 0

    reports_count = (
        await db.execute(
            select(func.count()).where(MetadataReport.reporter_id == user.id)
        )
    ).scalar() or 0

    return AdminUserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        reputation_score=user.reputation_score,
        last_login=getattr(user, "last_login", None),
        matches_submitted=matches_count,
        votes_cast=votes_count,
        reports_submitted=reports_count,
        created_at=user.created_at,
    )


# ====== Match Management Endpoints ======


@router.get("/matches", response_model=AdminMatchListResponse)
async def list_matches(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[MatchStatus | None, Query(alias="status")] = None,
    match_type: Annotated[str | None, Query()] = None,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminMatchListResponse:
    """
    List all matches with admin filters (admin only).
    """
    # Build query with user relationships
    query = select(Match).options(
        selectinload(Match.submitted_by_user),
        selectinload(Match.verified_by_user),
    )

    # Apply filters
    if status_filter:
        query = query.where(Match.status == status_filter.value)

    if match_type:
        query = query.where(Match.match_type == match_type)

    # Count total
    count_query = select(func.count()).select_from(
        select(Match).where(
            and_(
                Match.status == status_filter.value if status_filter else True,
                Match.match_type == match_type if match_type else True,
            )
        ).subquery()
    )
    total = (await db.execute(count_query)).scalar() or 0
    total_pages = (total + per_page - 1) // per_page

    # Order by created_at desc
    query = query.order_by(Match.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    matches = result.scalars().all()

    match_responses = []
    for match in matches:
        match_responses.append(
            AdminMatchResponse(
                id=str(match.id),
                source_url=match.source_url,
                source_platform=match.source_platform,
                target_url=match.target_url,
                target_platform=match.target_platform,
                score=float(match.match_score) if match.match_score else None,
                match_type=match.match_type,
                status=getattr(match, "status", "pending"),
                upvotes=match.upvotes,
                downvotes=match.downvotes,
                net_votes=match.net_votes,
                submitted_by=str(match.submitted_by) if match.submitted_by else None,
                submitted_by_username=(
                    match.submitted_by_user.username
                    if match.submitted_by_user
                    else None
                ),
                verified_by=str(match.verified_by) if match.verified_by else None,
                verified_by_username=(
                    match.verified_by_user.username if match.verified_by_user else None
                ),
                created_at=match.created_at,
            )
        )

    return AdminMatchListResponse(
        matches=match_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.patch("/matches/{match_id}", response_model=AdminMatchResponse)
async def update_match_status(
    match_id: str,
    request: UpdateMatchStatusRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminMatchResponse:
    """
    Update match status (verify/reject) (admin only).
    """
    try:
        match_uuid = UUID(match_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid match ID: {match_id}",
        ) from e

    result = await db.execute(
        select(Match)
        .options(
            selectinload(Match.submitted_by_user),
            selectinload(Match.verified_by_user),
        )
        .where(Match.id == match_uuid)
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    # Track previous status for reputation calculation
    previous_status = match.status

    # Update status and verifier
    match.status = request.status.value
    if request.status == MatchStatus.VERIFIED:
        match.verified_by = admin.id

    # Award/deduct reputation to the submitter (if any)
    if match.submitted_by and previous_status == "pending":
        user_repo = UserRepository(db)
        if request.status == MatchStatus.VERIFIED:
            await user_repo.update_reputation(
                match.submitted_by, ReputationReward.MATCH_VERIFIED
            )
        elif request.status == MatchStatus.REJECTED:
            await user_repo.update_reputation(
                match.submitted_by, ReputationReward.MATCH_REJECTED
            )

    await db.commit()
    await db.refresh(match)

    logger.info(
        "Admin %s updated match %s status to %s",
        admin.username,
        match_id,
        request.status.value,
    )

    # Refresh to get updated relationships
    await db.refresh(match, ["verified_by_user"])

    return AdminMatchResponse(
        id=str(match.id),
        source_url=match.source_url,
        source_platform=match.source_platform,
        target_url=match.target_url,
        target_platform=match.target_platform,
        score=float(match.match_score) if match.match_score else None,
        match_type=match.match_type,
        status=match.status,
        upvotes=match.upvotes,
        downvotes=match.downvotes,
        net_votes=match.net_votes,
        submitted_by=str(match.submitted_by) if match.submitted_by else None,
        submitted_by_username=(
            match.submitted_by_user.username if match.submitted_by_user else None
        ),
        verified_by=str(match.verified_by) if match.verified_by else None,
        verified_by_username=(
            match.verified_by_user.username if match.verified_by_user else None
        ),
        created_at=match.created_at,
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
    songs_count = (await db.execute(select(func.count()).select_from(Song))).scalar() or 0
    artists_count = (await db.execute(select(func.count()).select_from(Artist))).scalar() or 0
    albums_count = (await db.execute(select(func.count()).select_from(Album))).scalar() or 0
    playlists_count = (await db.execute(select(func.count()).select_from(Playlist))).scalar() or 0
    matches_count = (await db.execute(select(func.count()).select_from(Match))).scalar() or 0
    users_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0

    # Growth stats
    songs_today = (
        await db.execute(
            select(func.count()).where(Song.created_at >= today_start)
        )
    ).scalar() or 0

    songs_this_week = (
        await db.execute(
            select(func.count()).where(Song.created_at >= week_start)
        )
    ).scalar() or 0

    matches_today = (
        await db.execute(
            select(func.count()).where(Match.created_at >= today_start)
        )
    ).scalar() or 0

    matches_this_week = (
        await db.execute(
            select(func.count()).where(Match.created_at >= week_start)
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

    # Cache stats - returns 0 when no cache system is configured
    # In production, this would integrate with Redis or similar
    cache_stats = CacheStatsResponse(
        hit_rate=0.0,
        size_mb=0.0,
        entries=0,
    )

    # Calculate actual uptime
    uptime = int(time.time() - _server_start_time)

    return SystemStatsResponse(
        entities=EntityCountsResponse(
            songs=songs_count,
            artists=artists_count,
            albums=albums_count,
            playlists=playlists_count,
            matches=matches_count,
            users=users_count,
        ),
        growth=GrowthStatsResponse(
            songs_today=songs_today,
            songs_this_week=songs_this_week,
            matches_today=matches_today,
            matches_this_week=matches_this_week,
            new_users_today=users_today,
            new_users_this_week=users_this_week,
        ),
        cache=cache_stats,
        uptime_seconds=uptime,
    )


# ====== Import Endpoints ======


class ImportMatchesRequest(BaseModel):
    """Request to import matches from JSON."""

    matches: list[dict]


class BulkUrlImportRequest(BaseModel):
    """Request to import songs from URLs."""

    urls: list[str] = Field(..., min_length=1, max_length=1000)


@router.post("/import/matches")
async def import_matches(
    request: ImportMatchesRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Import matches from JSON data (admin only).

    Expects a list of match objects with source_url, target_url, etc.
    """
    imported = 0
    skipped = 0
    errors = []

    for match_data in request.matches:
        try:
            # Check if match already exists
            existing = await db.execute(
                select(Match).where(
                    and_(
                        Match.source_url == match_data.get("source_url"),
                        Match.target_url == match_data.get("target_url"),
                    )
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            # Create new match
            match = Match(
                source_url=match_data["source_url"],
                source_platform=match_data.get("source_platform", "unknown"),
                target_url=match_data["target_url"],
                target_platform=match_data.get("target_platform", "unknown"),
                match_score=match_data.get("score"),
                match_type=match_data.get("match_type", "imported"),
                status=match_data.get("status", "pending"),
            )
            db.add(match)
            imported += 1
        except Exception as e:
            errors.append(str(e))

    await db.commit()

    logger.info(
        "Admin %s imported matches: %d imported, %d skipped, %d errors",
        admin.username,
        imported,
        skipped,
        len(errors),
    )

    return {
        "message": f"Import complete: {imported} imported, {skipped} skipped",
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:10] if errors else [],  # Return first 10 errors
    }


@router.post("/import/urls")
async def import_urls(
    request: BulkUrlImportRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Import songs from URLs (admin only).

    Resolves each URL to get song metadata and stores in the database.
    """
    unique_urls = list(set(request.urls))

    logger.info(
        "Admin %s importing %d URLs",
        admin.username,
        len(unique_urls),
    )

    service = get_song_service()
    resolved = 0
    skipped = 0
    errors: list[str] = []

    for url in unique_urls:
        try:
            songs = await service.resolve_url(url)
            if songs:
                resolved += len(songs)
                logger.debug("Resolved %d songs from %s", len(songs), url)
            else:
                skipped += 1
                logger.debug("No songs found for URL: %s", url)
        except UnsupportedURLError:
            skipped += 1
            errors.append(f"Unsupported URL: {url}")
            logger.warning("Unsupported URL: %s", url)
        except SongServiceError as e:
            skipped += 1
            errors.append(f"Error resolving {url}: {str(e)}")
            logger.warning("Error resolving URL %s: %s", url, e)
        except Exception as e:
            skipped += 1
            errors.append(f"Unexpected error for {url}: {str(e)}")
            logger.exception("Unexpected error resolving URL %s", url)

    return {
        "message": f"Resolved {resolved} songs from {len(unique_urls)} URLs ({skipped} failed)",
        "resolved": resolved,
        "skipped": skipped,
        "errors": errors[:10] if errors else [],
    }


# ====== Danger Zone Endpoints ======


@router.delete("/matches/unverified")
async def purge_unverified_matches(
    confirm: Annotated[bool, Query()] = False,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Purge all unverified (pending/rejected) matches (admin only).

    Requires confirm=true query parameter to execute.
    """
    if not confirm:
        # Count matches that would be deleted
        pending_count = (
            await db.execute(
                select(func.count()).where(Match.status == "pending")
            )
        ).scalar() or 0
        rejected_count = (
            await db.execute(
                select(func.count()).where(Match.status == "rejected")
            )
        ).scalar() or 0

        return {
            "message": "Dry run - add ?confirm=true to execute",
            "pending_matches": pending_count,
            "rejected_matches": rejected_count,
            "total_to_delete": pending_count + rejected_count,
        }

    # Delete pending and rejected matches
    result = await db.execute(
        select(Match).where(Match.status.in_(["pending", "rejected"]))
    )
    matches_to_delete = result.scalars().all()
    deleted_count = len(matches_to_delete)

    for match in matches_to_delete:
        await db.delete(match)

    await db.commit()

    logger.warning(
        "Admin %s purged %d unverified matches",
        admin.username,
        deleted_count,
    )

    return {
        "message": f"Purged {deleted_count} unverified matches",
        "deleted": deleted_count,
    }


@router.delete("/reset-database")
async def reset_database(
    confirm: Annotated[str, Query()] = "",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Reset database to clean state (admin only).

    WARNING: This deletes ALL data except users.
    Requires confirm=RESET query parameter to execute.
    """
    if confirm != "RESET":
        # Count what would be deleted
        songs_count = (await db.execute(select(func.count()).select_from(Song))).scalar() or 0
        artists_count = (await db.execute(select(func.count()).select_from(Artist))).scalar() or 0
        albums_count = (await db.execute(select(func.count()).select_from(Album))).scalar() or 0
        playlists_count = (await db.execute(select(func.count()).select_from(Playlist))).scalar() or 0
        matches_count = (await db.execute(select(func.count()).select_from(Match))).scalar() or 0

        return {
            "message": "Dry run - add ?confirm=RESET to execute this IRREVERSIBLE action",
            "songs_to_delete": songs_count,
            "artists_to_delete": artists_count,
            "albums_to_delete": albums_count,
            "playlists_to_delete": playlists_count,
            "matches_to_delete": matches_count,
            "users_preserved": True,
        }

    # Delete all data in order (respecting foreign keys)
    await db.execute(Match.__table__.delete())
    await db.execute(Vote.__table__.delete())
    await db.execute(MetadataReport.__table__.delete())
    await db.execute(Song.__table__.delete())
    await db.execute(Album.__table__.delete())
    await db.execute(Playlist.__table__.delete())
    await db.execute(Artist.__table__.delete())

    await db.commit()

    logger.critical(
        "Admin %s reset the database - all entity data deleted",
        admin.username,
    )

    return {
        "message": "Database reset complete - all entity data deleted",
        "users_preserved": True,
    }


# ====== Export Endpoints ======


class MatchExportItem(BaseModel):
    """Match data for export."""

    id: str
    source_url: str
    source_platform: str
    target_url: str
    target_platform: str
    score: float | None
    match_type: str
    status: str
    upvotes: int
    downvotes: int
    net_votes: int
    created_at: datetime


class UserExportItem(BaseModel):
    """Anonymized user data for export."""

    id: str
    username: str  # Kept for reference
    is_admin: bool
    is_active: bool
    reputation_score: int
    matches_submitted: int
    votes_cast: int
    reports_submitted: int
    created_at: datetime


class StatisticsExport(BaseModel):
    """Complete statistics export."""

    exported_at: datetime
    entities: EntityCountsResponse
    growth: GrowthStatsResponse
    uptime_seconds: int
    matches_by_status: dict[str, int]
    users_by_reputation_tier: dict[str, int]


@router.get("/export/matches")
async def export_matches(
    status_filter: Annotated[MatchStatus | None, Query(alias="status")] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Export all matches as JSON (admin only).

    Returns all verified matches by default, or filter by status.
    """
    query = select(Match)

    if status_filter:
        query = query.where(Match.status == status_filter.value)
    else:
        # Default to verified matches only
        query = query.where(Match.status == MatchStatus.VERIFIED.value)

    query = query.order_by(Match.created_at.desc())

    result = await db.execute(query)
    matches = result.scalars().all()

    export_items = [
        MatchExportItem(
            id=str(m.id),
            source_url=m.source_url,
            source_platform=m.source_platform,
            target_url=m.target_url,
            target_platform=m.target_platform,
            score=float(m.match_score) if m.match_score else None,
            match_type=m.match_type,
            status=m.status,
            upvotes=m.upvotes,
            downvotes=m.downvotes,
            net_votes=m.net_votes,
            created_at=m.created_at,
        ).model_dump()
        for m in matches
    ]

    logger.info(
        "Admin %s exported %d matches (status=%s)",
        admin.username,
        len(export_items),
        status_filter or "verified",
    )

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(export_items),
        "filter_status": status_filter.value if status_filter else "verified",
        "matches": export_items,
    }


@router.get("/export/users")
async def export_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Export user data (admin only).

    Exports user statistics without sensitive information (email, password).
    """
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    export_items = []
    for user in users:
        # Count matches submitted
        matches_count = (
            await db.execute(
                select(func.count()).where(Match.submitted_by == user.id)
            )
        ).scalar() or 0

        # Count votes
        votes_count = (
            await db.execute(
                select(func.count()).where(Vote.user_id == user.id)
            )
        ).scalar() or 0

        # Count reports
        reports_count = (
            await db.execute(
                select(func.count()).where(MetadataReport.reporter_id == user.id)
            )
        ).scalar() or 0

        export_items.append(
            UserExportItem(
                id=str(user.id),
                username=user.username,
                is_admin=user.is_admin,
                is_active=user.is_active,
                reputation_score=user.reputation_score,
                matches_submitted=matches_count,
                votes_cast=votes_count,
                reports_submitted=reports_count,
                created_at=user.created_at,
            ).model_dump()
        )

    logger.info("Admin %s exported %d users", admin.username, len(export_items))

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(export_items),
        "users": export_items,
    }


@router.get("/export/statistics")
async def export_statistics(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Export complete statistics (admin only).

    Includes entity counts, growth metrics, and aggregated statistics.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # Entity counts
    songs_count = (await db.execute(select(func.count()).select_from(Song))).scalar() or 0
    artists_count = (await db.execute(select(func.count()).select_from(Artist))).scalar() or 0
    albums_count = (await db.execute(select(func.count()).select_from(Album))).scalar() or 0
    playlists_count = (await db.execute(select(func.count()).select_from(Playlist))).scalar() or 0
    matches_count = (await db.execute(select(func.count()).select_from(Match))).scalar() or 0
    users_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0

    # Growth stats
    songs_today = (await db.execute(select(func.count()).where(Song.created_at >= today_start))).scalar() or 0
    songs_this_week = (await db.execute(select(func.count()).where(Song.created_at >= week_start))).scalar() or 0
    matches_today = (await db.execute(select(func.count()).where(Match.created_at >= today_start))).scalar() or 0
    matches_this_week = (await db.execute(select(func.count()).where(Match.created_at >= week_start))).scalar() or 0
    users_today = (await db.execute(select(func.count()).where(User.created_at >= today_start))).scalar() or 0
    users_this_week = (await db.execute(select(func.count()).where(User.created_at >= week_start))).scalar() or 0

    # Matches by status
    pending_count = (await db.execute(select(func.count()).where(Match.status == "pending"))).scalar() or 0
    verified_count = (await db.execute(select(func.count()).where(Match.status == "verified"))).scalar() or 0
    rejected_count = (await db.execute(select(func.count()).where(Match.status == "rejected"))).scalar() or 0

    # Users by reputation tier
    tier_low = (await db.execute(select(func.count()).where(User.reputation_score < 100))).scalar() or 0
    tier_medium = (await db.execute(select(func.count()).where(User.reputation_score.between(100, 499)))).scalar() or 0
    tier_high = (await db.execute(select(func.count()).where(User.reputation_score.between(500, 999)))).scalar() or 0
    tier_elite = (await db.execute(select(func.count()).where(User.reputation_score >= 1000))).scalar() or 0

    uptime = int(time.time() - _server_start_time)

    export = StatisticsExport(
        exported_at=now,
        entities=EntityCountsResponse(
            songs=songs_count,
            artists=artists_count,
            albums=albums_count,
            playlists=playlists_count,
            matches=matches_count,
            users=users_count,
        ),
        growth=GrowthStatsResponse(
            songs_today=songs_today,
            songs_this_week=songs_this_week,
            matches_today=matches_today,
            matches_this_week=matches_this_week,
            new_users_today=users_today,
            new_users_this_week=users_this_week,
        ),
        uptime_seconds=uptime,
        matches_by_status={
            "pending": pending_count,
            "verified": verified_count,
            "rejected": rejected_count,
        },
        users_by_reputation_tier={
            "novice (0-99)": tier_low,
            "contributor (100-499)": tier_medium,
            "trusted (500-999)": tier_high,
            "elite (1000+)": tier_elite,
        },
    )

    logger.info("Admin %s exported statistics", admin.username)

    return export.model_dump()
