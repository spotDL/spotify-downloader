"""Match finding API endpoints."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urljoin, urlparse
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from spotdl.api.v1.auth import get_current_user_id, get_current_user_id_optional
from spotdl.api.v1.dependencies import UserPreferences, get_user_preferences
from spotdl.api.v1.votes import calculate_wilson_score
from spotdl.core.reputation import ReputationReward
from spotdl.core.services.entity import EntityPersistenceService
from spotdl.core.services.match import get_match_service
from spotdl.core.services.song import (
    SongServiceError,
    UnsupportedURLError,
    get_song_service,
)
from spotdl.core.types.result import TargetPlatform
from spotdl.core.types.song import Platform, Song
from spotdl.db.database import get_db_session
from spotdl.db.models.match import Match, MatchType
from spotdl.db.repositories.match import MatchRepository
from spotdl.db.repositories.user import UserRepository
from spotdl.db.repositories.vote import VoteRepository
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
    song_id: str | None = None
    description: str | None = None
    site_name: str | None = None
    resolved_via: str | None = None


class MatchResponse(BaseModel):
    """Response model for a match."""

    id: str | None = None
    source_url: str
    source_song_id: str | None = None
    source_platform: str | None = None
    target_url: str
    target_song_id: str | None = None
    target_platform: str
    score: float
    confidence: float
    match_type: str
    status: str | None = None
    upvotes: int | None = None
    downvotes: int | None = None
    net_votes: int | None = None
    submitted_by_username: str | None = None
    verified_by_username: str | None = None
    result: MatchResult


class MatchDetailResponse(BaseModel):
    """Detailed match response for UI consumption."""

    id: str
    source_url: str
    source_song_id: str | None = None
    source_platform: str
    target_url: str
    target_song_id: str | None = None
    target_platform: str
    score: float
    confidence: float
    match_type: str
    status: str
    result: MatchResult
    upvotes: int
    downvotes: int
    net_votes: int
    created_at: str
    submitted_by_username: str | None = None
    verified_by_username: str | None = None
    message: str | None = None


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


class MatchPreviewResponse(BaseModel):
    """Response model for previewing a target match URL."""

    target_url: str
    target_platform: str
    result: MatchResult


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


class MatchVoteSummaryResponse(BaseModel):
    """Vote summary for a match."""

    match_id: UUID
    upvotes: int
    downvotes: int
    score: int
    total_votes: int
    confidence: float
    user_vote: str | None = None


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


def _result_from_song(song) -> MatchResult:
    """Convert a Song object to MatchResult."""
    return MatchResult(
        name=getattr(song, "name", "Unknown"),
        artists=list(getattr(song, "artists", []) or []),
        artist=getattr(song, "artist", "Unknown"),
        duration=int(getattr(song, "duration", 0) or 0),
        platform=getattr(getattr(song, "platform", ""), "value", None)
        or getattr(song, "platform", "")
        or "unknown",
        platform_id=getattr(song, "platform_id", ""),
        url=getattr(song, "url", ""),
        album_name=getattr(song, "album_name", None),
        cover_url=getattr(song, "cover_url", None),
        views=getattr(song, "views", None),
        explicit=bool(getattr(song, "explicit", False)),
        verified=bool(getattr(song, "verified", False)),
        description=None,
        site_name=None,
        resolved_via="provider",
    )


def _extract_meta_tag(soup: BeautifulSoup, *keys: str) -> str | None:
    """Extract first matching meta tag content by property/name."""
    for key in keys:
        tag = soup.find("meta", attrs={"property": key})
        if tag and tag.get("content"):
            return str(tag.get("content")).strip() or None
        tag = soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            return str(tag.get("content")).strip() or None
    return None


async def _fetch_open_graph(url: str) -> dict[str, str | None] | None:
    """Fetch basic Open Graph metadata for a URL."""
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; SpotDLBot/1.0; "
                    "+https://github.com/spotDL/spotify-downloader)"
                )
            },
        ) as client:
            response = await client.get(url)
    except Exception:
        return None

    if response.status_code >= 400 or not response.text:
        return None

    try:
        soup = BeautifulSoup(response.text, "lxml")
    except Exception:
        return None

    title = _extract_meta_tag(soup, "og:title", "twitter:title")
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip() or None

    description = _extract_meta_tag(soup, "og:description", "twitter:description", "description")
    site_name = _extract_meta_tag(soup, "og:site_name")
    image = _extract_meta_tag(soup, "og:image", "twitter:image")

    if image:
        image = urljoin(str(response.url), image)

    if not title and not description and not site_name and not image:
        return None

    return {
        "title": title,
        "description": description,
        "site_name": site_name,
        "image": image,
    }


async def _resolve_match_result(
    target_url: str,
    target_platform: str,
    song_service,
) -> MatchResult:
    """Resolve target URL details via provider first, then Open Graph fallback."""
    try:
        songs = await song_service.resolve_url(target_url)
        if songs:
            return _result_from_song(songs[0])
    except Exception:
        pass

    og_data = await _fetch_open_graph(target_url)
    if og_data is not None:
        hostname = urlparse(target_url).hostname or ""
        source_name = og_data.get("site_name") or hostname.replace("www.", "") or "Unknown"
        title = og_data.get("title") or "Unknown"
        return MatchResult(
            name=title,
            artists=[source_name] if source_name != "Unknown" else [],
            artist=source_name,
            duration=0,
            platform=target_platform,
            platform_id="",
            url=target_url,
            album_name=None,
            cover_url=og_data.get("image"),
            views=None,
            explicit=False,
            verified=False,
            description=og_data.get("description"),
            site_name=og_data.get("site_name"),
            resolved_via="open_graph",
        )

    return MatchResult(
        name="Unknown",
        artists=[],
        artist="Unknown",
        duration=0,
        platform=target_platform,
        platform_id="",
        url=target_url,
        album_name=None,
        cover_url=None,
        views=None,
        explicit=False,
        verified=False,
        description=None,
        site_name=None,
        resolved_via="fallback",
    )


def _target_result_to_song(result) -> Song | None:
    """Convert a target Result into a persistable Song DTO when possible."""
    platform_map: dict[TargetPlatform, Platform] = {
        TargetPlatform.YOUTUBE: Platform.YOUTUBE_MUSIC,
        TargetPlatform.YOUTUBE_MUSIC: Platform.YOUTUBE_MUSIC,
        TargetPlatform.PIPED: Platform.YOUTUBE_MUSIC,
        TargetPlatform.SOUNDCLOUD: Platform.SOUNDCLOUD,
        TargetPlatform.BANDCAMP: Platform.BANDCAMP,
    }
    mapped_platform = platform_map.get(result.platform)
    if mapped_platform is None:
        return None

    source_url = result.url
    if result.platform in {TargetPlatform.YOUTUBE, TargetPlatform.PIPED}:
        source_url = f"https://music.youtube.com/watch?v={result.platform_id}"

    return Song(
        name=result.name,
        artists=list(result.artists),
        artist=result.artist,
        duration=result.duration,
        platform=mapped_platform,
        platform_id=result.platform_id,
        url=source_url,
        album_name=result.album_name or "",
        cover_url=result.cover_url,
        explicit=bool(result.explicit),
    )


async def _match_to_detail(
    match: Match,
    song_service,
    *,
    message: str | None = None,
) -> MatchDetailResponse:
    """Convert a Match DB row to a detailed response."""
    score = float(match.match_score) if match.match_score is not None else 0.0
    confidence = max(0.0, min(1.0, score / 100.0))
    result = await _resolve_match_result(match.target_url, match.target_platform, song_service)

    return MatchDetailResponse(
        id=str(match.id),
        source_url=match.source_url,
        source_song_id=str(match.source_song_id) if match.source_song_id else None,
        source_platform=match.source_platform,
        target_url=match.target_url,
        target_song_id=None,
        target_platform=match.target_platform,
        score=score,
        confidence=confidence,
        match_type=match.match_type,
        status=getattr(match, "status", "pending"),
        result=result,
        upvotes=match.upvotes,
        downvotes=match.downvotes,
        net_votes=match.net_votes,
        created_at=match.created_at.isoformat(),
        submitted_by_username=(
            match.submitted_by_user.username if match.submitted_by_user else None
        ),
        verified_by_username=(
            match.verified_by_user.username if match.verified_by_user else None
        ),
        message=message,
    )


@router.post("/find")
async def find_matches(
    request: FindMatchesRequest,
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
    db: AsyncSession = Depends(get_db_session),
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
    entity_service = EntityPersistenceService(db)
    match_repo = MatchRepository(db)

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

    # Persist source entity so downstream consumers always get internal IDs.
    source_song_id: str | None = None
    try:
        persist_result = await entity_service.persist_from_search([song])
        source_key = f"{song.platform.value}:{song.platform_id}"
        source_id = persist_result.song_ids.get(source_key)
        source_song_id = str(source_id) if source_id else None
        await db.flush()
    except Exception:
        source_song_id = None

    # Find matches
    matches = await match_service.find_matches(
        song,
        target_platforms=target_platforms,
        limit=request.limit,
    )

    # Persist target entities for platforms that map to source Song platforms.
    target_song_id_by_url: dict[str, str] = {}
    target_songs: list[tuple[str, Song]] = []
    for matched in matches:
        target_song = _target_result_to_song(matched.target_result)
        if target_song is not None:
            target_songs.append((matched.target_result.url, target_song))

    if target_songs:
        try:
            target_persist = await entity_service.persist_from_search(
                [song_obj for _, song_obj in target_songs]
            )
            for original_url, target_song in target_songs:
                key = f"{target_song.platform.value}:{target_song.platform_id}"
                target_id = target_persist.song_ids.get(key)
                if target_id:
                    target_song_id_by_url[original_url] = str(target_id)
            await db.flush()
        except Exception:
            target_song_id_by_url = {}

    source_platform = detect_platform(song.url)
    source_platform_value = source_platform.value if source_platform else song.platform.value
    source_song_uuid: UUID | None = None
    if source_song_id:
        try:
            source_song_uuid = UUID(source_song_id)
        except ValueError:
            source_song_uuid = None
    persisted_matches: dict[tuple[str, str], Match] = {}

    for matched in matches:
        target_platform_value = matched.target_platform.value
        existing_match = await match_repo.get_by_source_and_target(
            source_url=matched.source_url,
            target_platform=target_platform_value,
            target_url=matched.target_url,
        )

        if existing_match is not None:
            if source_song_uuid is not None and existing_match.source_song_id is None:
                existing_match.source_song_id = source_song_uuid
            if existing_match.source_platform != source_platform_value:
                existing_match.source_platform = source_platform_value
            if existing_match.match_type != MatchType.USER:
                existing_match.match_type = MatchType.SYSTEM
                existing_match.match_score = matched.score
            persisted = existing_match
        else:
            persisted = await match_repo.create(
                source_song_id=source_song_uuid,
                source_platform=source_platform_value,
                source_url=matched.source_url,
                target_platform=target_platform_value,
                target_url=matched.target_url,
                match_type=MatchType.SYSTEM,
                match_score=matched.score,
            )

        persisted_matches[(target_platform_value, matched.target_url)] = persisted

    await db.flush()

    match_responses: list[MatchResponse] = []
    for m in matches:
        persisted = persisted_matches.get((m.target_platform.value, m.target_url))
        match_responses.append(
            MatchResponse(
                id=str(persisted.id) if persisted else None,
                source_url=m.source_url,
                source_song_id=source_song_id,
                source_platform=source_platform_value,
                target_url=m.target_url,
                target_song_id=target_song_id_by_url.get(m.target_url),
                target_platform=m.target_platform.value,
                score=m.score,
                confidence=m.confidence,
                match_type=persisted.match_type if persisted else m.match_type,
                status=persisted.status if persisted else None,
                upvotes=persisted.upvotes if persisted else 0,
                downvotes=persisted.downvotes if persisted else 0,
                net_votes=persisted.net_votes if persisted else 0,
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
                    song_id=target_song_id_by_url.get(m.target_result.url),
                    description=None,
                    site_name=None,
                    resolved_via="provider",
                ),
            )
        )

    return FindMatchesResponse(
        source_url=str(request.source_url),
        matches=match_responses,
        total=len(match_responses),
    )


@router.get("/find")
async def find_matches_get(
    source_url: Annotated[str, Query(description="Source URL to find matches for")],
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
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
    return await find_matches(request, preferences, db)


@router.get("/preview", response_model=MatchPreviewResponse)
async def preview_match_url(
    target_url: Annotated[str, Query(description="Target URL to preview")],
) -> MatchPreviewResponse:
    """Preview metadata for a target link using provider parsing and OG fallback."""
    target_platform = detect_target_platform(target_url)
    if target_platform is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported target platform. Supported: youtube, youtube_music, "
                "soundcloud, bandcamp, piped"
            ),
        )

    song_service = get_song_service()
    result = await _resolve_match_result(target_url, target_platform, song_service)
    return MatchPreviewResponse(
        target_url=target_url,
        target_platform=target_platform,
        result=result,
    )


@router.post("/submit", response_model=MatchDetailResponse)
async def submit_match(
    request: SubmitMatchRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> MatchDetailResponse:
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
        song_service = get_song_service()
        return await _match_to_detail(
            existing,
            song_service,
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

    song_service = get_song_service()
    return await _match_to_detail(
        match,
        song_service,
        message="Match submitted successfully. It will be available after verification.",
    )


@router.get("/platforms")
async def get_target_platforms() -> dict[str, list[str]]:
    """Get list of supported target platforms."""
    match_service = get_match_service()
    return {
        "platforms": [p.value for p in match_service.supported_platforms],
    }


@router.get("/{match_id}", response_model=MatchDetailResponse)
async def get_match(
    match_id: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MatchDetailResponse:
    """Get a single match by ID."""
    try:
        match_uuid = UUID(match_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid match ID: {match_id}") from e

    query = (
        select(Match)
        .options(
            selectinload(Match.submitted_by_user),
            selectinload(Match.verified_by_user),
        )
        .where(Match.id == match_uuid)
    )
    result = await db.execute(query)
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    song_service = get_song_service()
    return await _match_to_detail(match, song_service)


@router.get("/{match_id}/votes", response_model=MatchVoteSummaryResponse)
async def get_match_votes(
    match_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[UUID | None, Depends(get_current_user_id_optional)] = None,
) -> MatchVoteSummaryResponse:
    """Get vote summary for a match (legacy alias)."""
    match_repo = MatchRepository(db)
    vote_repo = VoteRepository(db)

    match = await match_repo.get_by_id(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    user_vote = None
    if user_id:
        vote = await vote_repo.get_user_vote(match_id=match_id, user_id=user_id)
        if vote:
            user_vote = vote.vote_type.value

    confidence = calculate_wilson_score(match.upvotes, match.downvotes)

    return MatchVoteSummaryResponse(
        match_id=match_id,
        upvotes=match.upvotes,
        downvotes=match.downvotes,
        score=match.upvotes - match.downvotes,
        total_votes=match.upvotes + match.downvotes,
        confidence=confidence,
        user_vote=user_vote,
    )
