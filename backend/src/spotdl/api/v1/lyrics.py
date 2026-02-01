"""Lyrics API endpoints."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.config import get_settings
from spotdl.core.services.lyrics import LyricsResult, get_lyrics_service
from spotdl.db.database import get_db_session
from spotdl.db.models.song import Song
from spotdl.db.repositories.song import SongRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lyrics")


class LyricsResponse(BaseModel):
    """Response model for lyrics."""

    song_id: str
    lyrics_text: str
    lyrics_synced: str | None = None
    source: str
    from_cache: bool = False


class LyricsNotFoundResponse(BaseModel):
    """Response when lyrics are not found."""

    song_id: str
    message: str = "No lyrics found"


@router.get("/song/{song_id}", response_model=LyricsResponse | LyricsNotFoundResponse)
async def get_lyrics_for_song(
    song_id: str,
    force_refresh: Annotated[
        bool, Query(description="Force refresh lyrics from providers")
    ] = False,
    db: AsyncSession = Depends(get_db_session),
) -> LyricsResponse | LyricsNotFoundResponse:
    """
    Get lyrics for a song by its internal ID.

    Attempts to retrieve from cache first, then fetches from providers
    if not cached or force_refresh is True.
    """
    # Validate UUID
    try:
        song_uuid = uuid.UUID(song_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid song ID: {song_id}") from e

    # Get song from database
    song_repo = SongRepository(db)
    song = await song_repo.get_by_id(song_uuid)

    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    # Get lyrics using service
    settings = get_settings()
    genius_token = settings.genius_access_token.get_secret_value() if settings.genius_access_token else None

    async with get_lyrics_service(
        session=db,
        genius_token=genius_token,
        enable_cache=True,
    ) as lyrics_service:
        result = await lyrics_service.fetch_lyrics(
            song_id=song_uuid,
            name=song.name,
            artists=song.artists,
            force_refresh=force_refresh,
        )

    if not result:
        return LyricsNotFoundResponse(song_id=song_id)

    return LyricsResponse(
        song_id=song_id,
        lyrics_text=result.lyrics_text,
        lyrics_synced=result.lyrics_synced,
        source=result.source,
        from_cache=result.from_cache,
    )


@router.get("/search", response_model=LyricsResponse | LyricsNotFoundResponse)
async def search_lyrics(
    name: Annotated[str, Query(description="Song name")],
    artist: Annotated[str, Query(description="Artist name")],
    db: AsyncSession = Depends(get_db_session),
) -> LyricsResponse | LyricsNotFoundResponse:
    """
    Search for lyrics by song name and artist.

    Does not cache results (use song ID endpoint for caching).
    """
    settings = get_settings()
    genius_token = settings.genius_access_token.get_secret_value() if settings.genius_access_token else None

    async with get_lyrics_service(
        session=db,
        genius_token=genius_token,
        enable_cache=False,  # Don't cache search results
    ) as lyrics_service:
        # Use a dummy UUID since we're not caching
        result = await lyrics_service.fetch_lyrics(
            song_id=uuid.uuid4(),
            name=name,
            artists=[artist],
            force_refresh=True,
        )

    if not result:
        return LyricsNotFoundResponse(song_id="search", message="No lyrics found")

    return LyricsResponse(
        song_id="search",
        lyrics_text=result.lyrics_text,
        lyrics_synced=result.lyrics_synced,
        source=result.source,
        from_cache=False,
    )
