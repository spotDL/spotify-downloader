"""Lyrics API endpoints."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.api.v1.auth import get_current_user_id
from spotdl.api.v1.dependencies import UserPreferences, get_user_preferences
from spotdl.api.v1.validation import validate_uuid
from spotdl.config import get_settings
from spotdl.core.services.entity_unified import EntityNotFoundError, UnifiedEntityService
from spotdl.core.services.lyrics import get_lyrics_service
from spotdl.db.database import get_db_session
from spotdl.db.models.entity_unified import EntityCanonical
from spotdl.db.repositories.lyrics import LyricsRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lyrics")


class LyricsResponse(BaseModel):
    """Response model for lyrics."""

    entity_id: str
    lyrics_text: str
    lyrics_synced: str | None = None
    source: str
    from_cache: bool = False


class LyricsNotFoundResponse(BaseModel):
    """Response when lyrics are not found."""

    entity_id: str
    message: str = "No lyrics found"


@router.get("/entity/{entity_id}", response_model=LyricsResponse | LyricsNotFoundResponse)
async def get_lyrics_for_entity(
    entity_id: str,
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
    force_refresh: Annotated[
        bool, Query(description="Force refresh lyrics from providers")
    ] = False,
    db: AsyncSession = Depends(get_db_session),
) -> LyricsResponse | LyricsNotFoundResponse:
    """
    Get lyrics for an entity by its internal ID.

    Attempts to retrieve from cache first, then fetches from providers
    if not cached or force_refresh is True.

    Uses user's lyrics source preferences to determine provider order.
    Unauthenticated users get default provider order.
    """
    # Validate UUID
    entity_uuid = validate_uuid(entity_id, "entity ID")

    entity_service = UnifiedEntityService(db)
    try:
        entity = await entity_service.get_entity(entity_uuid)
    except EntityNotFoundError:
        await entity_service.close()
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

    await entity_service.close()

    # Get lyrics using service
    settings = get_settings()
    genius_token = (
        settings.genius_access_token.get_secret_value() if settings.genius_access_token else None
    )

    ec_result = await db.execute(
        select(EntityCanonical).where(EntityCanonical.entity_id == entity_uuid)
    )
    ec = ec_result.scalar_one_or_none()
    canonical = ec.canonical if ec else {}

    artists = canonical.get("artists", [])
    if isinstance(artists, str):
        artists = [artists]

    async with get_lyrics_service(
        session=db,
        genius_token=genius_token,
        enable_cache=True,
        lyrics_preferences=preferences["lyrics"],
    ) as lyrics_service:
        result = await lyrics_service.fetch_lyrics(
            entity_id=entity_uuid,
            name=ec.name if ec else "Unknown",
            artists=artists,
            force_refresh=force_refresh,
        )

    if not result:
        return LyricsNotFoundResponse(entity_id=entity_id)

    return LyricsResponse(
        entity_id=entity_id,
        lyrics_text=result.lyrics_text,
        lyrics_synced=result.lyrics_synced,
        source=result.source,
        from_cache=result.from_cache,
    )


@router.get("/search", response_model=LyricsResponse | LyricsNotFoundResponse)
async def search_lyrics(
    name: Annotated[str, Query(description="Song/Entity name")],
    artist: Annotated[str, Query(description="Artist name")],
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
    db: AsyncSession = Depends(get_db_session),
) -> LyricsResponse | LyricsNotFoundResponse:
    """
    Search for lyrics by name and artist.

    Does not cache results (use entity ID endpoint for caching).

    Uses user's lyrics source preferences to determine provider order.
    Unauthenticated users get default provider order.
    """
    settings = get_settings()
    genius_token = (
        settings.genius_access_token.get_secret_value() if settings.genius_access_token else None
    )

    async with get_lyrics_service(
        session=db,
        genius_token=genius_token,
        enable_cache=False,  # Don't cache search results
        lyrics_preferences=preferences["lyrics"],
    ) as lyrics_service:
        # Use a dummy UUID since we're not caching
        result = await lyrics_service.fetch_lyrics(
            entity_id=uuid.uuid4(),
            name=name,
            artists=[artist],
            force_refresh=True,
        )

    if not result:
        return LyricsNotFoundResponse(entity_id="search", message="No lyrics found")

    return LyricsResponse(
        entity_id="search",
        source=result.source,
        lyrics_text=result.lyrics_text,
        lyrics_synced=result.lyrics_synced,
        from_cache=False,
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


class SubmitLyricsRequest(BaseModel):
    """Request model for submitting lyrics."""

    lyrics_text: str
    lyrics_synced: str | None = None
    source: str = "user"


@router.post("/entity/{entity_id}", response_model=LyricsSourceResponse)
async def submit_user_lyrics(
    entity_id: str,
    request: SubmitLyricsRequest,
    _user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> LyricsSourceResponse:
    """
    Submit user-provided lyrics for an entity.

    These metrics are saved with the provided source (default "user").
    """
    # Validate UUID
    entity_uuid = validate_uuid(entity_id, "entity ID")

    entity_service = UnifiedEntityService(db)
    try:
        entity = await entity_service.get_entity(entity_uuid)
    except EntityNotFoundError:
        await entity_service.close()
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
    finally:
        await entity_service.close()

    lyrics_repo = LyricsRepository(db)

    # Simple line count
    lines = [line for line in request.lyrics_text.splitlines() if line.strip()]
    line_count = len(lines)

    saved_lyrics = await lyrics_repo.upsert(
        entity_id=entity_uuid,
        source=request.source or "user",
        lyrics_text=request.lyrics_text.strip(),
        lyrics_synced=request.lyrics_synced.strip() if request.lyrics_synced else None,
        quality_score=1.0,  # User submitted considered high quality
        is_verified=True,
        line_count=line_count,
    )

    return LyricsSourceResponse(
        source=saved_lyrics.source,
        lyrics_text=saved_lyrics.lyrics_text,
        lyrics_synced=saved_lyrics.lyrics_synced,
        quality_score=saved_lyrics.quality_score,
        is_verified=saved_lyrics.is_verified or False,
        language=saved_lyrics.language,
        has_translations=saved_lyrics.has_translations,
    )


class AllLyricsResponse(BaseModel):
    """Response model for all lyrics sources."""

    entity_id: str
    lyrics: list[LyricsSourceResponse]
    total_sources: int


@router.get("/entity/{entity_id}/all")
async def get_all_lyrics_for_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> AllLyricsResponse:
    """
    Get lyrics from ALL sources for an entity.

    Returns lyrics from all cached sources (Genius, MusixMatch, LRCLIB, AZLyrics),
    allowing users to compare and choose their preferred version.
    """
    # Validate UUID
    entity_uuid = validate_uuid(entity_id, "entity ID")

    entity_service = UnifiedEntityService(db)
    try:
        entity = await entity_service.get_entity(entity_uuid)
    except EntityNotFoundError:
        await entity_service.close()
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
    finally:
        await entity_service.close()

    # Get all lyrics from repository
    lyrics_repo = LyricsRepository(db)
    all_lyrics = await lyrics_repo.get_all_for_entity(entity_uuid)

    return AllLyricsResponse(
        entity_id=entity_id,
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


@router.post("/entity/{entity_id}/fetch-all")
async def fetch_all_lyrics_sources(
    entity_id: str,
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
    entity_uuid = validate_uuid(entity_id, "entity ID")

    entity_service = UnifiedEntityService(db)
    try:
        entity = await entity_service.get_entity(entity_uuid)
    except EntityNotFoundError:
        await entity_service.close()
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
    finally:
        await entity_service.close()

    # Fetch from all providers
    settings = get_settings()
    genius_token = (
        settings.genius_access_token.get_secret_value() if settings.genius_access_token else None
    )

    ec_result2 = await db.execute(
        select(EntityCanonical).where(EntityCanonical.entity_id == entity_uuid)
    )
    ec2 = ec_result2.scalar_one_or_none()
    canonical2 = ec2.canonical if ec2 else {}

    async with get_lyrics_service(
        session=db,
        genius_token=genius_token,
        enable_cache=True,
        lyrics_preferences=preferences["lyrics"],
    ) as lyrics_service:
        artists = canonical2.get("artists", [])
        if isinstance(artists, str):
            artists = [artists]

        album_name = canonical2.get("album_name")
        duration = canonical2.get("duration", canonical2.get("duration_ms", 0) // 1000)

        results = await lyrics_service.fetch_all_lyrics(
            entity_id=entity_uuid,
            name=ec2.name if ec2 else "Unknown",
            artists=artists,
            album_name=album_name,
            duration=duration,
        )

    return AllLyricsResponse(
        entity_id=entity_id,
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


@router.post("/{lyrics_id}/vote")
async def vote_lyrics(
    lyrics_id: str,
    vote: Annotated[str, Query(description="Vote: 'up' or 'down'")],
    _user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    lyrics_uuid = validate_uuid(lyrics_id, "lyrics ID")
    if vote not in ("up", "down"):
        raise HTTPException(status_code=400, detail="Invalid vote")

    from spotdl.db.models.lyrics import Lyrics

    values = (
        {Lyrics.upvotes: Lyrics.upvotes + 1}
        if vote == "up"
        else {Lyrics.downvotes: Lyrics.downvotes + 1}
    )
    result = await db.execute(
        update(Lyrics).where(Lyrics.id == lyrics_uuid).values(**values).returning(Lyrics.upvotes, Lyrics.downvotes)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Lyrics not found")

    return {"status": "ok", "upvotes": str(row.upvotes), "downvotes": str(row.downvotes)}
