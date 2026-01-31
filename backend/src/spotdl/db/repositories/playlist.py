"""Playlist repository for playlist data access."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from spotdl.db.models.playlist import Playlist, PlaylistPlatformLink, PlaylistTrack
from spotdl.db.repositories.base import BaseRepository


class PlaylistRepository(BaseRepository[Playlist]):
    """Repository for Playlist model operations."""

    model = Playlist

    async def get_by_id_with_links(self, id: uuid.UUID) -> Playlist | None:
        """Get a playlist by ID with platform links eagerly loaded."""
        query = (
            select(Playlist)
            .where(Playlist.id == id)
            .options(selectinload(Playlist.platform_links))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id_with_tracks(self, id: uuid.UUID) -> Playlist | None:
        """Get a playlist by ID with tracks eagerly loaded."""
        query = (
            select(Playlist)
            .where(Playlist.id == id)
            .options(
                selectinload(Playlist.platform_links),
                selectinload(Playlist.tracks).selectinload(PlaylistTrack.song),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_platform_id(
        self, platform: str, platform_id: str
    ) -> Playlist | None:
        """Get a playlist by platform and platform ID."""
        query = (
            select(Playlist)
            .join(PlaylistPlatformLink)
            .where(
                PlaylistPlatformLink.platform == platform,
                PlaylistPlatformLink.platform_id == platform_id,
            )
            .options(selectinload(Playlist.platform_links))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def search_by_name(
        self, name: str, *, limit: int = 20
    ) -> list[Playlist]:
        """Search playlists by name (case-insensitive partial match)."""
        query = (
            select(Playlist)
            .where(Playlist.name.ilike(f"%{name}%"))
            .options(selectinload(Playlist.platform_links))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_platform_link(
        self,
        playlist_id: uuid.UUID,
        platform: str,
        platform_id: str,
        platform_url: str,
        followers: int | None = None,
    ) -> PlaylistPlatformLink:
        """Add a platform link to a playlist (or return existing one)."""
        # Check if link already exists
        existing = await self.get_platform_link(platform, platform_id)
        if existing:
            return existing

        link = PlaylistPlatformLink(
            playlist_id=playlist_id,
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
    ) -> PlaylistPlatformLink | None:
        """Get a platform link by platform and platform ID."""
        query = select(PlaylistPlatformLink).where(
            PlaylistPlatformLink.platform == platform,
            PlaylistPlatformLink.platform_id == platform_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add_track(
        self,
        playlist_id: uuid.UUID,
        song_id: uuid.UUID,
        position: int,
    ) -> PlaylistTrack:
        """Add a track to a playlist."""
        track = PlaylistTrack(
            playlist_id=playlist_id,
            song_id=song_id,
            position=position,
        )
        self.session.add(track)
        await self.session.flush()
        return track

    async def clear_tracks(self, playlist_id: uuid.UUID) -> int:
        """Remove all tracks from a playlist. Returns count of removed tracks."""
        query = select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id)
        result = await self.session.execute(query)
        tracks = result.scalars().all()
        count = len(tracks)
        for track in tracks:
            await self.session.delete(track)
        await self.session.flush()
        return count
