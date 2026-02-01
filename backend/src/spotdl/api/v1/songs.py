"""Song resolution API endpoints."""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
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


# Entity types and response models
class EntityType(str, Enum):
    """Type of entity (artist, album, playlist, track)."""

    ARTIST = "artist"
    ALBUM = "album"
    PLAYLIST = "playlist"
    TRACK = "track"


class ArtistResponse(BaseModel):
    """Response model for an artist entity."""

    id: str
    name: str
    platform: str
    url: str
    image_url: str | None = None
    genres: list[str] = []
    followers: int | None = None
    songs: list[SongResponse] = []
    total_songs: int = 0


class AlbumResponse(BaseModel):
    """Response model for an album entity."""

    id: str
    name: str
    platform: str
    url: str
    artist_name: str
    cover_url: str | None = None
    release_date: str | None = None
    year: int | None = None
    total_tracks: int = 0
    songs: list[SongResponse] = []


class PlaylistResponse(BaseModel):
    """Response model for a playlist entity."""

    id: str
    name: str
    platform: str
    url: str
    description: str | None = None
    owner_name: str | None = None
    cover_url: str | None = None
    total_tracks: int = 0
    songs: list[SongResponse] = []


class EntitySearchResult(BaseModel):
    """Search result for an entity (artist, album, playlist, or track)."""

    entity_type: EntityType
    id: str
    name: str
    platform: str
    url: str
    image_url: str | None = None
    subtitle: str | None = None  # Artist for albums, owner for playlists


class EntitySearchResponse(BaseModel):
    """Response model for entity search."""

    query: str
    entity_type: EntityType | None
    results: list[EntitySearchResult]
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


def _song_to_response(song) -> SongResponse:
    """Convert a song object to SongResponse."""
    return SongResponse(
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


# Entity endpoints
@router.get("/entities/artist/{platform}/{entity_id}")
async def get_artist(
    platform: Annotated[str, Path(description="Platform (spotify, youtube_music, etc.)")],
    entity_id: Annotated[str, Path(description="Artist ID on the platform")],
) -> ArtistResponse:
    """
    Get artist details including their discography.

    Returns artist metadata and list of songs.
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
        # Build artist URL based on platform
        artist_url = _build_entity_url(platform_enum, "artist", entity_id)
        songs = await service.resolve_url(artist_url)

        song_responses = [_song_to_response(song) for song in songs]

        # Extract artist info from first song
        artist_name = song_responses[0].artist if song_responses else "Unknown Artist"
        genres = song_responses[0].genres if song_responses else []
        image_url = song_responses[0].cover_url if song_responses else None

        return ArtistResponse(
            id=entity_id,
            name=artist_name,
            platform=platform,
            url=artist_url,
            image_url=image_url,
            genres=genres,
            songs=song_responses,
            total_songs=len(song_responses),
        )

    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SongServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/entities/album/{platform}/{entity_id}")
async def get_album(
    platform: Annotated[str, Path(description="Platform (spotify, youtube_music, etc.)")],
    entity_id: Annotated[str, Path(description="Album ID on the platform")],
) -> AlbumResponse:
    """
    Get album details including tracklist.

    Returns album metadata and list of tracks.
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
        album_url = _build_entity_url(platform_enum, "album", entity_id)
        songs = await service.resolve_url(album_url)

        song_responses = [_song_to_response(song) for song in songs]

        # Extract album info from first song
        first = song_responses[0] if song_responses else None
        album_name = first.album_name if first else "Unknown Album"
        artist_name = first.artist if first else "Unknown Artist"
        cover_url = first.cover_url if first else None
        year = first.year if first else None
        date = first.date if first else None

        return AlbumResponse(
            id=entity_id,
            name=album_name,
            platform=platform,
            url=album_url,
            artist_name=artist_name,
            cover_url=cover_url,
            release_date=date,
            year=year,
            total_tracks=len(song_responses),
            songs=song_responses,
        )

    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SongServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/entities/playlist/{platform}/{entity_id}")
async def get_playlist(
    platform: Annotated[str, Path(description="Platform (spotify, youtube_music, etc.)")],
    entity_id: Annotated[str, Path(description="Playlist ID on the platform")],
) -> PlaylistResponse:
    """
    Get playlist details including tracks.

    Returns playlist metadata and list of tracks.
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
        playlist_url = _build_entity_url(platform_enum, "playlist", entity_id)
        songs = await service.resolve_url(playlist_url)

        song_responses = [_song_to_response(song) for song in songs]

        # For playlists, we don't have owner info from songs
        cover_url = song_responses[0].cover_url if song_responses else None

        return PlaylistResponse(
            id=entity_id,
            name="Playlist",  # Would need additional API call to get actual name
            platform=platform,
            url=playlist_url,
            cover_url=cover_url,
            total_tracks=len(song_responses),
            songs=song_responses,
        )

    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SongServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/entities/track/{platform}/{entity_id}")
async def get_track(
    platform: Annotated[str, Path(description="Platform (spotify, youtube_music, etc.)")],
    entity_id: Annotated[str, Path(description="Track ID on the platform")],
) -> SongResponse:
    """
    Get track details.

    Returns full track metadata.
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
        track_url = _build_entity_url(platform_enum, "track", entity_id)
        songs = await service.resolve_url(track_url)

        if not songs:
            raise HTTPException(status_code=404, detail="Track not found")

        return _song_to_response(songs[0])

    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SongServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/search/entities")
async def search_entities(
    query: Annotated[str, Query(description="Search query")],
    entity_type: Annotated[
        EntityType | None,
        Query(description="Entity type to search for (artist, album, playlist, track)"),
    ] = None,
    platform: Annotated[str, Query(description="Platform to search")] = "spotify",
    limit: Annotated[int, Query(ge=1, le=50, description="Maximum results")] = 10,
) -> EntitySearchResponse:
    """
    Search for entities (artists, albums, playlists, tracks) on a platform.

    If entity_type is not specified, returns mixed results of all types.
    Currently falls back to song search since most platforms don't have
    separate entity search APIs accessible through spotdl.
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
        # Search songs and extract unique entities from results.
        # Most platforms don't expose dedicated entity search APIs, so we derive
        # albums and artists from song metadata to provide unified entity search.
        songs = await service.search(query, platform=platform_enum, limit=limit * 3)

        results: list[EntitySearchResult] = []
        seen_ids: set[str] = set()

        for song in songs:
            song_resp = _song_to_response(song)

            # Add as track result
            if entity_type is None or entity_type == EntityType.TRACK:
                track_id = f"track:{song_resp.platform_id}"
                if track_id not in seen_ids:
                    seen_ids.add(track_id)
                    results.append(
                        EntitySearchResult(
                            entity_type=EntityType.TRACK,
                            id=song_resp.platform_id,
                            name=song_resp.name,
                            platform=song_resp.platform,
                            url=song_resp.url,
                            image_url=song_resp.cover_url,
                            subtitle=song_resp.artist,
                        )
                    )

            # Extract album as entity
            if song_resp.album_id and (entity_type is None or entity_type == EntityType.ALBUM):
                album_id = f"album:{song_resp.album_id}"
                if album_id not in seen_ids and song_resp.album_name:
                    seen_ids.add(album_id)
                    album_url = _build_entity_url(platform_enum, "album", song_resp.album_id)
                    results.append(
                        EntitySearchResult(
                            entity_type=EntityType.ALBUM,
                            id=song_resp.album_id,
                            name=song_resp.album_name,
                            platform=song_resp.platform,
                            url=album_url,
                            image_url=song_resp.cover_url,
                            subtitle=song_resp.artist,
                        )
                    )

            # Extract artist as entity (using artist name as pseudo-ID for search results)
            if entity_type is None or entity_type == EntityType.ARTIST:
                # Use artist name normalized as ID since we don't have actual artist IDs
                artist_key = song_resp.artist.lower().strip()
                artist_id = f"artist:{artist_key}"
                if artist_id not in seen_ids and song_resp.artist:
                    seen_ids.add(artist_id)
                    track_count = len([s for s in songs if s.artist.lower().strip() == artist_key])
                    # Artist IDs aren't consistently available from search APIs, so we use
                    # normalized artist names as identifiers and link to platform search pages
                    results.append(
                        EntitySearchResult(
                            entity_type=EntityType.ARTIST,
                            id=artist_key,  # Use normalized name as ID
                            name=song_resp.artist,
                            platform=song_resp.platform,
                            url=f"https://open.spotify.com/search/{song_resp.artist}/artists" if platform_enum == Platform.SPOTIFY else "",
                            image_url=song_resp.cover_url,  # Use album art as placeholder
                            subtitle=f"{track_count} tracks found",
                        )
                    )

        # Sort artist results by relevance (track count and query match)
        if entity_type == EntityType.ARTIST:
            query_lower = query.lower()
            results.sort(
                key=lambda r: (
                    # Prioritize exact query match in name
                    0 if query_lower in r.name.lower() else 1,
                    # Then by track count (extract from subtitle, descending)
                    -int(r.subtitle.split()[0]) if r.subtitle else 0,
                ),
            )

        # Limit results
        results = results[:limit]

        return EntitySearchResponse(
            query=query,
            entity_type=entity_type,
            results=results,
            total=len(results),
        )

    except SongServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def _build_entity_url(platform: Platform, entity_type: str, entity_id: str) -> str:
    """Build a platform-specific URL for an entity."""
    if platform == Platform.SPOTIFY:
        return f"https://open.spotify.com/{entity_type}/{entity_id}"
    elif platform == Platform.YOUTUBE_MUSIC:
        if entity_type == "track":
            return f"https://music.youtube.com/watch?v={entity_id}"
        elif entity_type == "album":
            return f"https://music.youtube.com/browse/{entity_id}"
        elif entity_type == "playlist":
            return f"https://music.youtube.com/playlist?list={entity_id}"
        elif entity_type == "artist":
            return f"https://music.youtube.com/channel/{entity_id}"
    elif platform == Platform.DEEZER:
        return f"https://www.deezer.com/{entity_type}/{entity_id}"
    elif platform == Platform.SOUNDCLOUD:
        # SoundCloud doesn't use simple IDs, this is a placeholder
        return f"https://soundcloud.com/{entity_id}"
    elif platform == Platform.BANDCAMP:
        return f"https://bandcamp.com/{entity_type}/{entity_id}"
    elif platform == Platform.APPLE_MUSIC:
        return f"https://music.apple.com/{entity_type}/{entity_id}"
    elif platform == Platform.TIDAL:
        return f"https://tidal.com/browse/{entity_type}/{entity_id}"

    # Fallback
    return f"https://{platform.value}.com/{entity_type}/{entity_id}"
