"""Typed entity GETs (``/tracks|albums|artists|playlists/{id}``) + sub-resources.

All read-only: the entities were persisted by ``POST /resolve``; these handlers
map the service DTO to the typed ``*Out`` response model. ``{id}`` is a ``UUID``
(FastAPI rejects a malformed id with 422 ``validation_error``); an id that is
well-formed but absent raises ``NotFoundError`` → 404 ``not_found``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from spotdl_server.api.deps import get_entity_service
from spotdl_server.api.routers import ERROR_RESPONSES
from spotdl_server.api.schemas import (
    AlbumOut,
    ArtistOut,
    LyricsOut,
    LyricsResponse,
    MatchesResponse,
    MatchOut,
    PlaylistOut,
    TrackOut,
)
from spotdl_server.services.entities import EntityService

router = APIRouter(prefix="/api/v1", tags=["entities"], responses=ERROR_RESPONSES)


@router.get("/tracks/{id}", response_model=TrackOut)
async def get_track(
    id: UUID,
    service: EntityService = Depends(get_entity_service),
) -> TrackOut:
    return TrackOut.from_view(await service.get_track(id))


@router.get("/albums/{id}", response_model=AlbumOut)
async def get_album(
    id: UUID,
    service: EntityService = Depends(get_entity_service),
) -> AlbumOut:
    return AlbumOut.from_view(await service.get_album(id))


@router.get("/artists/{id}", response_model=ArtistOut)
async def get_artist(
    id: UUID,
    service: EntityService = Depends(get_entity_service),
) -> ArtistOut:
    return ArtistOut.from_view(await service.get_artist(id))


@router.get("/playlists/{id}", response_model=PlaylistOut)
async def get_playlist(
    id: UUID,
    service: EntityService = Depends(get_entity_service),
) -> PlaylistOut:
    return PlaylistOut.from_view(await service.get_playlist(id))


@router.get("/tracks/{id}/matches", response_model=MatchesResponse)
async def get_track_matches(
    id: UUID,
    service: EntityService = Depends(get_entity_service),
) -> MatchesResponse:
    matches = await service.get_matches(id)
    return MatchesResponse(track_id=str(id), matches=[MatchOut.from_view(m) for m in matches])


@router.get("/tracks/{id}/lyrics", response_model=LyricsResponse)
async def get_track_lyrics(
    id: UUID,
    service: EntityService = Depends(get_entity_service),
) -> LyricsResponse:
    lyrics = await service.get_lyrics(id)
    return LyricsResponse(track_id=str(id), lyrics=[LyricsOut.from_view(item) for item in lyrics])
