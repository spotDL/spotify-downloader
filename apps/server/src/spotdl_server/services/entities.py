"""EntityService — the read-only canonical-entity surface.

Backs the typed entity GETs of spec §6.2 (``GET /tracks|albums|artists|playlists/{id}``
plus ``/tracks/{id}/matches`` and ``/tracks/{id}/lyrics``). Every canonical row it
returns was already persisted by :class:`~spotdl_server.services.resolve.ResolveService`;
this service performs **no** provider I/O. It maps ORM rows to the frozen service
DTOs (via the shared :mod:`spotdl_server.services.views` mappers) with their
relations eagerly loaded.

Absence semantics (spec §10):

* An entity GET for an id that is not in the DB (or a syntactically invalid id)
  raises the **server-side** :class:`~spotdl_server.services.errors.NotFoundError`
  carrying the canonical ``entity_type`` and the requested id — never core's
  :class:`~spotdl_core.providers.EntityNotFound` (which is reserved for a provider
  reporting an upstream miss).
* ``get_matches`` / ``get_lyrics`` raise ``NotFoundError`` when the **track** is
  absent, but return an empty tuple when the track exists with no matches / lyrics
  yet.

Collaborators are injected; the service holds no FastAPI types and returns no ORM
rows. The session's unit of work is the caller's.
"""

from __future__ import annotations

import uuid

from spotdl_core.model import EntityType
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.models import Track as TrackModel
from spotdl_server.repositories.entities import (
    AlbumRepository,
    ArtistRepository,
    PlaylistRepository,
    TrackRepository,
)
from spotdl_server.repositories.lyrics import LyricsRepository
from spotdl_server.repositories.matches import MatchRepository
from spotdl_server.services import views
from spotdl_server.services.dto import (
    AlbumView,
    ArtistView,
    LyricsView,
    MatchView,
    PlaylistView,
    TrackView,
)
from spotdl_server.services.errors import NotFoundError


class EntityService:
    """Read-only mapping of persisted canonical entities to service DTOs."""

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._tracks = TrackRepository(session)
        self._albums = AlbumRepository(session)
        self._artists = ArtistRepository(session)
        self._playlists = PlaylistRepository(session)
        self._matches = MatchRepository(session)
        self._lyrics = LyricsRepository(session)

    async def get_track(self, id: uuid.UUID | str) -> TrackView:
        track = await self._require_track(EntityType.TRACK, id)
        matches = await self._matches.list_for_track(track.id)
        lyrics = await self._lyrics.list_for_track(track.id)
        return views.track_view(track, matches=matches, lyrics=lyrics, include_album=True)

    async def get_album(self, id: uuid.UUID | str) -> AlbumView:
        entity_id = _coerce(id)
        album = await self._albums.get(entity_id) if entity_id is not None else None
        if album is None:
            raise NotFoundError(entity_type=EntityType.ALBUM, entity_id=id)
        return views.album_view(album)

    async def get_artist(self, id: uuid.UUID | str) -> ArtistView:
        entity_id = _coerce(id)
        artist = await self._artists.get(entity_id) if entity_id is not None else None
        if artist is None:
            raise NotFoundError(entity_type=EntityType.ARTIST, entity_id=id)
        return views.artist_view(artist)

    async def get_playlist(self, id: uuid.UUID | str) -> PlaylistView:
        entity_id = _coerce(id)
        playlist = await self._playlists.get(entity_id) if entity_id is not None else None
        if playlist is None:
            raise NotFoundError(entity_type=EntityType.PLAYLIST, entity_id=id)
        return views.playlist_view(playlist)

    async def get_matches(self, track_id: uuid.UUID | str) -> tuple[MatchView, ...]:
        track = await self._require_track(EntityType.TRACK, track_id)
        rows = await self._matches.list_for_track(track.id)
        return tuple(views.match_view(row) for row in rows)

    async def get_lyrics(self, track_id: uuid.UUID | str) -> tuple[LyricsView, ...]:
        track = await self._require_track(EntityType.TRACK, track_id)
        rows = await self._lyrics.list_for_track(track.id)
        return tuple(views.lyrics_view(row) for row in rows)

    async def _require_track(self, entity_type: EntityType, id: uuid.UUID | str) -> TrackModel:
        """Load a track or raise :class:`NotFoundError` (invalid id counts as absent)."""
        entity_id = _coerce(id)
        track = await self._tracks.get(entity_id) if entity_id is not None else None
        if track is None:
            raise NotFoundError(entity_type=entity_type, entity_id=id)
        return track


def _coerce(value: uuid.UUID | str) -> uuid.UUID | None:
    """Coerce a public id to a ``UUID``; ``None`` for a syntactically invalid id."""
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None
