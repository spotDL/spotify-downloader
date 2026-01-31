"""Album repository for album data access."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from spotdl.db.models.album import Album, AlbumPlatformLink
from spotdl.db.repositories.base import BaseRepository


class AlbumRepository(BaseRepository[Album]):
    """Repository for Album model operations."""

    model = Album

    async def get_by_id_with_links(self, id: uuid.UUID) -> Album | None:
        """Get an album by ID with platform links eagerly loaded."""
        query = (
            select(Album)
            .where(Album.id == id)
            .options(selectinload(Album.platform_links))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_normalized_name_and_artist(
        self, name_normalized: str, artist_id: uuid.UUID | None = None
    ) -> Album | None:
        """Get an album by normalized name and optionally artist."""
        query = select(Album).where(Album.name_normalized == name_normalized)
        if artist_id is not None:
            query = query.where(Album.artist_id == artist_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_platform_id(
        self, platform: str, platform_id: str
    ) -> Album | None:
        """Get an album by platform and platform ID."""
        query = (
            select(Album)
            .join(AlbumPlatformLink)
            .where(
                AlbumPlatformLink.platform == platform,
                AlbumPlatformLink.platform_id == platform_id,
            )
            .options(selectinload(Album.platform_links))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_artist_id(
        self, artist_id: uuid.UUID, *, limit: int = 100
    ) -> list[Album]:
        """Get all albums by an artist."""
        query = (
            select(Album)
            .where(Album.artist_id == artist_id)
            .options(selectinload(Album.platform_links))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_by_name(
        self, name: str, *, limit: int = 20
    ) -> list[Album]:
        """Search albums by name (case-insensitive partial match)."""
        query = (
            select(Album)
            .where(Album.name.ilike(f"%{name}%"))
            .options(selectinload(Album.platform_links))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_platform_link(
        self,
        album_id: uuid.UUID,
        platform: str,
        platform_id: str,
        platform_url: str,
    ) -> AlbumPlatformLink:
        """Add a platform link to an album."""
        link = AlbumPlatformLink(
            album_id=album_id,
            platform=platform,
            platform_id=platform_id,
            platform_url=platform_url,
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def get_platform_link(
        self, platform: str, platform_id: str
    ) -> AlbumPlatformLink | None:
        """Get a platform link by platform and platform ID."""
        query = select(AlbumPlatformLink).where(
            AlbumPlatformLink.platform == platform,
            AlbumPlatformLink.platform_id == platform_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
