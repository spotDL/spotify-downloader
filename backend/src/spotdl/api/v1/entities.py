"""Entity API endpoints for internal ID-based access."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from spotdl.core.services.entity import EntityPersistenceService
from spotdl.core.services.song import get_song_service
from spotdl.db.database import get_db_session
from spotdl.db.models.album import Album
from spotdl.db.models.artist import Artist
from spotdl.db.models.playlist import Playlist
from spotdl.db.models.song import Song
from spotdl.db.repositories.album import AlbumRepository
from spotdl.db.repositories.artist import ArtistRepository
from spotdl.db.repositories.playlist import PlaylistRepository
from spotdl.db.repositories.song import SongRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entities")


class PlatformInfo(BaseModel):
    """Platform link information."""

    platform: str
    platform_id: str
    url: str
    followers: int | None = None


class AudioFeatures(BaseModel):
    """Audio features from Spotify."""

    bpm: float | None = None
    energy: float | None = None
    danceability: float | None = None
    valence: float | None = None
    key: int | None = None
    mode: int | None = None
    loudness: float | None = None
    speechiness: float | None = None
    acousticness: float | None = None
    instrumentalness: float | None = None
    liveness: float | None = None
    time_signature: int | None = None


class SongResponse(BaseModel):
    """Response model for a song entity."""

    id: str  # Internal UUID
    name: str
    artists: list[str]
    artist: str
    artist_id: str | None = None
    duration: int
    album_name: str | None = None
    album_id: str | None = None
    cover_url: str | None = None
    isrc: str | None = None
    year: int | None = None
    platforms: list[PlatformInfo] = []
    # Enhanced fields for song detail page
    audio_features: AudioFeatures | None = None
    popularity: int | None = None
    explicit: bool = False
    release_date: str | None = None
    label: str | None = None
    copyright_text: str | None = None
    genres: list[str] = []
    matches_count: int = 0
    track_number: int | None = None
    disc_number: int | None = None

    model_config = {"from_attributes": True}


class ArtistResponse(BaseModel):
    """Response model for an artist entity."""

    id: str  # Internal UUID
    name: str
    image_url: str | None = None
    genres: list[str] = []
    platforms: list[PlatformInfo] = []
    albums: list["AlbumSummary"] = []
    songs: list[SongResponse] = []
    total_albums: int = 0
    total_songs: int = 0


class AlbumSummary(BaseModel):
    """Summary of an album for artist response."""

    id: str
    name: str
    cover_url: str | None = None
    year: int | None = None
    total_tracks: int = 0


class AlbumResponse(BaseModel):
    """Response model for an album entity."""

    id: str  # Internal UUID
    name: str
    artist_name: str
    artist_id: str | None = None
    cover_url: str | None = None
    year: int | None = None
    total_tracks: int = 0
    platforms: list[PlatformInfo] = []
    songs: list[SongResponse] = []


class PlaylistResponse(BaseModel):
    """Response model for a playlist entity."""

    id: str  # Internal UUID
    name: str
    owner_name: str | None = None
    description: str | None = None
    cover_url: str | None = None
    total_tracks: int = 0
    platforms: list[PlatformInfo] = []
    songs: list[SongResponse] = []


# Forward reference resolution
ArtistResponse.model_rebuild()


def _song_to_response(song: Song, include_enhanced: bool = False) -> SongResponse:
    """Convert a Song model to SongResponse."""
    # Extract metadata from JSON if available
    metadata = song.metadata_json or {}
    cover_url = metadata.get("cover_url")
    year = metadata.get("year")
    track_number = metadata.get("track_number")
    disc_number = metadata.get("disc_number")

    response = SongResponse(
        id=str(song.id),
        name=song.name,
        artists=song.artists,
        artist=song.artists[0] if song.artists else "Unknown Artist",
        artist_id=str(song.artist_id) if song.artist_id else None,
        duration=song.duration_seconds,
        album_name=song.album_name,
        album_id=str(song.album_id) if song.album_id else None,
        cover_url=cover_url,
        isrc=song.isrc,
        year=year,
        platforms=[
            PlatformInfo(
                platform=song.platform,
                platform_id=song.platform_id,
                url=song.platform_url,
            )
        ],
    )

    # Add enhanced fields for detail pages
    if include_enhanced:
        response.popularity = song.popularity
        response.explicit = song.explicit or False
        response.release_date = str(song.release_date) if song.release_date else None
        response.label = song.label
        response.copyright_text = song.copyright_text
        response.genres = song.genres or []
        response.track_number = track_number
        response.disc_number = disc_number

        # Build audio features if any exist
        if any([
            song.bpm, song.energy, song.danceability, song.valence,
            song.key is not None, song.mode is not None, song.loudness,
            song.speechiness, song.acousticness, song.instrumentalness,
            song.liveness, song.time_signature
        ]):
            response.audio_features = AudioFeatures(
                bpm=float(song.bpm) if song.bpm else None,
                energy=float(song.energy) if song.energy else None,
                danceability=float(song.danceability) if song.danceability else None,
                valence=float(song.valence) if song.valence else None,
                key=song.key,
                mode=song.mode,
                loudness=float(song.loudness) if song.loudness else None,
                speechiness=float(song.speechiness) if song.speechiness else None,
                acousticness=float(song.acousticness) if song.acousticness else None,
                instrumentalness=float(song.instrumentalness) if song.instrumentalness else None,
                liveness=float(song.liveness) if song.liveness else None,
                time_signature=song.time_signature,
            )

    return response


@router.get("/artists/{id}")
async def get_artist(
    id: Annotated[str, Path(description="Internal artist UUID")],
    db: AsyncSession = Depends(get_db_session),
) -> ArtistResponse:
    """
    Get an artist by internal UUID.

    Returns artist details with all platform links, albums, and songs.
    """
    try:
        artist_uuid = uuid.UUID(id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid UUID format") from e

    artist_repo = ArtistRepository(db)
    artist = await artist_repo.get_by_id_with_links(artist_uuid)

    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    # Get albums for this artist
    album_repo = AlbumRepository(db)
    albums = await album_repo.get_by_artist_id(artist_uuid)

    # Get songs for this artist
    from sqlalchemy import select

    query = select(Song).where(Song.artist_id == artist_uuid).limit(100)
    result = await db.execute(query)
    songs = result.scalars().all()

    return ArtistResponse(
        id=str(artist.id),
        name=artist.name,
        image_url=artist.image_url,
        genres=artist.genres or [],
        platforms=[
            PlatformInfo(
                platform=link.platform,
                platform_id=link.platform_id,
                url=link.platform_url,
                followers=link.followers,
            )
            for link in artist.platform_links
        ],
        albums=[
            AlbumSummary(
                id=str(album.id),
                name=album.name,
                cover_url=album.cover_url,
                year=album.year,
                total_tracks=album.total_tracks,
            )
            for album in albums
        ],
        songs=[_song_to_response(song) for song in songs],
        total_albums=len(albums),
        total_songs=len(songs),
    )


@router.get("/albums/{id}")
async def get_album(
    id: Annotated[str, Path(description="Internal album UUID")],
    db: AsyncSession = Depends(get_db_session),
) -> AlbumResponse:
    """
    Get an album by internal UUID.

    Returns album details with all platform links and songs.
    """
    try:
        album_uuid = uuid.UUID(id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid UUID format") from e

    album_repo = AlbumRepository(db)
    album = await album_repo.get_by_id_with_links(album_uuid)

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Get songs for this album
    from sqlalchemy import select

    query = select(Song).where(Song.album_id == album_uuid).limit(100)
    result = await db.execute(query)
    songs = result.scalars().all()

    # Use actual song count if stored total_tracks is 0
    total_tracks = album.total_tracks if album.total_tracks > 0 else len(songs)

    return AlbumResponse(
        id=str(album.id),
        name=album.name,
        artist_name=album.artist_name,
        artist_id=str(album.artist_id) if album.artist_id else None,
        cover_url=album.cover_url,
        year=album.year,
        total_tracks=total_tracks,
        platforms=[
            PlatformInfo(
                platform=link.platform,
                platform_id=link.platform_id,
                url=link.platform_url,
            )
            for link in album.platform_links
        ],
        songs=[_song_to_response(song) for song in songs],
    )


@router.get("/songs/{id}")
async def get_song(
    id: Annotated[str, Path(description="Internal song UUID")],
    db: AsyncSession = Depends(get_db_session),
) -> SongResponse:
    """
    Get a song by internal UUID.

    Returns enhanced song details including audio features, popularity, and metadata.
    """
    try:
        song_uuid = uuid.UUID(id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid UUID format") from e

    song_repo = SongRepository(db)
    song = await song_repo.get_by_id(song_uuid)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Return enhanced response with all metadata for song detail page
    return _song_to_response(song, include_enhanced=True)


@router.get("/playlists/{id}")
async def get_playlist(
    id: Annotated[str, Path(description="Internal playlist UUID")],
    db: AsyncSession = Depends(get_db_session),
) -> PlaylistResponse:
    """
    Get a playlist by internal UUID.

    Returns playlist details with all platform links and songs.
    """
    try:
        playlist_uuid = uuid.UUID(id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid UUID format") from e

    playlist_repo = PlaylistRepository(db)
    playlist = await playlist_repo.get_by_id_with_tracks(playlist_uuid)

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return PlaylistResponse(
        id=str(playlist.id),
        name=playlist.name,
        owner_name=playlist.owner_name,
        description=playlist.description,
        cover_url=playlist.cover_url,
        total_tracks=playlist.total_tracks,
        platforms=[
            PlatformInfo(
                platform=link.platform,
                platform_id=link.platform_id,
                url=link.platform_url,
                followers=link.followers,
            )
            for link in playlist.platform_links
        ],
        songs=[_song_to_response(track.song) for track in playlist.tracks],
    )


# Legacy redirects - find by platform and redirect to internal ID


@router.get("/artists/platform/{platform}/{platform_id}")
async def get_artist_by_platform(
    platform: Annotated[str, Path(description="Platform name")],
    platform_id: Annotated[str, Path(description="Platform-specific ID")],
    db: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    """
    Find an artist by platform ID and redirect to internal ID endpoint.

    If the artist doesn't exist, attempts to fetch and create it.
    """
    artist_repo = ArtistRepository(db)
    artist = await artist_repo.get_by_platform_id(platform, platform_id)

    if artist:
        return RedirectResponse(
            url=f"/api/v1/entities/artists/{artist.id}",
            status_code=307,
        )

    # Artist not found - try to fetch from provider
    # Build URL based on platform
    url = _build_platform_url(platform, "artist", platform_id)
    if not url:
        raise HTTPException(status_code=404, detail="Artist not found")

    try:
        song_service = get_song_service()
        song_list = await song_service.get_artist(url)

        if not song_list.songs:
            raise HTTPException(status_code=404, detail="Artist not found")

        # Persist the artist
        entity_service = EntityPersistenceService(db)

        # Get artist info from first song
        first_song = song_list.songs[0]
        artist_name = first_song.artists[0] if first_song.artists else "Unknown"

        artist, _ = await entity_service.find_or_create_artist(
            name=artist_name,
            platform=platform,
            platform_id=platform_id,
            platform_url=url,
        )

        # Persist songs
        await entity_service.persist_from_search(song_list.songs)
        await db.commit()

        return RedirectResponse(
            url=f"/api/v1/entities/artists/{artist.id}",
            status_code=307,
        )

    except Exception as e:
        logger.error(f"Failed to fetch artist: {e}")
        raise HTTPException(status_code=404, detail="Artist not found") from e


@router.get("/albums/platform/{platform}/{platform_id}")
async def get_album_by_platform(
    platform: Annotated[str, Path(description="Platform name")],
    platform_id: Annotated[str, Path(description="Platform-specific ID")],
    db: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    """
    Find an album by platform ID and redirect to internal ID endpoint.
    """
    album_repo = AlbumRepository(db)
    album = await album_repo.get_by_platform_id(platform, platform_id)

    if album:
        return RedirectResponse(
            url=f"/api/v1/entities/albums/{album.id}",
            status_code=307,
        )

    # Album not found - try to fetch from provider
    url = _build_platform_url(platform, "album", platform_id)
    if not url:
        raise HTTPException(status_code=404, detail="Album not found")

    try:
        song_service = get_song_service()
        song_list = await song_service.get_album(url)

        if not song_list.songs:
            raise HTTPException(status_code=404, detail="Album not found")

        # Persist the album and songs
        entity_service = EntityPersistenceService(db)

        first_song = song_list.songs[0]
        artist_name = first_song.artists[0] if first_song.artists else "Unknown"

        album, _ = await entity_service.find_or_create_album(
            name=song_list.name,
            artist_name=artist_name,
            platform=platform,
            platform_id=platform_id,
            platform_url=url,
            cover_url=first_song.cover_url,
            year=first_song.year,
            total_tracks=len(song_list.songs),
        )

        await entity_service.persist_from_search(song_list.songs)
        await db.commit()

        return RedirectResponse(
            url=f"/api/v1/entities/albums/{album.id}",
            status_code=307,
        )

    except Exception as e:
        logger.error(f"Failed to fetch album: {e}")
        raise HTTPException(status_code=404, detail="Album not found") from e


@router.get("/playlists/platform/{platform}/{platform_id}")
async def get_playlist_by_platform(
    platform: Annotated[str, Path(description="Platform name")],
    platform_id: Annotated[str, Path(description="Platform-specific ID")],
    db: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    """
    Find a playlist by platform ID and redirect to internal ID endpoint.
    """
    playlist_repo = PlaylistRepository(db)
    playlist = await playlist_repo.get_by_platform_id(platform, platform_id)

    if playlist:
        return RedirectResponse(
            url=f"/api/v1/entities/playlists/{playlist.id}",
            status_code=307,
        )

    # Playlist not found - try to fetch from provider
    url = _build_platform_url(platform, "playlist", platform_id)
    if not url:
        raise HTTPException(status_code=404, detail="Playlist not found")

    try:
        song_service = get_song_service()
        song_list = await song_service.get_playlist(url)

        if not song_list.songs:
            raise HTTPException(status_code=404, detail="Playlist not found")

        # Persist the playlist
        entity_service = EntityPersistenceService(db)

        playlist, _ = await entity_service.find_or_create_playlist(
            name=song_list.name,
            platform=platform,
            platform_id=platform_id,
            platform_url=url,
            total_tracks=len(song_list.songs),
        )

        # Persist songs and add to playlist
        persist_result = await entity_service.persist_from_search(song_list.songs)

        # Add tracks to playlist
        for i, song in enumerate(song_list.songs):
            song_key = f"{song.platform.value}:{song.platform_id}"
            song_id = persist_result.song_ids.get(song_key)
            if song_id:
                from spotdl.db.repositories.playlist import PlaylistRepository

                playlist_repo = PlaylistRepository(db)
                await playlist_repo.add_track(playlist.id, song_id, i)

        await db.commit()

        return RedirectResponse(
            url=f"/api/v1/entities/playlists/{playlist.id}",
            status_code=307,
        )

    except Exception as e:
        logger.error(f"Failed to fetch playlist: {e}")
        raise HTTPException(status_code=404, detail="Playlist not found") from e


@router.get("/songs/platform/{platform}/{platform_id}")
async def get_song_by_platform(
    platform: Annotated[str, Path(description="Platform name")],
    platform_id: Annotated[str, Path(description="Platform-specific ID")],
    db: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    """
    Find a song by platform ID and redirect to internal ID endpoint.
    """
    song_repo = SongRepository(db)
    song = await song_repo.get_by_platform_id(platform, platform_id)

    if song:
        return RedirectResponse(
            url=f"/api/v1/entities/songs/{song.id}",
            status_code=307,
        )

    # Song not found - try to fetch from provider
    url = _build_platform_url(platform, "track", platform_id)
    if not url:
        raise HTTPException(status_code=404, detail="Song not found")

    try:
        song_service = get_song_service()
        track = await song_service.get_track(url)

        # Persist the song
        entity_service = EntityPersistenceService(db)
        song_model, _ = await entity_service.persist_song(track)
        await db.commit()

        return RedirectResponse(
            url=f"/api/v1/entities/songs/{song_model.id}",
            status_code=307,
        )

    except Exception as e:
        logger.error(f"Failed to fetch song: {e}")
        raise HTTPException(status_code=404, detail="Song not found") from e


def _build_platform_url(platform: str, entity_type: str, platform_id: str) -> str | None:
    """Build a platform-specific URL for an entity."""
    platform = platform.lower()

    if platform == "spotify":
        return f"https://open.spotify.com/{entity_type}/{platform_id}"
    elif platform == "deezer":
        return f"https://www.deezer.com/{entity_type}/{platform_id}"
    elif platform == "youtube_music":
        if entity_type == "track":
            return f"https://music.youtube.com/watch?v={platform_id}"
        elif entity_type == "album":
            return f"https://music.youtube.com/browse/{platform_id}"
        elif entity_type == "playlist":
            return f"https://music.youtube.com/playlist?list={platform_id}"
        elif entity_type == "artist":
            return f"https://music.youtube.com/channel/{platform_id}"
    elif platform == "soundcloud":
        # SoundCloud URLs are more complex, would need the full URL
        return None
    elif platform == "apple_music":
        # Apple Music URLs need more info
        return None
    elif platform == "tidal":
        return f"https://tidal.com/{entity_type}/{platform_id}"
    elif platform == "bandcamp":
        # Bandcamp URLs are domain-based
        return None

    return None
