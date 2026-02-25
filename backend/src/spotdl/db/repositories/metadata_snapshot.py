"""Metadata snapshot repository for storing metadata from different sources."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select

from spotdl.db.models.metadata_snapshot import MetadataSnapshot
from spotdl.db.repositories.base import BaseRepository


class MetadataSnapshotRepository(BaseRepository[MetadataSnapshot]):
    """Repository for MetadataSnapshot model operations."""

    model = MetadataSnapshot

    async def get_by_song_and_source(
        self,
        song_id: uuid.UUID,
        source: str,
    ) -> MetadataSnapshot | None:
        """Get a metadata snapshot for a specific song and source."""
        query = select(MetadataSnapshot).where(
            and_(
                MetadataSnapshot.song_id == song_id,
                MetadataSnapshot.source == source,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all_for_song(self, song_id: uuid.UUID) -> list[MetadataSnapshot]:
        """Get all metadata snapshots for a song."""
        query = select(MetadataSnapshot).where(MetadataSnapshot.song_id == song_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def upsert(
        self,
        song_id: uuid.UUID,
        source: str,
        raw_response: dict[str, Any] | None,
        snapshot_data: dict[str, Any],
        confidence: float = 1.0,
    ) -> MetadataSnapshot:
        """Create or update a metadata snapshot for a song/source combination."""
        existing = await self.get_by_song_and_source(song_id, source)

        if existing:
            existing.raw_response = raw_response
            existing.snapshot_data = snapshot_data
            existing.confidence = confidence
            existing.fetched_at = datetime.now(UTC)
            await self.session.flush()
            return existing

        snapshot = MetadataSnapshot(
            song_id=song_id,
            source=source,
            raw_response=raw_response,
            snapshot_data=snapshot_data,
            confidence=confidence,
            fetched_at=datetime.now(UTC),
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot
