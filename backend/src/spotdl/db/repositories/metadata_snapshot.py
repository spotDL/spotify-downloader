"""Metadata snapshot repository for multi-source metadata access."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_

from spotdl.db.models.metadata_snapshot import MetadataSnapshot
from spotdl.db.repositories.base import BaseRepository


class MetadataSnapshotRepository(BaseRepository[MetadataSnapshot]):
    """Repository for MetadataSnapshot model operations."""

    model = MetadataSnapshot

    async def get_for_song(
        self,
        song_id: uuid.UUID,
        *,
        order_by_confidence: bool = True,
    ) -> list[MetadataSnapshot]:
        """
        Get all metadata snapshots for a song.

        Args:
            song_id: The song's UUID
            order_by_confidence: If True, order by confidence descending

        Returns:
            List of MetadataSnapshot objects
        """
        query = select(MetadataSnapshot).where(MetadataSnapshot.song_id == song_id)

        if order_by_confidence:
            query = query.order_by(MetadataSnapshot.confidence.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_source(
        self,
        song_id: uuid.UUID,
        source: str,
    ) -> MetadataSnapshot | None:
        """
        Get a specific source's snapshot for a song.

        Args:
            song_id: The song's UUID
            source: Source identifier (e.g., "musicbrainz", "discogs")

        Returns:
            MetadataSnapshot if found, None otherwise
        """
        query = select(MetadataSnapshot).where(
            and_(
                MetadataSnapshot.song_id == song_id,
                MetadataSnapshot.source == source,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        song_id: uuid.UUID,
        source: str,
        snapshot_data: dict[str, Any],
        raw_response: dict[str, Any] | None = None,
        confidence: float = 1.0,
    ) -> MetadataSnapshot:
        """
        Create or update a metadata snapshot.

        If a snapshot for this song/source combination exists, it will be updated.
        Otherwise, a new snapshot will be created.

        Args:
            song_id: The song's UUID
            source: Source identifier
            snapshot_data: Normalized metadata fields
            raw_response: Complete raw API response (optional)
            confidence: Confidence score (0.0-1.0)

        Returns:
            The created or updated MetadataSnapshot
        """
        existing = await self.get_by_source(song_id, source)

        if existing:
            # Update existing snapshot
            existing.snapshot_data = snapshot_data
            existing.raw_response = raw_response
            existing.confidence = confidence
            existing.fetched_at = datetime.now(timezone.utc)
            await self.session.flush()
            return existing

        # Create new snapshot
        snapshot = MetadataSnapshot(
            song_id=song_id,
            source=source,
            snapshot_data=snapshot_data,
            raw_response=raw_response,
            confidence=confidence,
            fetched_at=datetime.now(timezone.utc),
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def delete_for_song(self, song_id: uuid.UUID) -> int:
        """
        Delete all snapshots for a song.

        Args:
            song_id: The song's UUID

        Returns:
            Number of snapshots deleted
        """
        snapshots = await self.get_for_song(song_id)
        for snapshot in snapshots:
            await self.session.delete(snapshot)
        await self.session.flush()
        return len(snapshots)

    async def get_sources_for_song(self, song_id: uuid.UUID) -> list[str]:
        """
        Get list of available sources for a song.

        Args:
            song_id: The song's UUID

        Returns:
            List of source identifiers
        """
        query = (
            select(MetadataSnapshot.source)
            .where(MetadataSnapshot.song_id == song_id)
            .distinct()
        )
        result = await self.session.execute(query)
        return [row[0] for row in result.all()]
