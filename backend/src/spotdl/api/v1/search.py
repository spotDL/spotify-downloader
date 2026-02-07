"""Universal search API endpoint."""

from __future__ import annotations

import asyncio
import logging
import re
from enum import Enum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.core.services.entity import EntityPersistenceService
from spotdl.core.services.song import (
    SongServiceError,
    UnsupportedURLError,
    get_song_service,
)
from spotdl.core.types.song import Platform
from spotdl.db.database import get_db_session
from spotdl.db.repositories.album import AlbumRepository
from spotdl.db.repositories.artist import ArtistRepository
from spotdl.providers.sources import detect_platform

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search")

# URL patterns for detection
URL_PATTERN = re.compile(
    r"^https?://|"
    r"^spotify:|"
    r"^open\.spotify\.com|"
    r"^music\.youtube\.com|"
    r"^youtube\.com|"
    r"^youtu\.be|"
    r"^deezer\.com|"
    r"^music\.apple\.com|"
    r"^tidal\.com|"
    r"^soundcloud\.com|"
    r"^bandcamp\.com"
)


class EntityType(str, Enum):
    """Type of entity."""

    ARTIST = "artist"
    ALBUM = "album"
    PLAYLIST = "playlist"
    TRACK = "track"
    ALL = "all"


class PlatformInfo(BaseModel):
    """Platform link information."""

    platform: str
    platform_id: str
    url: str


class SearchResult(BaseModel):
    """A single search result with internal ID."""

    id: str  # Internal UUID
    entity_type: EntityType
    name: str
    subtitle: str | None = None  # Artist for albums/tracks, owner for playlists
    image_url: str | None = None
    platforms: list[PlatformInfo] = []
    duration: int | None = None  # For tracks


class SearchResponse(BaseModel):
    """Response for universal search."""

    query: str
    query_type: str  # "url" or "text"
    results: list[SearchResult]
    entities_created: int = 0
    total: int = 0


class SearchRequest(BaseModel):
    """Request model for search."""

    query: str
    entity_types: list[EntityType] | None = None
    limit: int = 20


# Platforms that support search
SEARCHABLE_PLATFORMS = [
    Platform.SPOTIFY,
    Platform.YOUTUBE_MUSIC,
    Platform.DEEZER,
    Platform.SOUNDCLOUD,
]


def _platform_links_to_info(links) -> list[PlatformInfo]:
    """Convert platform links to response model."""
    return [
        PlatformInfo(
            platform=link.platform,
            platform_id=link.platform_id,
            url=link.platform_url,
        )
        for link in (links or [])
    ]


def is_url(query: str) -> bool:
    """Check if the query looks like a URL."""
    return bool(URL_PATTERN.match(query.lower().strip()))


@router.post("")
async def universal_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    """
    Universal search endpoint that handles both URLs and text queries.

    - URLs: Resolve and persist the entity
    - Text: Search across platforms and persist results

    Returns internal IDs for all entities.
    """
    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    entity_service = EntityPersistenceService(db)
    song_service = get_song_service()

    # Determine if this is a URL or text search
    if is_url(query):
        return await _search_url(query, entity_service, song_service)
    else:
        return await _search_text(
            query,
            entity_service,
            song_service,
            entity_types=request.entity_types,
            limit=request.limit,
        )


@router.get("")
async def universal_search_get(
    q: Annotated[str, Query(description="Search query (URL or text)")],
    type: Annotated[
        EntityType | None, Query(description="Entity type filter")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="Maximum results")] = 20,
    db: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    """
    Universal search (GET method for simple queries).

    - URLs: Resolve and persist the entity
    - Text: Search across platforms and persist results
    """
    query = q.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    entity_service = EntityPersistenceService(db)
    song_service = get_song_service()

    entity_types = [type] if type and type != EntityType.ALL else None

    if is_url(query):
        return await _search_url(query, entity_service, song_service)
    else:
        return await _search_text(
            query,
            entity_service,
            song_service,
            entity_types=entity_types,
            limit=limit,
        )


async def _search_url(
    url: str,
    entity_service: EntityPersistenceService,
    song_service,
) -> SearchResponse:
    """Handle URL resolution and persistence."""
    try:
        # Detect platform and entity type from URL
        platform = detect_platform(url)

        if platform is None:
            raise HTTPException(status_code=400, detail=f"Unsupported URL: {url}")

        # Resolve the URL to get songs
        songs = await song_service.resolve_url(url)

        if not songs:
            return SearchResponse(
                query=url,
                query_type="url",
                results=[],
                entities_created=0,
                total=0,
            )

        # Persist entities and get internal IDs
        # Note: Enrichment is deferred to entity page load for better search performance
        persist_result = await entity_service.persist_from_search(songs)

        # Build results based on what was resolved
        results: list[SearchResult] = []

        # Group results by unique entities
        seen_artists: set[str] = set()
        seen_albums: set[str] = set()
        artist_repo = ArtistRepository(entity_service.session)
        album_repo = AlbumRepository(entity_service.session)
        artist_cache: dict[str, Any] = {}
        album_cache: dict[str, Any] = {}

        for song in songs:
            # Add track result
            song_key = f"{song.platform.value}:{song.platform_id}"
            song_id = persist_result.song_ids.get(song_key)

            if song_id:
                results.append(
                    SearchResult(
                        id=str(song_id),
                        entity_type=EntityType.TRACK,
                        name=song.name,
                        subtitle=song.artist,
                        image_url=song.cover_url,
                        platforms=[
                            PlatformInfo(
                                platform=song.platform.value,
                                platform_id=song.platform_id,
                                url=song.url,
                            )
                        ],
                        duration=song.duration,
                    )
                )

            # Add artist result (deduplicated)
            if song.artists:
                artist_normalized = EntityPersistenceService.normalize_name(
                    song.artists[0]
                )
                if artist_normalized not in seen_artists:
                    artist_id = persist_result.artist_ids.get(artist_normalized)
                    if artist_id:
                        seen_artists.add(artist_normalized)
                        artist = artist_cache.get(str(artist_id))
                        if artist is None:
                            try:
                                artist = await artist_repo.get_by_id_with_links(artist_id)
                            except Exception:
                                artist = None
                            artist_cache[str(artist_id)] = artist
                        results.insert(
                            0,  # Artists first
                            SearchResult(
                                id=str(artist_id),
                                entity_type=EntityType.ARTIST,
                                name=song.artists[0],
                                subtitle=None,
                                image_url=getattr(artist, "image_url", None) if artist else None,
                                platforms=_platform_links_to_info(
                                    getattr(artist, "platform_links", [])
                                )
                                if artist
                                else [],
                            ),
                        )

            # Add album result (deduplicated)
            if song.album_name:
                album_key = f"{artist_normalized}:{EntityPersistenceService.normalize_name(song.album_name)}"
                if album_key not in seen_albums:
                    album_id = persist_result.album_ids.get(album_key)
                    if album_id:
                        seen_albums.add(album_key)
                        album = album_cache.get(str(album_id))
                        if album is None:
                            try:
                                album = await album_repo.get_by_id_with_links(album_id)
                            except Exception:
                                album = None
                            album_cache[str(album_id)] = album
                        results.insert(
                            len(seen_artists),  # Albums after artists
                            SearchResult(
                                id=str(album_id),
                                entity_type=EntityType.ALBUM,
                                name=song.album_name,
                                subtitle=song.artist,
                                image_url=getattr(album, "cover_url", None) if album else song.cover_url,
                                platforms=_platform_links_to_info(
                                    getattr(album, "platform_links", [])
                                )
                                if album
                                else [],
                            ),
                        )

        return SearchResponse(
            query=url,
            query_type="url",
            results=results,
            entities_created=persist_result.total_created,
            total=len(results),
        )

    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SongServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _search_text(
    query: str,
    entity_service: EntityPersistenceService,
    song_service,
    entity_types: list[EntityType] | None = None,
    limit: int = 20,
) -> SearchResponse:
    """Handle text-based search across platforms."""
    # Search on primary platform (Spotify by default)
    try:
        # Search all platforms in parallel
        async def search_platform(platform: Platform) -> list:
            try:
                results = await song_service.search(query, platform=platform, limit=limit)
                logger.debug(f"Search on {platform.value} returned {len(results)} results")
                return results
            except Exception as e:
                logger.warning(f"Search failed on {platform.value}: {e}")
                return []

        # Run searches in parallel
        platform_results = await asyncio.gather(
            *[search_platform(p) for p in SEARCHABLE_PLATFORMS]
        )

        # Flatten results and remove duplicates
        all_songs = []
        seen_isrcs: set[str] = set()
        seen_keys: set[str] = set()

        for songs in platform_results:
            for song in songs:
                # Deduplicate by ISRC if available
                if song.isrc and song.isrc in seen_isrcs:
                    continue
                if song.isrc:
                    seen_isrcs.add(song.isrc)

                # Fallback deduplication by name+artist
                key = f"{song.name.lower()}|{song.artist.lower()}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                all_songs.append(song)

        # Limit total results
        all_songs = all_songs[:limit]

        logger.debug(f"Text search for '{query}' found {len(all_songs)} songs after deduplication")

        if not all_songs:
            logger.info(f"Text search for '{query}' returned no results from any platform")
            return SearchResponse(
                query=query,
                query_type="text",
                results=[],
                entities_created=0,
                total=0,
            )

        # Persist entities - enrichment is deferred to entity page load for better search performance
        persist_result = await entity_service.persist_from_search(all_songs)

        logger.debug(
            f"Persist result: {persist_result.songs_created} songs created, "
            f"{persist_result.songs_linked} linked, {len(persist_result.song_ids)} IDs mapped"
        )

        # Build results
        results: list[SearchResult] = []
        seen_artists: set[str] = set()
        seen_albums: set[str] = set()
        artist_repo = ArtistRepository(entity_service.session)
        album_repo = AlbumRepository(entity_service.session)
        artist_cache: dict[str, Any] = {}
        album_cache: dict[str, Any] = {}

        # Filter by entity type if specified
        include_tracks = (
            entity_types is None
            or EntityType.TRACK in entity_types
            or EntityType.ALL in entity_types
        )
        include_artists = (
            entity_types is None
            or EntityType.ARTIST in entity_types
            or EntityType.ALL in entity_types
        )
        include_albums = (
            entity_types is None
            or EntityType.ALBUM in entity_types
            or EntityType.ALL in entity_types
        )

        for song in all_songs:
            # Add artist (deduplicated)
            if include_artists and song.artists:
                artist_normalized = EntityPersistenceService.normalize_name(
                    song.artists[0]
                )
                if artist_normalized not in seen_artists:
                    artist_id = persist_result.artist_ids.get(artist_normalized)
                    if artist_id:
                        seen_artists.add(artist_normalized)
                        artist = artist_cache.get(str(artist_id))
                        if artist is None:
                            try:
                                artist = await artist_repo.get_by_id_with_links(artist_id)
                            except Exception:
                                artist = None
                            artist_cache[str(artist_id)] = artist
                        results.append(
                            SearchResult(
                                id=str(artist_id),
                                entity_type=EntityType.ARTIST,
                                name=song.artists[0],
                                subtitle=None,
                                image_url=getattr(artist, "image_url", None) if artist else None,
                                platforms=_platform_links_to_info(
                                    getattr(artist, "platform_links", [])
                                )
                                if artist
                                else [],
                            )
                        )

            # Add album (deduplicated)
            if include_albums and song.album_name:
                artist_norm = (
                    EntityPersistenceService.normalize_name(song.artists[0])
                    if song.artists
                    else ""
                )
                album_key = f"{artist_norm}:{EntityPersistenceService.normalize_name(song.album_name)}"
                if album_key not in seen_albums:
                    album_id = persist_result.album_ids.get(album_key)
                    if album_id:
                        seen_albums.add(album_key)
                        album = album_cache.get(str(album_id))
                        if album is None:
                            try:
                                album = await album_repo.get_by_id_with_links(album_id)
                            except Exception:
                                album = None
                            album_cache[str(album_id)] = album
                        results.append(
                            SearchResult(
                                id=str(album_id),
                                entity_type=EntityType.ALBUM,
                                name=song.album_name,
                                subtitle=song.artist,
                                image_url=getattr(album, "cover_url", None) if album else song.cover_url,
                                platforms=_platform_links_to_info(
                                    getattr(album, "platform_links", [])
                                )
                                if album
                                else [],
                            )
                        )

            # Add track
            if include_tracks:
                song_key = f"{song.platform.value}:{song.platform_id}"
                song_id = persist_result.song_ids.get(song_key)

                if song_id:
                    results.append(
                        SearchResult(
                            id=str(song_id),
                            entity_type=EntityType.TRACK,
                            name=song.name,
                            subtitle=song.artist,
                            image_url=song.cover_url,
                            platforms=[
                                PlatformInfo(
                                    platform=song.platform.value,
                                    platform_id=song.platform_id,
                                    url=song.url,
                                )
                            ],
                            duration=song.duration,
                        )
                    )

        return SearchResponse(
            query=query,
            query_type="text",
            results=results,
            entities_created=persist_result.total_created,
            total=len(results),
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}") from e
