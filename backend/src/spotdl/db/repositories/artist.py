"""Artist repository for artist data access."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from spotdl.db.models.artist import Artist, ArtistPlatformLink
from spotdl.db.repositories.base import BaseRepository


class ArtistRepository(BaseRepository[Artist]):
    """Repository for Artist model operations."""

    model = Artist

    async def get_by_id_with_links(self, id: uuid.UUID) -> Artist | None:
        """Get an artist by ID with platform links eagerly loaded."""
        query = (
            select(Artist)
            .where(Artist.id == id)
            .options(selectinload(Artist.platform_links))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_normalized_name(self, name_normalized: str) -> Artist | None:
        """Get an artist by normalized name."""
        query = select(Artist).where(Artist.name_normalized == name_normalized)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_platform_id(
        self, platform: str, platform_id: str
    ) -> Artist | None:
        """Get an artist by platform and platform ID."""
        query = (
            select(Artist)
            .join(ArtistPlatformLink)
            .where(
                ArtistPlatformLink.platform == platform,
                ArtistPlatformLink.platform_id == platform_id,
            )
            .options(selectinload(Artist.platform_links))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def search_by_name(
        self, name: str, *, limit: int = 20
    ) -> list[Artist]:
        """Search artists by name (case-insensitive partial match)."""
        query = (
            select(Artist)
            .where(Artist.name.ilike(f"%{name}%"))
            .options(selectinload(Artist.platform_links))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_platform_link(
        self,
        artist_id: uuid.UUID,
        platform: str,
        platform_id: str,
        platform_url: str,
        followers: int | None = None,
    ) -> ArtistPlatformLink:
        """Add a platform link to an artist (or return existing one)."""
        # Check if link already exists
        existing = await self.get_platform_link(platform, platform_id)
        if existing:
            return existing

        link = ArtistPlatformLink(
            artist_id=artist_id,
            platform=platform,
            platform_id=platform_id,
            platform_url=platform_url,
            followers=followers,
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def get_platform_link(
        self, platform: str, platform_id: str
    ) -> ArtistPlatformLink | None:
        """Get a platform link by platform and platform ID."""
        query = select(ArtistPlatformLink).where(
            ArtistPlatformLink.platform == platform,
            ArtistPlatformLink.platform_id == platform_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
