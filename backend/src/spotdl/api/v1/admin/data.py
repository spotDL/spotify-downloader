"""Admin import/export and danger zone endpoints."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from spotdl.api.v1.admin.deps import (
    _get_user_contribution_counts,
    _relation_to_admin_match,
    require_admin,
)
from spotdl.api.v1.admin.schemas import (
    BulkUrlImportRequest,
    ImportMatchesRequest,
    MatchExportResponse,
    StatisticsExportResponse,
    UserExportItem,
    UserExportResponse,
)
from spotdl.api.v1.admin.stats import get_system_stats
from spotdl.api.v1.dependencies import get_entity_service
from spotdl.core.services.entity_unified import UnifiedEntityService
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

router = APIRouter()


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


@router.post("/import/matches")
async def import_matches(
    request: ImportMatchesRequest,
    service: Annotated[UnifiedEntityService, Depends(get_entity_service)],
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Import matches from source/target URL pairs."""
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
            logger.warning(
                "Match import failed for %s -> %s: %s",
                item.source_url,
                item.target_url,
                e,
            )
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
    service: Annotated[UnifiedEntityService, Depends(get_entity_service)],
    _admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """Bulk import URLs by discovering entities for each."""
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
            logger.warning("URL import failed for %s: %s", url, e)
            errors.append(f"Error resolving {url}: {e!s}")
            skipped += 1

    return {
        "message": f"Resolved {resolved} URLs, skipped {skipped}.",
        "resolved": resolved,
        "skipped": skipped,
        "errors": errors,
    }


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
