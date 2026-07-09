"""Canonical entity repositories: tracks, albums, artists, playlists.

Each repository owns a single canonical table plus the ordered many-to-many
link tables that hang off it. All relations load eagerly (``lazy="selectin"`` on
the models), so ``get`` returns a fully-populated object. Repositories never
commit — the caller's unit of work does.
"""

from __future__ import annotations

import unicodedata
import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.models import (
    Album,
    Artist,
    Playlist,
    Track,
    playlist_tracks,
    track_artists,
)


def normalize_artist_name(name: str) -> str:
    """NFKC-normalize, casefold, collapse internal whitespace runs to one space, strip.

    The single implementation of the artist-identity dedup key (schema §6.1
    artist-identity contract). Merge and any future correction flow import this
    — the key is never re-derived inline. Examples:
    ``"  The  Beatles "`` → ``"the beatles"``; ``"BØRNS"`` → ``"børns"``.
    """
    folded = unicodedata.normalize("NFKC", name).casefold()
    return " ".join(folded.split())


def _dedupe_preserving_order(ids: list[uuid.UUID]) -> list[uuid.UUID]:
    seen: set[uuid.UUID] = set()
    ordered: list[uuid.UUID] = []
    for value in ids:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


class TrackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: uuid.UUID) -> Track | None:
        return await self.session.get(Track, id)

    async def create(self, **fields: Any) -> Track:
        track = Track(**fields)
        self.session.add(track)
        await self.session.flush()
        return track

    async def update(self, model: Track, **fields: Any) -> Track:
        for key, value in fields.items():
            setattr(model, key, value)
        await self.session.flush()
        return model

    async def get_or_create_by_isrc(self, isrc: str) -> tuple[Track, bool]:
        """Return the canonical track for ``isrc``, creating a stub if absent.

        The dedupe hook used by merge. A newly created row is a stub
        (``name=""``) that the merger fills in via :meth:`update`.
        """
        result = await self.session.execute(select(Track).where(Track.isrc == isrc))
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing, False
        track = Track(name="", isrc=isrc)
        self.session.add(track)
        await self.session.flush()
        return track, True

    async def set_artists(self, track: Track, artist_ids_in_order: list[uuid.UUID]) -> None:
        """Replace the track's full ordered artist set. Re-runnable/idempotent.

        Positions are assigned by list index (0 = main artist). Duplicate ids
        are deduped keeping first occurrence so the composite PK never collides.
        """
        ordered = _dedupe_preserving_order(artist_ids_in_order)
        await self.session.execute(
            delete(track_artists).where(track_artists.c.track_id == track.id)
        )
        rows = [
            {"track_id": track.id, "artist_id": artist_id, "position": position}
            for position, artist_id in enumerate(ordered)
        ]
        if rows:
            await self.session.execute(track_artists.insert(), rows)
        await self.session.flush()
        await self.session.refresh(track, attribute_names=["artists"])


class AlbumRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: uuid.UUID) -> Album | None:
        return await self.session.get(Album, id)

    async def create(self, **fields: Any) -> Album:
        album = Album(**fields)
        self.session.add(album)
        await self.session.flush()
        return album

    async def update(self, model: Album, **fields: Any) -> Album:
        for key, value in fields.items():
            setattr(model, key, value)
        await self.session.flush()
        return model


class ArtistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: uuid.UUID) -> Artist | None:
        return await self.session.get(Artist, id)

    async def create(self, **fields: Any) -> Artist:
        artist = Artist(**fields)
        self.session.add(artist)
        await self.session.flush()
        return artist

    async def update(self, model: Artist, **fields: Any) -> Artist:
        for key, value in fields.items():
            setattr(model, key, value)
        await self.session.flush()
        return model

    async def get_or_create_by_normalized_name(self, name: str) -> tuple[Artist, bool]:
        """Resolve the canonical artist row by normalized name (the dedup key).

        Returns the existing row for :func:`normalize_artist_name`\\ (name) or
        creates one with ``name`` (original casing) and the computed
        ``normalized_name``. The artist-dedup hook used by merge.
        """
        key = normalize_artist_name(name)
        result = await self.session.execute(select(Artist).where(Artist.normalized_name == key))
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing, False
        artist = Artist(name=name, normalized_name=key)
        self.session.add(artist)
        await self.session.flush()
        return artist, True


class PlaylistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: uuid.UUID) -> Playlist | None:
        return await self.session.get(Playlist, id)

    async def create(self, **fields: Any) -> Playlist:
        playlist = Playlist(**fields)
        self.session.add(playlist)
        await self.session.flush()
        return playlist

    async def update(self, model: Playlist, **fields: Any) -> Playlist:
        for key, value in fields.items():
            setattr(model, key, value)
        await self.session.flush()
        return model

    async def set_tracks(self, playlist: Playlist, track_ids_in_order: list[uuid.UUID]) -> None:
        """Replace the playlist's full ordered track set. Re-runnable/idempotent."""
        ordered = _dedupe_preserving_order(track_ids_in_order)
        await self.session.execute(
            delete(playlist_tracks).where(playlist_tracks.c.playlist_id == playlist.id)
        )
        rows = [
            {"playlist_id": playlist.id, "track_id": track_id, "position": position}
            for position, track_id in enumerate(ordered)
        ]
        if rows:
            await self.session.execute(playlist_tracks.insert(), rows)
        await self.session.flush()
        await self.session.refresh(playlist, attribute_names=["tracks"])
