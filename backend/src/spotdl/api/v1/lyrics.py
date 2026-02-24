"""Lyrics API endpoints."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.api.v1.dependencies import UserPreferences, get_user_preferences
from spotdl.api.v1.validation import validate_uuid
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
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
    force_refresh: Annotated[
        bool, Query(description="Force refresh lyrics from providers")
    ] = False,
    db: AsyncSession = Depends(get_db_session),
) -> LyricsResponse | LyricsNotFoundResponse:
    """
    Get lyrics for a song by its internal ID.

    Attempts to retrieve from cache first, then fetches from providers
    if not cached or force_refresh is True.

    Uses user's lyrics source preferences to determine provider order.
    Unauthenticated users get default provider order.
    """
    # Validate UUID
    song_uuid = validate_uuid(song_id, "song ID")

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
        lyrics_preferences=preferences["lyrics"],
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
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
    db: AsyncSession = Depends(get_db_session),
) -> LyricsResponse | LyricsNotFoundResponse:
    """
    Search for lyrics by song name and artist.

    Does not cache results (use song ID endpoint for caching).

    Uses user's lyrics source preferences to determine provider order.
    Unauthenticated users get default provider order.
    """
    settings = get_settings()
    genius_token = settings.genius_access_token.get_secret_value() if settings.genius_access_token else None

    async with get_lyrics_service(
        session=db,
        genius_token=genius_token,
        enable_cache=False,  # Don't cache search results
        lyrics_preferences=preferences["lyrics"],
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

class SubmitLyricsRequest(BaseModel):
    """Request model for submitting lyrics."""

    lyrics_text: str
    lyrics_synced: str | None = None
    source: str = "user"


@router.post("/song/{song_id}", response_model=LyricsSourceResponse)
async def submit_user_lyrics(
    song_id: str,
    request: SubmitLyricsRequest,
    db: AsyncSession = Depends(get_db_session),
) -> LyricsSourceResponse:
    """
    Submit user-provided lyrics for a song.
    
    These metrics are saved with the provided source (default "user"). 
    """
    from spotdl.db.repositories import LyricsRepository

    # Validate UUID
    song_uuid = validate_uuid(song_id, "song ID")

    # Get song from database
    song_repo = SongRepository(db)
    song = await song_repo.get_by_id(song_uuid)

    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    lyrics_repo = LyricsRepository(db)
    
    # Simple line count
    lines = [line for line in request.lyrics_text.splitlines() if line.strip()]
    line_count = len(lines)

    saved_lyrics = await lyrics_repo.upsert(
        song_id=song_uuid,
        source=request.source or "user",
        lyrics_text=request.lyrics_text.strip(),
        lyrics_synced=request.lyrics_synced.strip() if request.lyrics_synced else None,
        quality_score=1.0,  # User submitted considered high quality
        is_verified=True,
        line_count=line_count,
    )
    
    await db.commit()

    return LyricsSourceResponse(
        source=saved_lyrics.source,
        lyrics_text=saved_lyrics.lyrics_text,
        lyrics_synced=saved_lyrics.lyrics_synced,
        quality_score=saved_lyrics.quality_score,
        is_verified=saved_lyrics.is_verified or False,
        language=saved_lyrics.language,
        has_translations=saved_lyrics.has_translations,
    )
class LyricsSourceResponse(BaseModel):
    """Response model for a single lyrics source."""

    source: str
    lyrics_text: str
    lyrics_synced: str | None = None
    quality_score: float | None = None
    is_verified: bool = False
    language: str | None = None
    has_translations: bool | None = None


class AllLyricsResponse(BaseModel):
    """Response model for all lyrics sources."""

    song_id: str
    lyrics: list[LyricsSourceResponse]
    total_sources: int


@router.get("/song/{song_id}/all")
async def get_all_lyrics_for_song(
    song_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> AllLyricsResponse:
    """
    Get lyrics from ALL sources for a song.

    Returns lyrics from all cached sources (Genius, MusixMatch, LRCLIB, AZLyrics),
    allowing users to compare and choose their preferred version.
    """
    from spotdl.db.repositories import LyricsRepository

    # Validate UUID
    song_uuid = validate_uuid(song_id, "song ID")

    # Get song from database
    song_repo = SongRepository(db)
    song = await song_repo.get_by_id(song_uuid)

    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    # Get all lyrics from repository
    lyrics_repo = LyricsRepository(db)
    all_lyrics = await lyrics_repo.get_all_for_song(song_uuid)

    return AllLyricsResponse(
        song_id=song_id,
        lyrics=[
            LyricsSourceResponse(
                source=lyrics.source,
                lyrics_text=lyrics.lyrics_text,
                lyrics_synced=lyrics.lyrics_synced,
                quality_score=lyrics.quality_score,
                is_verified=lyrics.is_verified or False,
                language=lyrics.language,
                has_translations=lyrics.has_translations,
            )
            for lyrics in all_lyrics
        ],
        total_sources=len(all_lyrics),
    )


@router.post("/song/{song_id}/fetch-all")
async def fetch_all_lyrics_sources(
    song_id: str,
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
    db: AsyncSession = Depends(get_db_session),
) -> AllLyricsResponse:
    """
    Fetch lyrics from ALL providers and store each result.

    Unlike the regular lyrics endpoint which returns the first result,
    this fetches from ALL providers in parallel and stores each result
    separately, allowing users to compare lyrics from different sources.

    Uses user's lyrics source preferences to determine which providers to use
    and in what order. Unauthenticated users get default provider set.
    """
    # Validate UUID
    song_uuid = validate_uuid(song_id, "song ID")

    # Get song from database
    song_repo = SongRepository(db)
    song = await song_repo.get_by_id(song_uuid)

    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    # Fetch from all providers
    settings = get_settings()
    genius_token = settings.genius_access_token.get_secret_value() if settings.genius_access_token else None

    async with get_lyrics_service(
        session=db,
        genius_token=genius_token,
        enable_cache=True,
        lyrics_preferences=preferences["lyrics"],
    ) as lyrics_service:
        results = await lyrics_service.fetch_all_lyrics(
            song_id=song_uuid,
            name=song.name,
            artists=song.artists or [],
            album_name=song.album_name,
            duration=song.duration_seconds,
        )

    await db.commit()

    return AllLyricsResponse(
        song_id=song_id,
        lyrics=[
            LyricsSourceResponse(
                source=r.source,
                lyrics_text=r.lyrics_text,
                lyrics_synced=r.lyrics_synced,
                quality_score=None,  # Not available in LyricsResult
                is_verified=False,
            )
            for r in results
        ],
        total_sources=len(results),
    )
