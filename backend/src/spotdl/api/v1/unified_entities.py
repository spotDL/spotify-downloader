"""Unified entity-first API endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.api.v1.auth import get_current_user_id, get_current_user_id_optional
from spotdl.api.v1.download import require_downloads_enabled
from spotdl.api.v1.validation import validate_uuid
from spotdl.core.services.entity_unified import (
    CapabilityUnsupportedError,
    EntityNotFoundError,
    UnifiedEntityError,
    UnifiedEntityService,
    relation_confidence,
)
from spotdl.db.database import get_db_session
from spotdl.db.models.entity_unified import (
    Entity,
    EntityCanonical,
    EntityFieldProvenance,
    EntityRelation,
    EntitySnapshot,
)

router = APIRouter()


class EntityDiscoverRequest(BaseModel):
    url: str | None = None
    query: str | None = None
    types: list[str] | None = None
    providers: list[str] | None = None
    limit: int = Field(default=20, ge=1, le=100)


class EntityRefs(BaseModel):
    """Resolved internal-UUID cross-references for an entity."""

    album_entity_id: str | None = None
    artist_entity_id: str | None = None


class EntityResponse(BaseModel):
    id: str
    type: str
    name: str
    canonical: dict[str, Any]
    capabilities: dict[str, Any]
    quality_score: float
    last_merged_at: str
    merge_version: int
    refs: EntityRefs = Field(default_factory=EntityRefs)


class RelationResponse(BaseModel):
    id: str
    from_entity_id: str
    to_entity_id: str
    relation_type: str
    match_score: float | None
    confidence: float
    status: str
    discovered_by: str | None
    upvotes: int
    downvotes: int
    net_votes: int
    relation_data: dict[str, Any]
    target: EntityResponse | None = None


class DiscoverResponse(BaseModel):
    query: str
    query_type: str
    entities: list[EntityResponse]
    total: int
    entities_created: int
    top_relations: dict[str, list[RelationResponse]]


class SnapshotResponse(BaseModel):
    id: str
    provider_id: str
    provider_entity_id: str | None
    provider_url: str | None
    normalized_payload: dict[str, Any]
    raw_payload: dict[str, Any]
    confidence: float
    fetched_at: str
    expires_at: str | None
    capabilities: dict[str, Any]


class ProvenanceResponse(BaseModel):
    id: str
    field_name: str
    snapshot_id: str
    score: float
    selected: bool
    reason: str | None


class SnapshotsResponse(BaseModel):
    entity_id: str
    snapshots: list[SnapshotResponse]
    provenance: list[ProvenanceResponse]


class RefreshRequest(BaseModel):
    providers: list[str] | None = None


class RefreshResponse(BaseModel):
    entity: EntityResponse
    refreshed_snapshots: int
    failed_providers: list[dict[str, str]]


class DiscoverRelationsRequest(BaseModel):
    target_providers: list[str] | None = None
    limit: int = Field(default=6, ge=1, le=50)


class RelationsResponse(BaseModel):
    entity_id: str
    relations: list[RelationResponse]
    total: int


class RelationVoteRequest(BaseModel):
    vote: str = Field(description="One of: up, down, remove")


class RelationVoteResponse(BaseModel):
    relation_id: str
    upvotes: int
    downvotes: int
    net_votes: int
    confidence: float
    user_vote: str | None


class DownloadEntityRequest(BaseModel):
    relation_id: str | None = None
    provider_id: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class DownloadEntityResponse(BaseModel):
    download_id: str
    status: str
    provider_id: str
    used_provider_hook: bool
    fallback_used: bool


class CreateRelationRequest(BaseModel):
    to_entity_id: str | None = None
    to_url: str | None = None
    relation_type: str = "audio_match"
    match_score: float | None = None


async def _batch_resolve_entity_refs(
    entities: list[Entity],
    db: AsyncSession,
) -> dict[str, EntityRefs]:
    """Resolve cross-entity UUID references for a list of entities in ONE query.

    Returns a mapping of entity.id (str) -> EntityRefs.  Only tracks and albums
    are enriched; artists and playlists get empty refs.
    """
    from sqlalchemy import or_, select

    enrichable_ids = [e.id for e in entities if e.entity_type in {"track", "album"}]
    refs: dict[str, EntityRefs] = {str(e.id): EntityRefs() for e in entities}

    if not enrichable_ids:
        return refs

    result = await db.execute(
        select(EntityRelation).where(
            EntityRelation.to_entity_id.in_(enrichable_ids),
            or_(
                EntityRelation.relation_type == "contains",
                EntityRelation.relation_type == "performed",
            ),
        )
    )
    relations: list[EntityRelation] = list(result.scalars().all())

    entity_type_map = {str(e.id): e.entity_type for e in entities}

    for rel in relations:
        key = str(rel.to_entity_id)
        entity_type = entity_type_map.get(key)
        entry = refs.get(key)
        if entry is None or entity_type is None:
            continue
        if entity_type == "track":
            if rel.relation_type == "contains" and entry.album_entity_id is None:
                entry.album_entity_id = str(rel.from_entity_id)
            elif rel.relation_type == "performed" and entry.artist_entity_id is None:
                entry.artist_entity_id = str(rel.from_entity_id)
        elif entity_type == "album":
            if rel.relation_type == "performed" and entry.artist_entity_id is None:
                entry.artist_entity_id = str(rel.from_entity_id)

    return refs


def _entity_to_response(
    entity: Entity,
    refs: EntityRefs | None = None,
    ec: EntityCanonical | None = None,
) -> EntityResponse:
    # ec may be passed explicitly, or loaded from entity.canonical_data relationship
    if ec is None:
        ec = entity.canonical_data
    return EntityResponse(
        id=str(entity.id),
        type=entity.entity_type,
        name=ec.name if ec else "Unknown",
        canonical=ec.canonical if ec else {},
        capabilities=ec.capabilities if ec else {},
        quality_score=float(ec.quality_score) if ec else 0.0,
        last_merged_at=entity.updated_at.isoformat(),
        merge_version=int(ec.merge_version) if ec else 1,
        refs=refs or EntityRefs(),
    )


async def _entity_to_enriched_response(entity: Entity, db: AsyncSession) -> EntityResponse:
    """Single-entity convenience wrapper — uses a one-entity batch internally."""
    refs_map = await _batch_resolve_entity_refs([entity], db)
    ec = await db.execute(select(EntityCanonical).where(EntityCanonical.entity_id == entity.id))
    ec_row = ec.scalar_one_or_none()
    return _entity_to_response(entity, refs_map.get(str(entity.id)), ec=ec_row)


def _snapshot_to_response(snapshot: EntitySnapshot) -> SnapshotResponse:
    return SnapshotResponse(
        id=str(snapshot.id),
        provider_id=snapshot.provider_id,
        provider_entity_id=snapshot.provider_entity_id,
        provider_url=snapshot.provider_url,
        normalized_payload=snapshot.normalized_payload or {},
        raw_payload=snapshot.raw_payload or {},
        confidence=float(snapshot.confidence or 0.0),
        fetched_at=snapshot.fetched_at.isoformat(),
        expires_at=snapshot.expires_at.isoformat() if snapshot.expires_at else None,
        capabilities=snapshot.capabilities or {},
    )


def _provenance_to_response(row: EntityFieldProvenance) -> ProvenanceResponse:
    return ProvenanceResponse(
        id=str(row.id),
        field_name=row.field_name,
        snapshot_id=str(row.snapshot_id),
        score=float(row.score or 0.0),
        selected=bool(row.selected),
        reason=row.reason,
    )


async def _relation_to_response(
    relation: EntityRelation,
    db: AsyncSession,
    *,
    ec_cache: dict[str, EntityCanonical] | None = None,
) -> RelationResponse:
    target = None
    try:
        target_id = relation.to_entity_id
        entity_result = await db.execute(select(Entity).where(Entity.id == target_id))
        target_entity = entity_result.scalar_one_or_none()
        if target_entity is not None:
            ec = None
            if ec_cache is not None:
                ec = ec_cache.get(str(target_id))
            if ec is None:
                ec_result = await db.execute(
                    select(EntityCanonical).where(EntityCanonical.entity_id == target_id)
                )
                ec = ec_result.scalar_one_or_none()
            target = _entity_to_response(target_entity, ec=ec)
    except Exception:
        target = None

    return RelationResponse(
        id=str(relation.id),
        from_entity_id=str(relation.from_entity_id),
        to_entity_id=str(relation.to_entity_id),
        relation_type=relation.relation_type,
        match_score=float(relation.match_score) if relation.match_score is not None else None,
        confidence=float(relation_confidence(relation)),
        status=relation.status,
        discovered_by=relation.discovered_by,
        upvotes=int(relation.upvotes or 0),
        downvotes=int(relation.downvotes or 0),
        net_votes=int((relation.upvotes or 0) - (relation.downvotes or 0)),
        relation_data=relation.relation_data or {},
        target=target,
    )


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, IntegrityError):
        return HTTPException(
            status_code=409,
            detail="Entity state changed concurrently. Please retry.",
        )
    if isinstance(exc, EntityNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, CapabilityUnsupportedError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, UnifiedEntityError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=f"Unexpected unified entity error: {exc}")


@router.post("/entities/discover", response_model=DiscoverResponse)
async def discover_entities(
    request: EntityDiscoverRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> DiscoverResponse:
    if not request.url and not request.query:
        raise HTTPException(status_code=400, detail="Either 'url' or 'query' is required.")
    if request.url and request.query:
        raise HTTPException(status_code=400, detail="Provide either 'url' or 'query', not both.")

    service = UnifiedEntityService(db)
    value = request.url or request.query or ""
    try:
        result = await service.discover(
            value=value,
            entity_types=request.types,
            provider_ids=request.providers,
            limit=request.limit,
        )
        # Batch-load EntityCanonical for all entities
        entity_ids = [e.id for e in result.entities]
        ec_map: dict[str, EntityCanonical] = {}
        if entity_ids:
            ec_result = await db.execute(
                select(EntityCanonical).where(EntityCanonical.entity_id.in_(entity_ids))
            )
            for ec_row in ec_result.scalars().all():
                ec_map[str(ec_row.entity_id)] = ec_row

        # Batch-load relations for all entities
        top_relations: dict[str, list[RelationResponse]] = {}
        if entity_ids:
            from sqlalchemy import desc
            rel_result = await db.execute(
                select(EntityRelation)
                .where(
                    EntityRelation.from_entity_id.in_(entity_ids),
                    EntityRelation.relation_type == "audio_match",
                )
                .order_by(
                    EntityRelation.from_entity_id,
                    desc(EntityRelation.match_score),
                )
            )
            all_relations = list(rel_result.scalars().all())

            # Group by from_entity_id and take top 5
            from collections import defaultdict
            relations_by_entity: dict[str, list[EntityRelation]] = defaultdict(list)
            for rel in all_relations:
                key = str(rel.from_entity_id)
                if len(relations_by_entity[key]) < 5:
                    relations_by_entity[key].append(rel)

            # Batch-load canonical data for all relation targets
            target_ids = {rel.to_entity_id for rels in relations_by_entity.values() for rel in rels}
            if target_ids:
                target_ec_result = await db.execute(
                    select(EntityCanonical).where(EntityCanonical.entity_id.in_(target_ids))
                )
                for ec_row in target_ec_result.scalars().all():
                    ec_map[str(ec_row.entity_id)] = ec_row

            for eid_str, rels in relations_by_entity.items():
                top_relations[eid_str] = [
                    await _relation_to_response(rel, db, ec_cache=ec_map) for rel in rels
                ]

        # Ensure all entities have an entry
        for entity in result.entities:
            if str(entity.id) not in top_relations:
                top_relations[str(entity.id)] = []

        # Resolve all cross-entity UUIDs in a SINGLE batch query.
        refs_map = await _batch_resolve_entity_refs(result.entities, db)

        return DiscoverResponse(
            query=value,
            query_type="url" if request.url else "text",
            entities=[
                _entity_to_response(
                    entity,
                    refs_map.get(str(entity.id)),
                    ec=ec_map.get(str(entity.id)),
                )
                for entity in result.entities
            ],
            total=len(result.entities),
            entities_created=result.created_entities,
            top_relations=top_relations,
        )
    except Exception as exc:
        raise _translate_error(exc) from exc
    finally:
        await service.close()


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: Annotated[str, Path(description="Canonical entity UUID")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> EntityResponse:
    entity_uuid = validate_uuid(entity_id, "entity ID")
    service = UnifiedEntityService(db)
    try:
        entity = await service.get_entity(entity_uuid)
        return await _entity_to_enriched_response(entity, db)
    except Exception as exc:
        raise _translate_error(exc) from exc
    finally:
        await service.close()


@router.get("/entities/{entity_id}/snapshots", response_model=SnapshotsResponse)
async def get_entity_snapshots(
    entity_id: Annotated[str, Path(description="Canonical entity UUID")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SnapshotsResponse:
    entity_uuid = validate_uuid(entity_id, "entity ID")
    service = UnifiedEntityService(db)
    try:
        snapshots, provenance = await service.get_entity_snapshots(entity_uuid)
        return SnapshotsResponse(
            entity_id=entity_id,
            snapshots=[_snapshot_to_response(snapshot) for snapshot in snapshots],
            provenance=[_provenance_to_response(row) for row in provenance],
        )
    except Exception as exc:
        raise _translate_error(exc) from exc
    finally:
        await service.close()


@router.post("/entities/{entity_id}/refresh", response_model=RefreshResponse)
async def refresh_entity(
    entity_id: Annotated[str, Path(description="Canonical entity UUID")],
    request: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[uuid.UUID | None, Depends(get_current_user_id_optional)],
) -> RefreshResponse:
    from spotdl.db.repositories.refresh_cooldown import RefreshCooldownRepository

    entity_uuid = validate_uuid(entity_id, "entity ID")

    # Check cooldown
    cooldown_repo = RefreshCooldownRepository(db)
    entity_obj = await db.execute(
        select(Entity).where(Entity.id == entity_uuid)
    )
    entity_row = entity_obj.scalar_one_or_none()
    if entity_row is None:
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

    on_cooldown, remaining = await cooldown_repo.is_on_cooldown(
        entity_row.entity_type, entity_uuid, user_id
    )
    if on_cooldown:
        raise HTTPException(
            status_code=429,
            detail=f"Refresh on cooldown. Try again in {remaining} seconds.",
        )

    service = UnifiedEntityService(db)
    try:
        result = await service.refresh_entity(entity_uuid, request.providers)

        # Record the refresh for cooldown tracking
        await cooldown_repo.record_refresh(entity_row.entity_type, entity_uuid, user_id)

        return RefreshResponse(
            entity=_entity_to_response(result.entity),
            refreshed_snapshots=result.refreshed_snapshots,
            failed_providers=result.failed_providers,
        )
    except Exception as exc:
        raise _translate_error(exc) from exc
    finally:
        await service.close()


@router.post("/entities/{entity_id}/relations:discover", response_model=RelationsResponse)
async def discover_entity_relations(
    entity_id: Annotated[str, Path(description="Canonical entity UUID")],
    request: DiscoverRelationsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> RelationsResponse:
    entity_uuid = validate_uuid(entity_id, "entity ID")
    service = UnifiedEntityService(db)
    try:
        relations = await service.discover_relations(
            entity_uuid,
            target_provider_ids=request.target_providers,
            limit=request.limit,
        )
        return RelationsResponse(
            entity_id=entity_id,
            relations=[await _relation_to_response(relation, db) for relation in relations],
            total=len(relations),
        )
    except Exception as exc:
        raise _translate_error(exc) from exc
    finally:
        await service.close()


@router.get("/entities/{entity_id}/relations", response_model=RelationsResponse)
async def list_entity_relations(
    entity_id: Annotated[str, Path(description="Canonical entity UUID")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    relation_type: str = "audio_match",
) -> RelationsResponse:
    entity_uuid = validate_uuid(entity_id, "entity ID")
    service = UnifiedEntityService(db)
    try:
        relations = await service.list_relations(entity_uuid, relation_type=relation_type)
        return RelationsResponse(
            entity_id=entity_id,
            relations=[await _relation_to_response(relation, db) for relation in relations],
            total=len(relations),
        )
    except Exception as exc:
        raise _translate_error(exc) from exc
    finally:
        await service.close()


@router.post("/relations/{relation_id}/vote", response_model=RelationVoteResponse)
async def vote_relation(
    relation_id: Annotated[str, Path(description="Relation UUID")],
    request: RelationVoteRequest,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> RelationVoteResponse:
    relation_uuid = validate_uuid(relation_id, "relation ID")
    service = UnifiedEntityService(db)
    normalized_vote = request.vote.strip().lower()
    vote_type = None if normalized_vote in {"remove", "none", ""} else normalized_vote
    try:
        relation = await service.vote_relation(relation_uuid, user_id, vote_type)
        return RelationVoteResponse(
            relation_id=relation_id,
            upvotes=int(relation.upvotes or 0),
            downvotes=int(relation.downvotes or 0),
            net_votes=int((relation.upvotes or 0) - (relation.downvotes or 0)),
            confidence=float(relation_confidence(relation)),
            user_vote=vote_type,
        )
    except Exception as exc:
        raise _translate_error(exc) from exc
    finally:
        await service.close()


@router.get("/relations/{relation_id}", response_model=RelationResponse)
async def get_relation(
    relation_id: Annotated[str, Path(description="Relation UUID")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> RelationResponse:
    relation_uuid = validate_uuid(relation_id, "relation ID")
    service = UnifiedEntityService(db)
    try:
        relation = await service.get_relation(relation_uuid)
        return await _relation_to_response(relation, db)
    except Exception as exc:
        raise _translate_error(exc) from exc
    finally:
        await service.close()


@router.get("/relations/{relation_id}/vote", response_model=RelationVoteResponse)
async def get_relation_vote_summary(
    relation_id: Annotated[str, Path(description="Relation UUID")],
    user_id: Annotated[uuid.UUID | None, Depends(get_current_user_id_optional)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> RelationVoteResponse:
    relation_uuid = validate_uuid(relation_id, "relation ID")
    service = UnifiedEntityService(db)
    try:
        relation = await service.get_relation(relation_uuid)
        user_vote = await service.get_user_relation_vote(relation_uuid, user_id)
        return RelationVoteResponse(
            relation_id=relation_id,
            upvotes=int(relation.upvotes or 0),
            downvotes=int(relation.downvotes or 0),
            net_votes=int((relation.upvotes or 0) - (relation.downvotes or 0)),
            confidence=float(relation_confidence(relation)),
            user_vote=user_vote,
        )
    except Exception as exc:
        raise _translate_error(exc) from exc
    finally:
        await service.close()


@router.post("/entities/{entity_id}/relations", response_model=RelationResponse)
async def create_relation(
    entity_id: Annotated[str, Path(description="Canonical source entity UUID")],
    request: CreateRelationRequest,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> RelationResponse:
    source_entity_uuid = validate_uuid(entity_id, "entity ID")
    to_entity_uuid = (
        validate_uuid(request.to_entity_id, "target entity ID") if request.to_entity_id else None
    )
    if not to_entity_uuid and not request.to_url:
        raise HTTPException(status_code=400, detail="Provide either to_entity_id or to_url.")

    service = UnifiedEntityService(db)
    try:
        relation = await service.create_relation(
            source_entity_uuid,
            to_entity_id=to_entity_uuid,
            to_url=request.to_url,
            relation_type=request.relation_type,
            match_score=request.match_score,
            discovered_by=str(user_id),
        )
        return await _relation_to_response(relation, db)
    except Exception as exc:
        raise _translate_error(exc) from exc
    finally:
        await service.close()


@router.post("/entities/{entity_id}/download", response_model=DownloadEntityResponse)
async def download_entity(
    entity_id: Annotated[str, Path(description="Canonical entity UUID")],
    request: DownloadEntityRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: None = Depends(require_downloads_enabled),
) -> DownloadEntityResponse:
    entity_uuid = validate_uuid(entity_id, "entity ID")
    relation_uuid = (
        validate_uuid(request.relation_id, "relation ID") if request.relation_id else None
    )
    service = UnifiedEntityService(db)
    try:
        result = await service.download_entity(
            entity_uuid,
            relation_id=relation_uuid,
            provider_id=request.provider_id,
            settings=request.settings,
        )
        return DownloadEntityResponse(**result)
    except Exception as exc:
        raise _translate_error(exc) from exc
    finally:
        await service.close()
