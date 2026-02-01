"""Lyrics repository for multi-source lyrics access."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_

from spotdl.db.models.lyrics import Lyrics
from spotdl.db.repositories.base import BaseRepository


class LyricsRepository(BaseRepository[Lyrics]):
    """Repository for Lyrics model operations."""

    model = Lyrics

    async def get_all_for_song(
        self,
        song_id: uuid.UUID,
        *,
        order_by_quality: bool = True,
    ) -> list[Lyrics]:
        """
        Get all lyrics entries for a song from all sources.

        Args:
            song_id: The song's UUID
            order_by_quality: If True, order by quality_score descending

        Returns:
            List of Lyrics objects from all sources
        """
        query = select(Lyrics).where(Lyrics.song_id == song_id)

        if order_by_quality:
            # Order by: synced lyrics first, then quality score, then freshness
            query = query.order_by(
                # Synced lyrics are preferred
                Lyrics.lyrics_synced.isnot(None).desc(),
                # Then by quality score
                Lyrics.quality_score.desc().nullslast(),
                # Then by freshness
                Lyrics.fetched_at.desc(),
            )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_source(
        self,
        song_id: uuid.UUID,
        source: str,
    ) -> Lyrics | None:
        """
        Get lyrics from a specific source for a song.

        Args:
            song_id: The song's UUID
            source: Source identifier (e.g., "genius", "musixmatch", "lrclib")

        Returns:
            Lyrics if found, None otherwise
        """
        query = select(Lyrics).where(
            and_(
                Lyrics.song_id == song_id,
                Lyrics.source == source,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_best_for_song(self, song_id: uuid.UUID) -> Lyrics | None:
        """
        Get the best quality lyrics for a song.

        Prioritizes synced lyrics, then verified, then highest quality score.

        Args:
            song_id: The song's UUID

        Returns:
            Best Lyrics if found, None otherwise
        """
        all_lyrics = await self.get_all_for_song(song_id, order_by_quality=True)
        return all_lyrics[0] if all_lyrics else None

    async def upsert(
        self,
        song_id: uuid.UUID,
        source: str,
        lyrics_text: str,
        lyrics_synced: str | None = None,
        quality_score: float | None = None,
        is_verified: bool | None = None,
        line_count: int | None = None,
        content_hash: str | None = None,
        provider_track_id: str | None = None,
        has_translations: bool | None = None,
        language: str | None = None,
    ) -> Lyrics:
        """
        Create or update lyrics for a song/source combination.

        Args:
            song_id: The song's UUID
            source: Source identifier
            lyrics_text: Plain text lyrics
            lyrics_synced: LRC format synced lyrics (optional)
            quality_score: Quality score 0-1 (optional)
            is_verified: Whether lyrics are verified (optional)
            line_count: Number of lines (optional)
            content_hash: SHA256 hash for deduplication (optional)
            provider_track_id: Track ID on the provider (optional)
            has_translations: Whether translations available (optional)
            language: Detected language (optional)

        Returns:
            The created or updated Lyrics
        """
        existing = await self.get_by_source(song_id, source)

        if existing:
            # Update existing lyrics
            existing.lyrics_text = lyrics_text
            existing.lyrics_synced = lyrics_synced
            existing.quality_score = quality_score
            existing.is_verified = is_verified
            existing.line_count = line_count
            existing.content_hash = content_hash
            existing.provider_track_id = provider_track_id
            existing.has_translations = has_translations
            existing.language = language
            existing.fetched_at = datetime.now(timezone.utc)
            await self.session.flush()
            return existing

        # Create new lyrics entry
        lyrics = Lyrics(
            song_id=song_id,
            source=source,
            lyrics_text=lyrics_text,
            lyrics_synced=lyrics_synced,
            quality_score=quality_score,
            is_verified=is_verified,
            line_count=line_count,
            content_hash=content_hash,
            provider_track_id=provider_track_id,
            has_translations=has_translations,
            language=language,
            fetched_at=datetime.now(timezone.utc),
        )
        self.session.add(lyrics)
        await self.session.flush()
        return lyrics

    async def get_sources_for_song(self, song_id: uuid.UUID) -> list[str]:
        """
        Get list of available lyrics sources for a song.

        Args:
            song_id: The song's UUID

        Returns:
            List of source identifiers
        """
        query = (
            select(Lyrics.source)
            .where(Lyrics.song_id == song_id)
            .distinct()
        )
        result = await self.session.execute(query)
        return [row[0] for row in result.all()]

    async def has_synced_lyrics(self, song_id: uuid.UUID) -> bool:
        """
        Check if a song has synced lyrics from any source.

        Args:
            song_id: The song's UUID

        Returns:
            True if synced lyrics exist
        """
        query = select(Lyrics.id).where(
            and_(
                Lyrics.song_id == song_id,
                Lyrics.lyrics_synced.isnot(None),
            )
        ).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def delete_for_song(self, song_id: uuid.UUID) -> int:
        """
        Delete all lyrics for a song.

        Args:
            song_id: The song's UUID

        Returns:
            Number of lyrics entries deleted
        """
        all_lyrics = await self.get_all_for_song(song_id)
        for lyrics in all_lyrics:
            await self.session.delete(lyrics)
        await self.session.flush()
        return len(all_lyrics)
