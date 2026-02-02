"""Match finding API endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.api.v1.auth import get_current_user_id
from spotdl.api.v1.dependencies import UserPreferences, get_user_preferences
from spotdl.core.reputation import ReputationReward
from spotdl.core.services.match import get_match_service
from spotdl.core.services.song import (
    SongServiceError,
    UnsupportedURLError,
    get_song_service,
)
from spotdl.core.types.result import TargetPlatform
from spotdl.db.database import get_db_session
from spotdl.db.models.match import MatchType
from spotdl.db.repositories.match import MatchRepository
from spotdl.db.repositories.user import UserRepository
from spotdl.providers.sources import detect_platform

router = APIRouter(prefix="/matches")


class MatchResult(BaseModel):
    """Response model for a match result."""

    name: str
    artists: list[str]
    artist: str
    duration: int
    platform: str
    platform_id: str
    url: str
    album_name: str | None = None
    cover_url: str | None = None
    views: int | None = None
    explicit: bool = False
    verified: bool = False


class MatchResponse(BaseModel):
    """Response model for a match."""

    source_url: str
    target_url: str
    target_platform: str
    score: float
    confidence: float
    match_type: str
    result: MatchResult


class FindMatchesRequest(BaseModel):
    """Request model for finding matches."""

    source_url: HttpUrl
    target_platforms: list[str] | None = None
    limit: int = 5


class FindMatchesResponse(BaseModel):
    """Response model for finding matches."""

    source_url: str
    matches: list[MatchResponse]
    total: int


class SubmitMatchRequest(BaseModel):
    """Request model for submitting a user match."""

    source_url: HttpUrl
    target_url: HttpUrl


class SubmitMatchResponse(BaseModel):
    """Response model for submitted match."""

    id: str
    source_url: str
    target_url: str
    target_platform: str
    match_type: str
    message: str


def detect_target_platform(url: str) -> str | None:
    """Detect target platform from URL."""
    if "youtube.com" in url or "youtu.be" in url:
        if "music.youtube.com" in url:
            return "youtube_music"
        return "youtube"
    elif "soundcloud.com" in url:
        return "soundcloud"
    elif "bandcamp.com" in url:
        return "bandcamp"
    elif "piped" in url:
        return "piped"
    return None


@router.post("/find")
async def find_matches(
    request: FindMatchesRequest,
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
) -> FindMatchesResponse:
    """
    Find matches for a source URL on target platforms.

    Uses user's audio source preferences to determine which platforms to search
    and in what order. Unauthenticated users get default platform order.

    Args:
        request: Source URL and optional target platforms
        preferences: User's provider preferences

    Returns:
        List of matches sorted by score
    """
    song_service = get_song_service()
    match_service = get_match_service(audio_preferences=preferences["audio"])

    # Resolve source URL to song
    try:
        songs = await song_service.resolve_url(str(request.source_url))
        if not songs:
            raise HTTPException(status_code=404, detail="No songs found for URL")

        # Use first song for matching
        song = songs[0]

    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SongServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Parse target platforms
    target_platforms = None
    if request.target_platforms:
        try:
            target_platforms = [TargetPlatform(p) for p in request.target_platforms]
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid target platform. Supported: {[p.value for p in TargetPlatform]}",
            ) from e

    # Find matches
    matches = await match_service.find_matches(
        song,
        target_platforms=target_platforms,
        limit=request.limit,
    )

    match_responses = [
        MatchResponse(
            source_url=m.source_url,
            target_url=m.target_url,
            target_platform=m.target_platform.value,
            score=m.score,
            confidence=m.confidence,
            match_type=m.match_type,
            result=MatchResult(
                name=m.target_result.name,
                artists=list(m.target_result.artists),
                artist=m.target_result.artist,
                duration=m.target_result.duration,
                platform=m.target_result.platform.value,
                platform_id=m.target_result.platform_id,
                url=m.target_result.url,
                album_name=m.target_result.album_name,
                cover_url=m.target_result.cover_url,
                views=m.target_result.views,
                explicit=m.target_result.explicit,
                verified=m.target_result.verified,
            ),
        )
        for m in matches
    ]

    return FindMatchesResponse(
        source_url=str(request.source_url),
        matches=match_responses,
        total=len(match_responses),
    )


@router.get("/find")
async def find_matches_get(
    source_url: Annotated[str, Query(description="Source URL to find matches for")],
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
    target_platforms: Annotated[
        list[str] | None, Query(description="Target platforms")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=20, description="Maximum matches")] = 5,
) -> FindMatchesResponse:
    """
    Find matches for a source URL (GET version).

    Uses user's audio source preferences to determine which platforms to search
    and in what order. Unauthenticated users get default platform order.

    Args:
        source_url: Source URL to find matches for
        preferences: User's provider preferences
        target_platforms: Optional list of target platforms
        limit: Maximum number of matches to return

    Returns:
        List of matches sorted by score
    """
    request = FindMatchesRequest(
        source_url=source_url,
        target_platforms=target_platforms,
        limit=limit,
    )
    return await find_matches(request, preferences)


@router.post("/submit")
async def submit_match(
    request: SubmitMatchRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> SubmitMatchResponse:
    """
    Submit a user-discovered match.

    Requires authentication.

    Args:
        request: Source and target URLs
        db: Database session
        user_id: Current user ID from auth

    Returns:
        Submitted match info
    """
    match_repo = MatchRepository(db)

    # Detect target platform
    target_url = str(request.target_url)
    target_platform = detect_target_platform(target_url)

    if target_platform is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported target platform. Supported: youtube, youtube_music, soundcloud, bandcamp, piped",
        )

    # Detect source platform
    source_url = str(request.source_url)
    source_platform = detect_platform(source_url)
    if source_platform is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported source platform",
        )

    # Check if match already exists
    existing = await match_repo.get_by_source_and_target(
        source_url=source_url,
        target_platform=target_platform,
        target_url=target_url,
    )

    if existing:
        return SubmitMatchResponse(
            id=str(existing.id),
            source_url=source_url,
            target_url=target_url,
            target_platform=target_platform,
            match_type=existing.match_type,
            message="Match already exists.",
        )

    # Create new match
    match = await match_repo.create(
        source_platform=source_platform.value,
        source_url=source_url,
        target_platform=target_platform,
        target_url=target_url,
        match_type=MatchType.USER,
        submitted_by=user_id,
    )

    # Award reputation for submitting a match
    user_repo = UserRepository(db)
    await user_repo.update_reputation(user_id, ReputationReward.MATCH_SUBMITTED)
    await db.commit()

    return SubmitMatchResponse(
        id=str(match.id),
        source_url=source_url,
        target_url=target_url,
        target_platform=target_platform,
        match_type="user",
        message="Match submitted successfully. It will be available after verification.",
    )


@router.get("/platforms")
async def get_target_platforms() -> dict[str, list[str]]:
    """Get list of supported target platforms."""
    match_service = get_match_service()
    return {
        "platforms": [p.value for p in match_service.supported_platforms],
    }
