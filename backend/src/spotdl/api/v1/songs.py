"""Song resolution API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from spotdl.core.services.song import (
    SongServiceError,
    UnsupportedURLError,
    get_song_service,
)
from spotdl.core.types.song import Platform

router = APIRouter(prefix="/songs")


class SongResponse(BaseModel):
    """Response model for a song."""

    name: str
    artists: list[str]
    artist: str
    duration: int
    platform: str
    platform_id: str
    url: str
    album_name: str | None = None
    album_artist: str | None = None
    album_id: str | None = None
    track_number: int | None = None
    disc_number: int | None = None
    year: int | None = None
    date: str | None = None
    genres: list[str] = []
    isrc: str | None = None
    explicit: bool = False
    cover_url: str | None = None

    model_config = {"from_attributes": True}


class SongListResponse(BaseModel):
    """Response model for a list of songs."""

    name: str
    url: str
    platform: str
    songs: list[SongResponse]
    total: int


class ResolveRequest(BaseModel):
    """Request model for URL resolution."""

    url: HttpUrl


class ResolveResponse(BaseModel):
    """Response model for URL resolution."""

    songs: list[SongResponse]
    total: int


class SearchRequest(BaseModel):
    """Request model for search."""

    query: str
    platform: str = "spotify"
    limit: int = 10


class SearchResponse(BaseModel):
    """Response model for search."""

    songs: list[SongResponse]
    total: int


@router.get("/resolve")
async def resolve_url(
    url: Annotated[str, Query(description="URL to resolve")],
) -> ResolveResponse:
    """
    Resolve a URL to song metadata.

    Supports URLs from: Spotify, YouTube Music, Deezer, Apple Music,
    Tidal, SoundCloud, Bandcamp.
    """
    service = get_song_service()

    try:
        songs = await service.resolve_url(url)

        song_responses = [
            SongResponse(
                name=song.name,
                artists=list(song.artists),
                artist=song.artist,
                duration=song.duration,
                platform=song.platform.value,
                platform_id=song.platform_id,
                url=song.url,
                album_name=song.album_name,
                album_artist=song.album_artist,
                album_id=song.album_id,
                track_number=song.track_number,
                disc_number=song.disc_number,
                year=song.year if song.year else None,
                date=song.date,
                genres=list(song.genres) if song.genres else [],
                isrc=song.isrc,
                explicit=song.explicit,
                cover_url=song.cover_url,
            )
            for song in songs
        ]

        return ResolveResponse(
            songs=song_responses,
            total=len(song_responses),
        )

    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SongServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/search")
async def search_songs(
    query: Annotated[str, Query(description="Search query")],
    platform: Annotated[str, Query(description="Platform to search")] = "spotify",
    limit: Annotated[int, Query(ge=1, le=50, description="Maximum results")] = 10,
) -> SearchResponse:
    """
    Search for songs on a platform.

    Supports: spotify, youtube_music, deezer, soundcloud, bandcamp.
    """
    service = get_song_service()

    try:
        platform_enum = Platform(platform)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform: {platform}. Supported: {[p.value for p in Platform]}",
        ) from e

    try:
        songs = await service.search(query, platform=platform_enum, limit=limit)

        song_responses = [
            SongResponse(
                name=song.name,
                artists=list(song.artists),
                artist=song.artist,
                duration=song.duration,
                platform=song.platform.value,
                platform_id=song.platform_id,
                url=song.url,
                album_name=song.album_name,
                album_artist=song.album_artist,
                album_id=song.album_id,
                track_number=song.track_number,
                disc_number=song.disc_number,
                year=song.year if song.year else None,
                date=song.date,
                genres=list(song.genres) if song.genres else [],
                isrc=song.isrc,
                explicit=song.explicit,
                cover_url=song.cover_url,
            )
            for song in songs
        ]

        return SearchResponse(
            songs=song_responses,
            total=len(song_responses),
        )

    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SongServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/platforms")
async def get_supported_platforms() -> dict[str, list[str]]:
    """Get list of supported source platforms."""
    service = get_song_service()
    return {
        "platforms": [p.value for p in service.supported_platforms],
    }
