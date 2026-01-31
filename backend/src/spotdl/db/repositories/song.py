"""Song repository for song data access."""

from __future__ import annotations

from sqlalchemy import select

from spotdl.db.models.song import Song
from spotdl.db.repositories.base import BaseRepository


class SongRepository(BaseRepository[Song]):
    """Repository for Song model operations."""

    model = Song

    async def get_by_platform_id(
        self, platform: str, platform_id: str
    ) -> Song | None:
        """Get a song by platform and platform ID."""
        query = select(Song).where(
            Song.platform == platform,
            Song.platform_id == platform_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_url(self, platform_url: str) -> Song | None:
        """Get a song by its platform URL."""
        query = select(Song).where(Song.platform_url == platform_url)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_isrc(self, isrc: str) -> list[Song]:
        """Get all songs with a given ISRC."""
        query = select(Song).where(Song.isrc == isrc)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_by_name(
        self, name: str, platform: str | None = None, *, limit: int = 20
    ) -> list[Song]:
        """Search songs by name with optional platform filter."""
        query = select(Song).where(Song.name.ilike(f"%{name}%"))

        if platform:
            query = query.where(Song.platform == platform)

        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
