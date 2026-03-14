"""Relation and voting logic for unified entities."""

from __future__ import annotations

import logging
import math
import uuid
from typing import Any

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.db.models.entity_unified import (
    EntityRelation,
    RelationVote,
)

logger = logging.getLogger(__name__)


class RelationService:
    """Handles entity relation discovery, creation, listing, and voting."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def discover_relations(
        self,
        entity_id: uuid.UUID,
        *,
        target_provider_ids: list[str] | None = None,
        limit: int = 6,
        # Injected dependencies from the facade
        get_entity: Any = None,
        get_snapshots: Any = None,
        get_entity_canonical: Any = None,
        song_from_entity: Any = None,
        bundle_from_result: Any = None,
        upsert_entity_snapshot: Any = None,
        create_or_update_relation: Any = None,
        match_service_factory: Any = None,
    ) -> list[EntityRelation]:
        from spotdl.core.services.discovery import TARGET_ID_TO_PLATFORM

        entity = await get_entity(entity_id)
        if entity.entity_type != "track":
            return []

        snapshots = await get_snapshots(entity.id)
        ec = await get_entity_canonical(entity.id)
        song = song_from_entity(entity, snapshots, ec)

        target_provider_ids = target_provider_ids or [
            "youtube_music",
            "youtube",
            "soundcloud",
            "bandcamp",
        ]
        target_platforms = [
            TARGET_ID_TO_PLATFORM[provider_id]
            for provider_id in target_provider_ids
            if provider_id in TARGET_ID_TO_PLATFORM
        ]

        match_service = match_service_factory()
        matches = await match_service.find_matches(
            song,
            target_platforms=target_platforms or None,
            limit=limit,
        )

        relations: list[EntityRelation] = []
        for match in matches:
            bundle = bundle_from_result(match.target_result)
            target_entity, _ = await upsert_entity_snapshot(bundle)
            relation = await create_or_update_relation(
                entity.id,
                target_entity.id,
                "audio_match",
                float(match.score),
                bundle.provider_id,
                relation_data={
                    "confidence": match.confidence,
                    "provider_id": bundle.provider_id,
                    "target_url": bundle.provider_url,
                },
            )
            if relation is not None:
                relations.append(relation)

        await self._db.flush()
        return relations

    async def list_relations(
        self,
        entity_id: uuid.UUID,
        relation_type: str = "audio_match",
        limit: int = 50,
    ) -> list[EntityRelation]:
        query = (
            select(EntityRelation)
            .where(
                and_(
                    EntityRelation.from_entity_id == entity_id,
                    EntityRelation.relation_type == relation_type,
                )
            )
            .order_by(
                desc(EntityRelation.match_score),
                desc(EntityRelation.upvotes - EntityRelation.downvotes),
                desc(EntityRelation.updated_at),
            )
            .limit(limit)
        )
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def get_relation(self, relation_id: uuid.UUID) -> EntityRelation:
        from spotdl.core.services.entity_unified import EntityNotFoundError

        query = select(EntityRelation).where(EntityRelation.id == relation_id)
        result = await self._db.execute(query)
        relation = result.scalar_one_or_none()
        if relation is None:
            raise EntityNotFoundError(f"Relation not found: {relation_id}")
        return relation

    async def get_user_relation_vote(
        self,
        relation_id: uuid.UUID,
        user_id: uuid.UUID | None,
    ) -> str | None:
        if user_id is None:
            return None
        query = select(RelationVote).where(
            and_(
                RelationVote.relation_id == relation_id,
                RelationVote.user_id == user_id,
            )
        )
        result = await self._db.execute(query)
        vote = result.scalar_one_or_none()
        return vote.vote_type if vote is not None else None

    async def create_relation(
        self,
        from_entity_id: uuid.UUID,
        *,
        to_entity_id: uuid.UUID | None = None,
        to_url: str | None = None,
        relation_type: str = "audio_match",
        match_score: float | None = None,
        discovered_by: str = "user",
        # Injected dependencies from the facade
        get_entity: Any = None,
        discover_from_url: Any = None,
        create_or_update_relation: Any = None,
    ) -> EntityRelation:
        from spotdl.core.services.entity_unified import (
            CapabilityUnsupportedError,
            UnifiedEntityError,
        )

        from_entity = await get_entity(from_entity_id)
        if from_entity.entity_type != "track":
            raise CapabilityUnsupportedError(
                "Manual relation creation is supported only for track entities."
            )

        resolved_target_id = to_entity_id
        if resolved_target_id is None and to_url:
            discovered = await discover_from_url(url=to_url)
            track_entities = [
                entity for entity in discovered.entities if entity.entity_type == "track"
            ]
            if not track_entities:
                raise UnifiedEntityError("Unable to resolve target URL into a track entity.")
            resolved_target_id = track_entities[0].id

        if resolved_target_id is None:
            raise UnifiedEntityError("Provide either to_entity_id or to_url.")

        _ = await get_entity(resolved_target_id)
        relation = await create_or_update_relation(
            from_entity_id=from_entity_id,
            to_entity_id=resolved_target_id,
            relation_type=relation_type,
            match_score=match_score,
            discovered_by=discovered_by,
            relation_data={"manual": True},
        )
        if relation is None:
            raise UnifiedEntityError("Cannot create a relation between the same entity.")
        return relation

    async def vote_relation(
        self,
        relation_id: uuid.UUID,
        user_id: uuid.UUID,
        vote_type: str | None,
    ) -> EntityRelation:
        from spotdl.core.services.entity_unified import (
            EntityNotFoundError,
            UnifiedEntityError,
        )

        relation_query = select(EntityRelation).where(EntityRelation.id == relation_id)
        relation_result = await self._db.execute(relation_query)
        relation = relation_result.scalar_one_or_none()
        if relation is None:
            raise EntityNotFoundError(f"Relation not found: {relation_id}")

        vote_query = select(RelationVote).where(
            and_(
                RelationVote.relation_id == relation_id,
                RelationVote.user_id == user_id,
            )
        )
        vote_result = await self._db.execute(vote_query)
        vote = vote_result.scalar_one_or_none()

        normalized_vote = (vote_type or "").strip().lower() or None
        if normalized_vote not in {"up", "down", None}:
            raise UnifiedEntityError("Invalid vote type. Expected 'up', 'down', or null/remove.")

        if normalized_vote is None:
            if vote is not None:
                await self._db.delete(vote)
        else:
            if vote is None:
                try:
                    async with self._db.begin_nested():
                        vote = RelationVote(
                            relation_id=relation_id,
                            user_id=user_id,
                            vote_type=normalized_vote,
                        )
                        self._db.add(vote)
                        await self._db.flush()
                except IntegrityError:
                    vote_result = await self._db.execute(vote_query)
                    vote = vote_result.scalar_one_or_none()
                    if vote is None:
                        raise UnifiedEntityError(
                            "Failed to create or load relation vote after concurrent insert."
                        ) from None
                    vote.vote_type = normalized_vote
            else:
                vote.vote_type = normalized_vote

        await self._db.flush()

        # Atomic vote count update using correlated subqueries
        up_subq = (
            select(func.count())
            .where(RelationVote.relation_id == relation_id, RelationVote.vote_type == "up")
            .correlate_except(RelationVote)
            .scalar_subquery()
        )
        down_subq = (
            select(func.count())
            .where(RelationVote.relation_id == relation_id, RelationVote.vote_type == "down")
            .correlate_except(RelationVote)
            .scalar_subquery()
        )
        await self._db.execute(
            update(EntityRelation)
            .where(EntityRelation.id == relation_id)
            .values(upvotes=up_subq, downvotes=down_subq)
        )
        await self._db.flush()

        # Refresh the relation object to get the updated counts
        await self._db.refresh(relation)
        return relation


def relation_confidence(relation: EntityRelation) -> float:
    """
    Wilson-score lower bound mapped to [0, 1], blended with match score.
    """
    upvotes = relation.upvotes or 0
    downvotes = relation.downvotes or 0
    n = upvotes + downvotes
    wilson = 0.0
    if n > 0:
        p = upvotes / n
        z = 1.96
        denominator = 1 + z * z / n
        centre = p + z * z / (2 * n)
        deviation = math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
        wilson = max(0.0, min(1.0, (centre - z * deviation) / denominator))
    score_component = max(0.0, min(1.0, float((relation.match_score or 0.0) / 100.0)))
    if n == 0:
        return score_component
    return (0.65 * wilson) + (0.35 * score_component)
