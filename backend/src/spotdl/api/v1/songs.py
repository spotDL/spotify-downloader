"""Song resolution API endpoints."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.core.services.song import (
    SongServiceError,
    UnsupportedURLError,
    get_song_service,
)
from spotdl.core.types.song import Platform
from spotdl.db.database import get_db_session
from spotdl.db.models.match import Match, MatchType
from spotdl.db.repositories.match import MatchRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/songs")

# Platforms that support search (some may require credentials)
SEARCHABLE_PLATFORMS = [
    Platform.YOUTUBE_MUSIC,
    Platform.SOUNDCLOUD,
    Platform.DEEZER,
    Platform.SPOTIFY,
]


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


class PlatformSearchResult(BaseModel):
    """Search results for a single platform."""

    platform: str
    platform_name: str
    songs: list[SongResponse]
    total: int
    error: str | None = None


class MultiPlatformSearchResponse(BaseModel):
    """Response model for multi-platform search."""

    query: str
    results: list[PlatformSearchResult]
    total_results: int
    matches_saved: int


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


PLATFORM_DISPLAY_NAMES = {
    Platform.SPOTIFY: "Spotify",
    Platform.YOUTUBE_MUSIC: "YouTube Music",
    Platform.DEEZER: "Deezer",
    Platform.SOUNDCLOUD: "SoundCloud",
    Platform.BANDCAMP: "Bandcamp",
    Platform.APPLE_MUSIC: "Apple Music",
    Platform.TIDAL: "Tidal",
}


async def _search_platform(
    service,
    query: str,
    platform: Platform,
    limit: int,
) -> PlatformSearchResult:
    """Search a single platform and return results."""
    try:
        songs = await service.search(query, platform=platform, limit=limit)

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

        return PlatformSearchResult(
            platform=platform.value,
            platform_name=PLATFORM_DISPLAY_NAMES.get(platform, platform.value),
            songs=song_responses,
            total=len(song_responses),
        )

    except SongServiceError as e:
        logger.warning(f"Search failed on {platform.value}: {e}")
        return PlatformSearchResult(
            platform=platform.value,
            platform_name=PLATFORM_DISPLAY_NAMES.get(platform, platform.value),
            songs=[],
            total=0,
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error searching {platform.value}: {e}")
        return PlatformSearchResult(
            platform=platform.value,
            platform_name=PLATFORM_DISPLAY_NAMES.get(platform, platform.value),
            songs=[],
            total=0,
            error=f"Search unavailable: {type(e).__name__}",
        )


async def _save_cross_platform_matches(
    db: AsyncSession,
    results: list[PlatformSearchResult],
) -> int:
    """
    Save cross-platform matches to the database.

    When the same song appears on multiple platforms (matched by name + artist),
    we create match records linking them together.
    """
    matches_saved = 0
    match_repo = MatchRepository(db)

    # Group songs by normalized key (lowercase name + artist)
    song_groups: dict[str, list[tuple[str, SongResponse]]] = {}

    for result in results:
        if result.error:
            continue
        for song in result.songs:
            # Create a normalized key for matching
            key = f"{song.name.lower().strip()}|{song.artist.lower().strip()}"
            if key not in song_groups:
                song_groups[key] = []
            song_groups[key].append((result.platform, song))

    # For groups with songs from multiple platforms, create matches
    for key, songs in song_groups.items():
        if len(songs) < 2:
            continue

        # Create matches between all platform pairs
        for i, (source_platform, source_song) in enumerate(songs):
            for target_platform, target_song in songs[i + 1:]:
                # Check if match already exists
                existing = await match_repo.get_by_source_and_target(
                    source_url=source_song.url,
                    target_platform=target_platform,
                    target_url=target_song.url,
                )
                if existing:
                    continue

                # Create match record (source -> target)
                try:
                    await match_repo.create(
                        source_platform=source_platform,
                        source_url=source_song.url,
                        target_platform=target_platform,
                        target_url=target_song.url,
                        match_type=MatchType.SYSTEM,
                        match_score=85.0,  # High score for name+artist match
                    )
                    matches_saved += 1
                    logger.debug(
                        f"Saved match: {source_song.url} -> {target_song.url}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to save match: {e}")

                # Also create reverse match (target -> source)
                existing_reverse = await match_repo.get_by_source_and_target(
                    source_url=target_song.url,
                    target_platform=source_platform,
                    target_url=source_song.url,
                )
                if not existing_reverse:
                    try:
                        await match_repo.create(
                            source_platform=target_platform,
                            source_url=target_song.url,
                            target_platform=source_platform,
                            target_url=source_song.url,
                            match_type=MatchType.SYSTEM,
                            match_score=85.0,
                        )
                        matches_saved += 1
                    except Exception as e:
                        logger.warning(f"Failed to save reverse match: {e}")

    await db.commit()
    return matches_saved


@router.get("/search/all")
async def search_all_platforms(
    query: Annotated[str, Query(description="Search query")],
    limit: Annotated[int, Query(ge=1, le=20, description="Results per platform")] = 10,
    db: AsyncSession = Depends(get_db_session),
) -> MultiPlatformSearchResponse:
    """
    Search for songs across all available platforms in parallel.

    Returns results grouped by platform. Also saves cross-platform matches
    to the database when the same song is found on multiple platforms.
    """
    service = get_song_service()

    # Search all platforms in parallel
    search_tasks = [
        _search_platform(service, query, platform, limit)
        for platform in SEARCHABLE_PLATFORMS
    ]

    results = await asyncio.gather(*search_tasks, return_exceptions=False)

    # Filter out None results and sort by total (most results first)
    valid_results = [r for r in results if r is not None]
    valid_results.sort(key=lambda x: x.total, reverse=True)

    # Calculate total results
    total_results = sum(r.total for r in valid_results)

    # Save cross-platform matches to database
    matches_saved = 0
    try:
        matches_saved = await _save_cross_platform_matches(db, valid_results)
        if matches_saved > 0:
            logger.info(f"Saved {matches_saved} cross-platform matches for query: {query}")
    except Exception as e:
        logger.error(f"Failed to save matches: {e}")

    return MultiPlatformSearchResponse(
        query=query,
        results=valid_results,
        total_results=total_results,
        matches_saved=matches_saved,
    )
