"""Match finding API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from spotdl.core.services.match import get_match_service
from spotdl.core.services.song import (
    SongServiceError,
    UnsupportedURLError,
    get_song_service,
)
from spotdl.core.types.result import TargetPlatform

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


@router.post("/find")
async def find_matches(request: FindMatchesRequest) -> FindMatchesResponse:
    """
    Find matches for a source URL on target platforms.

    Args:
        request: Source URL and optional target platforms

    Returns:
        List of matches sorted by score
    """
    song_service = get_song_service()
    match_service = get_match_service()

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
    target_platforms: Annotated[
        list[str] | None, Query(description="Target platforms")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=20, description="Maximum matches")] = 5,
) -> FindMatchesResponse:
    """
    Find matches for a source URL (GET version).

    Args:
        source_url: Source URL to find matches for
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
    return await find_matches(request)


@router.post("/submit")
async def submit_match(request: SubmitMatchRequest) -> SubmitMatchResponse:
    """
    Submit a user-discovered match.

    This endpoint requires authentication (to be implemented).

    Args:
        request: Source and target URLs

    Returns:
        Submitted match info
    """
    # TODO: Add authentication check
    # TODO: Store match in database

    # For now, detect the target platform
    from spotdl.providers.sources import detect_platform

    target_platform = None
    target_url = str(request.target_url)

    # Check against target platforms (YouTube, etc)
    if "youtube.com" in target_url or "youtu.be" in target_url:
        if "music.youtube.com" in target_url:
            target_platform = "youtube_music"
        else:
            target_platform = "youtube"
    elif "soundcloud.com" in target_url:
        target_platform = "soundcloud"
    elif "bandcamp.com" in target_url:
        target_platform = "bandcamp"
    elif "piped" in target_url:
        target_platform = "piped"
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported target platform. Supported: youtube, youtube_music, soundcloud, bandcamp, piped",
        )

    # Generate a temporary ID
    import uuid

    match_id = str(uuid.uuid4())

    return SubmitMatchResponse(
        id=match_id,
        source_url=str(request.source_url),
        target_url=str(request.target_url),
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
