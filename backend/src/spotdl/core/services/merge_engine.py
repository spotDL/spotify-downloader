"""Field-level canonical merge engine with confidence, priority, recency, and validation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.db.models.entity_unified import (
    Entity,
    EntityCanonical,
    EntityFieldProvenance,
    EntitySnapshot,
)

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_PRIORITIES: dict[str, float] = {
    "spotify": 1.0,
    "apple_music": 0.95,
    "deezer": 0.92,
    "tidal": 0.9,
    "youtube_music": 0.88,
    "youtube": 0.84,
    "soundcloud": 0.82,
    "bandcamp": 0.8,
    "musicbrainz": 0.78,
    "discogs": 0.76,
    "open_graph": 0.45,
}


def _now_utc() -> datetime:
    return datetime.now(UTC)


class MergeEngine:
    """Field-level canonical merge with confidence, priority, recency, and validation."""

    def __init__(self, provider_priorities: dict[str, float] | None = None) -> None:
        self._priorities = provider_priorities or DEFAULT_PROVIDER_PRIORITIES

    def _priority(self, provider_id: str) -> float:
        return self._priorities.get(provider_id, 0.6)

    def _recency_factor(self, fetched_at: datetime) -> float:
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)
        else:
            fetched_at = fetched_at.astimezone(UTC)

        age_seconds = max((_now_utc() - fetched_at).total_seconds(), 0.0)
        age_days = age_seconds / 86400.0
        if age_days <= 1:
            return 1.0
        if age_days >= 180:
            return 0.5
        return max(0.5, 1.0 - (age_days / 360.0))

    def _field_validator_score(self, field_name: str, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, str):
            clean = value.strip()
            if not clean:
                return 0.0
            if field_name in {"url", "cover_url"}:
                return 1.0 if clean.startswith("http") else 0.1
            if field_name in {"name", "artist"}:
                return 1.0 if len(clean) >= 2 else 0.4
            return 1.0
        if isinstance(value, (int, float)):
            if field_name == "duration":
                return 1.0 if 10 <= int(value) <= 7200 else 0.35
            return 1.0
        if isinstance(value, list):
            return 0.0 if not value else 1.0
        if isinstance(value, dict):
            return 0.0 if not value else 1.0
        return 1.0

    def _score(self, snapshot: EntitySnapshot, field_name: str, value: Any) -> float:
        return (
            self._priority(snapshot.provider_id)
            * max(snapshot.confidence, 0.01)
            * self._recency_factor(snapshot.fetched_at)
            * self._field_validator_score(field_name, value)
        )

    async def merge(self, session: AsyncSession, entity: Entity) -> EntityCanonical:
        """Merge snapshots into EntityCanonical (create or update)."""
        snapshots_query = (
            select(EntitySnapshot)
            .where(EntitySnapshot.entity_id == entity.id)
            .order_by(desc(EntitySnapshot.fetched_at))
        )
        snapshots_result = await session.execute(snapshots_query)
        snapshots = list(snapshots_result.scalars().all())

        # Get or create EntityCanonical
        canonical_query = select(EntityCanonical).where(EntityCanonical.entity_id == entity.id)
        canonical_result = await session.execute(canonical_query)
        ec = canonical_result.scalar_one_or_none()
        if ec is None:
            ec = EntityCanonical(entity_id=entity.id)
            session.add(ec)

        if not snapshots:
            ec.canonical = ec.canonical or {}
            ec.name = str(ec.canonical.get("name") or ec.name or "Unknown")
            ec.merge_version = func.coalesce(EntityCanonical.merge_version, 0) + 1
            ec.quality_score = 0.0
            return ec

        all_fields: set[str] = set()
        for snapshot in snapshots:
            all_fields.update(snapshot.normalized_payload.keys())

        canonical: dict[str, Any] = {}
        provenance_rows: list[EntityFieldProvenance] = []
        selected_scores: list[float] = []

        for field_name in sorted(all_fields):
            candidates: list[tuple[EntitySnapshot, Any, float]] = []
            for snapshot in snapshots:
                if field_name not in snapshot.normalized_payload:
                    continue
                value = snapshot.normalized_payload.get(field_name)
                score = self._score(snapshot, field_name, value)
                if score <= 0:
                    continue
                candidates.append((snapshot, value, score))

            if not candidates:
                continue

            candidates.sort(key=lambda item: item[2], reverse=True)
            best_snapshot, best_value, best_score = candidates[0]
            canonical[field_name] = best_value
            selected_scores.append(best_score)

            for snapshot, _value, score in candidates:
                provenance_rows.append(
                    EntityFieldProvenance(
                        entity_id=entity.id,
                        field_name=field_name,
                        snapshot_id=snapshot.id,
                        score=score,
                        selected=snapshot.id == best_snapshot.id,
                        reason=(
                            f"priority={self._priority(snapshot.provider_id):.3f};"
                            f"confidence={snapshot.confidence:.3f};"
                            f"recency={self._recency_factor(snapshot.fetched_at):.3f}"
                        ),
                    )
                )

        await session.execute(
            delete(EntityFieldProvenance).where(EntityFieldProvenance.entity_id == entity.id)
        )
        if provenance_rows:
            session.add_all(provenance_rows)

        ec.canonical = canonical
        ec.name = str(canonical.get("name") or ec.name or "Unknown")
        ec.quality_score = (
            float(sum(selected_scores) / len(selected_scores)) if selected_scores else 0.0
        )
        ec.merge_version = func.coalesce(EntityCanonical.merge_version, 0) + 1
        return ec
