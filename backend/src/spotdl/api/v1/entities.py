"""Entity API endpoints for internal ID-based access."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from spotdl.api.v1.auth import get_current_user_optional
from spotdl.api.v1.dependencies import UserPreferences, get_user_preferences, get_embed_preferences
from spotdl.core.metadata_embed_config import MetadataEmbedPreferences
from spotdl.api.v1.validation import validate_uuid, UUIDPath, SkipQuery, LimitQuery
from spotdl.core.services.entity import EntityPersistenceService
from spotdl.core.services.song import SongServiceError, UnsupportedURLError, get_song_service
from spotdl.db.database import get_db_session
from spotdl.db.models.album import Album
from spotdl.db.models.artist import Artist
from spotdl.db.models.playlist import Playlist
from spotdl.db.models.song import Song
from spotdl.db.models.user import User
from spotdl.db.repositories.album import AlbumRepository
from spotdl.db.repositories.artist import ArtistRepository
from spotdl.db.repositories.playlist import PlaylistRepository
from spotdl.db.repositories.song import SongRepository
from spotdl.db.repositories.refresh_cooldown import RefreshCooldownRepository
from spotdl.db.models.metadata_snapshot import MetadataSnapshot

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
    # Enrichment tracking
    musicbrainz_id: str | None = None
    discogs_id: str | None = None
    field_sources: dict[str, str] | None = None
    enriched_at: str | None = None

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
    # Extended metadata
    monthly_listeners: int | None = None
    popularity: int | None = None
    bio: str | None = None
    origin_country: str | None = None
    origin_city: str | None = None
    formed_year: int | None = None
    external_urls: dict[str, str] | None = None


class AlbumSummary(BaseModel):
    """Summary of an album for artist response."""

    id: str
    name: str
    cover_url: str | None = None
    year: int | None = None
    total_tracks: int = 0
    album_type: str | None = None


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
    # Extended metadata
    album_type: str | None = None
    release_date: str | None = None
    label: str | None = None
    copyright_text: str | None = None
    popularity: int | None = None
    genres: list[str] = []


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
    # Extended metadata
    is_public: bool = True
    snapshot_id: str | None = None


# Forward reference resolution
ArtistResponse.model_rebuild()


def _normalize_name(name: str) -> str:
    """Normalize a song name for comparison."""
    import re
    # Remove parenthetical content, lowercase, remove extra whitespace
    name = re.sub(r'\([^)]*\)', '', name)
    name = re.sub(r'\[[^\]]*\]', '', name)
    name = name.lower().strip()
    name = re.sub(r'\s+', ' ', name)
    return name


def _deduplicate_album_songs(songs: list[Song]) -> list[Song]:
    """
    Deduplicate songs in an album by ISRC or normalized name.

    When the same track exists from multiple platforms (Spotify, YouTube, Deezer),
    we want to show it only once, preferring the version with the most metadata.

    Priority: Spotify > Deezer > Apple Music > YouTube Music > other
    """
    from collections import defaultdict

    # Platform priority (lower is better)
    platform_priority = {
        "spotify": 0,
        "deezer": 1,
        "apple_music": 2,
        "youtube_music": 3,
        "youtube": 4,
        "soundcloud": 5,
        "bandcamp": 6,
    }

    # Group songs by ISRC first
    isrc_groups: dict[str, list[Song]] = defaultdict(list)
    no_isrc: list[Song] = []

    for song in songs:
        if song.isrc:
            isrc_groups[song.isrc].append(song)
        else:
            no_isrc.append(song)

    # For songs without ISRC, group by normalized name + track number (if available)
    name_groups: dict[str, list[Song]] = defaultdict(list)
    for song in no_isrc:
        metadata = song.metadata_json or {}
        track_num = metadata.get("track_number", 0) or 0
        key = f"{_normalize_name(song.name)}:{track_num}"
        name_groups[key].append(song)

    # Select best song from each ISRC group
    deduped: list[Song] = []
    seen_names: set[str] = set()

    for isrc, group in isrc_groups.items():
        # Sort by platform priority, then by metadata richness
        group.sort(key=lambda s: (
            platform_priority.get(s.platform, 99),
            -(len(s.metadata_json or {})),  # More metadata is better
        ))
        best = group[0]
        deduped.append(best)
        seen_names.add(_normalize_name(best.name))

    # Select best song from each name group (if not already covered by ISRC)
    for key, group in name_groups.items():
        name_part = key.split(":")[0]
        if name_part in seen_names:
            continue  # Already have this song from ISRC group

        group.sort(key=lambda s: (
            platform_priority.get(s.platform, 99),
            -(len(s.metadata_json or {})),
        ))
        best = group[0]
        deduped.append(best)
        seen_names.add(name_part)

    # Sort by track number if available
    def sort_key(s: Song) -> tuple[int, int, str]:
        metadata = s.metadata_json or {}
        disc = metadata.get("disc_number", 1) or 1
        track = metadata.get("track_number", 999) or 999
        return (disc, track, s.name)

    deduped.sort(key=sort_key)

    return deduped


def _deduplicate_artist_songs(songs: list[Song]) -> list[Song]:
    """
    Deduplicate songs by ISRC or normalized name for artist pages.

    Similar to _deduplicate_album_songs but without track number grouping.
    """
    from collections import defaultdict

    platform_priority = {
        "spotify": 0,
        "deezer": 1,
        "apple_music": 2,
        "youtube_music": 3,
        "youtube": 4,
        "soundcloud": 5,
        "bandcamp": 6,
    }

    # Group songs by ISRC first
    isrc_groups: dict[str, list[Song]] = defaultdict(list)
    no_isrc: list[Song] = []

    for song in songs:
        if song.isrc:
            isrc_groups[song.isrc].append(song)
        else:
            no_isrc.append(song)

    # For songs without ISRC, group by normalized name
    name_groups: dict[str, list[Song]] = defaultdict(list)
    for song in no_isrc:
        key = _normalize_name(song.name)
        name_groups[key].append(song)

    # Select best song from each group
    deduped: list[Song] = []
    seen_names: set[str] = set()

    for isrc, group in isrc_groups.items():
        group.sort(key=lambda s: (
            platform_priority.get(s.platform, 99),
            -(len(s.metadata_json or {})),
        ))
        best = group[0]
        deduped.append(best)
        seen_names.add(_normalize_name(best.name))

    for key, group in name_groups.items():
        if key in seen_names:
            continue

        group.sort(key=lambda s: (
            platform_priority.get(s.platform, 99),
            -(len(s.metadata_json or {})),
        ))
        best = group[0]
        deduped.append(best)

    # Sort by name
    deduped.sort(key=lambda s: s.name.lower())

    return deduped


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

        # Enrichment tracking
        response.musicbrainz_id = song.musicbrainz_id
        response.discogs_id = song.discogs_id
        response.field_sources = song.field_sources
        response.enriched_at = song.enriched_at.isoformat() if song.enriched_at else None

    return response


def _build_song_snapshot_data(song: Song) -> dict[str, object]:
    """Build normalized snapshot data from a Song DB model."""
    metadata = song.metadata_json or {}
    snapshot_data: dict[str, object] = {
        "name": song.name,
        "artists": song.artists,
        "album_name": song.album_name,
        "isrc": song.isrc,
        "genres": song.genres or [],
        "year": song.release_date.year if song.release_date else metadata.get("year"),
        "release_date": str(song.release_date) if song.release_date else None,
        "explicit": song.explicit,
        "popularity": song.popularity,
        "label": song.label,
        "copyright_text": song.copyright_text,
        "track_number": metadata.get("track_number"),
        "disc_number": metadata.get("disc_number"),
        "musicbrainz_id": song.musicbrainz_id,
        "discogs_id": song.discogs_id,
    }

    if any([song.bpm, song.energy, song.danceability, song.valence]):
        snapshot_data.update({
            "bpm": float(song.bpm) if song.bpm else None,
            "energy": float(song.energy) if song.energy else None,
            "danceability": float(song.danceability) if song.danceability else None,
            "valence": float(song.valence) if song.valence else None,
            "key": song.key,
            "mode": song.mode,
            "loudness": float(song.loudness) if song.loudness else None,
            "speechiness": float(song.speechiness) if song.speechiness else None,
            "acousticness": float(song.acousticness) if song.acousticness else None,
            "instrumentalness": float(song.instrumentalness) if song.instrumentalness else None,
            "liveness": float(song.liveness) if song.liveness else None,
            "time_signature": song.time_signature,
        })

    return {k: v for k, v in snapshot_data.items() if v is not None}


async def _ensure_song_platform_snapshot(
    song: Song,
    db: AsyncSession,
) -> MetadataSnapshot:
    """Ensure the primary platform snapshot exists/up-to-date for a song."""
    from spotdl.db.repositories import MetadataSnapshotRepository

    snapshot_repo = MetadataSnapshotRepository(db)
    return await snapshot_repo.upsert(
        song_id=song.id,
        source=song.platform,
        snapshot_data=_build_song_snapshot_data(song),
        raw_response=None,
        confidence=1.0,
    )


def _apply_snapshot_to_song(song: Song, snapshot: MetadataSnapshot) -> list[str]:
    """Apply normalized snapshot data to song model and return updated field names."""
    data = snapshot.snapshot_data or {}
    updated_fields: list[str] = []
    field_sources = song.field_sources or {}

    if data.get("musicbrainz_id") and not song.musicbrainz_id:
        song.musicbrainz_id = str(data["musicbrainz_id"])
        field_sources["musicbrainz_id"] = snapshot.source
        updated_fields.append("musicbrainz_id")

    if data.get("discogs_id") and not song.discogs_id:
        song.discogs_id = str(data["discogs_id"])
        field_sources["discogs_id"] = snapshot.source
        updated_fields.append("discogs_id")

    if data.get("genres") and not song.genres:
        song.genres = list(data["genres"])
        field_sources["genres"] = snapshot.source
        updated_fields.append("genres")

    if data.get("label") and not song.label:
        song.label = str(data["label"])
        field_sources["label"] = snapshot.source
        updated_fields.append("label")

    if data.get("isrc") and not song.isrc:
        song.isrc = str(data["isrc"])
        field_sources["isrc"] = snapshot.source
        updated_fields.append("isrc")

    if not song.release_date and data.get("year"):
        try:
            song.release_date = date_type(int(data["year"]), 1, 1)
            field_sources["release_date"] = snapshot.source
            updated_fields.append("release_date")
        except (TypeError, ValueError):
            pass

    song.field_sources = field_sources
    return updated_fields


@router.get("/artists/{id}")
async def get_artist(
    id: Annotated[str, Path(description="Internal artist UUID")],
    db: AsyncSession = Depends(get_db_session),
) -> ArtistResponse:
    """
    Get an artist by internal UUID.

    Returns artist details with all platform links, albums, and songs.
    Automatically enriches with images/genres from Spotify if not already enriched.
    """
    artist_uuid = validate_uuid(id, "artist ID")

    artist_repo = ArtistRepository(db)
    artist = await artist_repo.get_by_id_with_links(artist_uuid)

    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    # Lazy enrichment: fetch Spotify data if artist lacks image/genres
    if not artist.image_url or not artist.genres:
        try:
            song_service = get_song_service()
            from spotdl.core.types.song import Platform
            import asyncio

            spotify_provider = song_service._providers.get(Platform.SPOTIFY)
            if spotify_provider:
                client = spotify_provider._get_client()
                loop = asyncio.get_event_loop()

                # First check if artist has a Spotify platform link
                spotify_artist_id = None
                for link in (artist.platform_links or []):
                    if link.platform == "spotify":
                        spotify_artist_id = link.platform_id
                        break

                # If no Spotify link, try to find Spotify artist ID from the artist's songs
                if not spotify_artist_id:
                    from sqlalchemy import select
                    song_query = (
                        select(Song)
                        .where(Song.artist_id == artist_uuid)
                        .where(Song.platform == "spotify")
                        .limit(1)
                    )
                    result = await db.execute(song_query)
                    spotify_song = result.scalars().first()

                    if spotify_song:
                        # Fetch track from Spotify to get artist ID
                        track_data = await loop.run_in_executor(
                            None, client.track, spotify_song.platform_id
                        )
                        if track_data and track_data.get("artists"):
                            spotify_artist_id = track_data["artists"][0].get("id")

                # Directly enrich from Spotify API using the artist ID
                if spotify_artist_id:
                    artist_data = await loop.run_in_executor(
                        None, client.artist, spotify_artist_id
                    )
                    if artist_data:
                        # Update image
                        images = artist_data.get("images", [])
                        if images and not artist.image_url:
                            sorted_images = sorted(
                                images,
                                key=lambda x: x.get("width", 0) * x.get("height", 0),
                                reverse=True,
                            )
                            artist.image_url = sorted_images[0].get("url")

                        # Update genres
                        genres = artist_data.get("genres", [])
                        if genres and not artist.genres:
                            artist.genres = genres

                        # Update followers count on Spotify link if it exists
                        followers = artist_data.get("followers", {}).get("total")
                        for link in (artist.platform_links or []):
                            if link.platform == "spotify" and followers:
                                link.followers = followers

                        await db.commit()
                        # Refresh artist
                        artist = await artist_repo.get_by_id_with_links(artist_uuid)

        except Exception as e:
            # Enrichment failed, continue with what we have
            logger.warning(f"Lazy artist enrichment failed: {e}")
            pass

    # Get albums for this artist
    album_repo = AlbumRepository(db)
    albums = await album_repo.get_by_artist_id(artist_uuid)

    # Get actual song counts for albums
    album_ids = [album.id for album in albums]
    song_counts = await album_repo.get_song_counts_by_album_ids(album_ids)

    # Get songs for this artist (no limit - return all songs)
    from sqlalchemy import select, func

    # First get total count
    count_query = select(func.count(Song.id)).where(Song.artist_id == artist_uuid)
    count_result = await db.execute(count_query)
    total_song_count = count_result.scalar() or 0

    # Get all songs (up to 500 to prevent excessive memory usage)
    query = select(Song).where(Song.artist_id == artist_uuid).limit(500)
    result = await db.execute(query)
    songs = result.scalars().all()

    # Deduplicate songs (same track from multiple platforms)
    deduped_songs = _deduplicate_artist_songs(songs)

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
                # Use actual song count from DB, fallback to stored total_tracks, then 0
                total_tracks=song_counts.get(album.id, album.total_tracks or 0),
                album_type=album.album_type,
            )
            for album in albums
        ],
        songs=[_song_to_response(song) for song in deduped_songs],
        total_albums=len(albums),
        total_songs=len(deduped_songs),  # Use deduplicated count
        # Extended metadata
        monthly_listeners=artist.monthly_listeners,
        popularity=artist.popularity,
        bio=artist.bio,
        origin_country=artist.origin_country,
        origin_city=artist.origin_city,
        formed_year=artist.formed_year,
        external_urls=artist.external_urls,
    )


@router.get("/albums/{id}")
async def get_album(
    id: Annotated[str, Path(description="Internal album UUID")],
    db: AsyncSession = Depends(get_db_session),
) -> AlbumResponse:
    """
    Get an album by internal UUID.

    Returns album details with all platform links and songs.
    Automatically fetches all tracks on first visit if album is incomplete.
    """
    album_uuid = validate_uuid(id, "album ID")

    album_repo = AlbumRepository(db)
    album = await album_repo.get_by_id_with_links(album_uuid)

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Get songs for this album (no artificial limit)
    from sqlalchemy import select

    query = select(Song).where(Song.album_id == album_uuid)
    result = await db.execute(query)
    songs = result.scalars().all()

    # Lazy enrichment: fetch all tracks if album appears incomplete
    # (has platform link but very few songs compared to what we'd expect)
    songs_count = len(songs)
    needs_enrichment = (
        album.platform_links
        and (songs_count == 0 or (album.total_tracks and songs_count < album.total_tracks * 0.5))
    )

    if needs_enrichment:
        try:
            song_service = get_song_service()
            song_list = None

            for link in album.platform_links:
                for candidate_url in _candidate_urls_for_link(link, "album"):
                    try:
                        song_list = await song_service.get_album(candidate_url)
                        if song_list.songs:
                            break
                    except Exception as e:
                        logger.debug(
                            "Album lazy enrichment candidate failed (%s): %s",
                            candidate_url,
                            e,
                        )
                if song_list and song_list.songs:
                    break

            if song_list and song_list.songs:
                entity_service = EntityPersistenceService(db)
                await entity_service.persist_from_search(song_list.songs)
                if len(song_list.songs) > (album.total_tracks or 0):
                    album.total_tracks = len(song_list.songs)
                await db.commit()
                # Re-fetch songs after enrichment
                result = await db.execute(query)
                songs = result.scalars().all()
        except Exception as e:
            # Enrichment failed, continue with what we have
            logger.warning(f"Lazy album enrichment failed: {e}")
            pass

    # Deduplicate songs by ISRC or normalized name
    # This handles cases where the same track exists from multiple platforms
    deduped_songs = _deduplicate_album_songs(songs)

    # Use actual song count from query result
    total_tracks = len(deduped_songs) if len(deduped_songs) > 0 else album.total_tracks

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
        songs=[_song_to_response(song) for song in deduped_songs],
        # Extended metadata
        album_type=album.album_type,
        release_date=str(album.release_date) if album.release_date else None,
        label=album.label,
        copyright_text=album.copyright_text,
        popularity=album.popularity,
        genres=album.genres or [],
    )


@router.get("/songs/{id}")
async def get_song(
    id: Annotated[str, Path(description="Internal song UUID")],
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
    db: AsyncSession = Depends(get_db_session),
) -> SongResponse:
    """
    Get a song by internal UUID.

    Returns enhanced song details including audio features, popularity, and metadata.
    Automatically enriches with MusicBrainz/Discogs data on first visit if not enriched.

    Uses user's metadata source preferences to determine enrichment provider order.
    Unauthenticated users get default provider order.
    """
    song_uuid = validate_uuid(id, "song ID")

    song_repo = SongRepository(db)
    song = await song_repo.get_by_id(song_uuid)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Lazy enrichment: fetch metadata snapshots from all configured providers
    # when we have never enriched this song.
    needs_enrichment = not song.enriched_at

    if needs_enrichment:
        try:
            from spotdl.core.services.metadata import MetadataService
            # Always capture/update the primary platform snapshot first.
            primary_snapshot = await _ensure_song_platform_snapshot(song, db)

            # Use MetadataService to fetch and save snapshots from other providers
            # Use user's metadata preferences if available
            metadata_service = MetadataService(
                metadata_preferences=preferences["metadata"],
            )

            # Fetch metadata from all providers and save snapshots
            snapshots = await metadata_service.fetch_all_snapshots(
                song_id=song_uuid,
                isrc=song.isrc,
                name=song.name,
                artist=song.artists[0] if song.artists else "",
                album_name=song.album_name,
                session=db,
            )

            # Update song from the highest-confidence snapshot among all sources.
            all_snapshots = [primary_snapshot, *snapshots]
            if all_snapshots:
                best_snapshot = max(all_snapshots, key=lambda s: s.confidence)
                _apply_snapshot_to_song(song, best_snapshot)

            song.enriched_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(song)

            logger.info(
                "Lazy song enrichment saved %d snapshots for %s",
                len(all_snapshots),
                song_uuid,
            )

        except Exception as e:
            # Enrichment failed, continue with what we have
            logger.warning(f"Lazy song enrichment failed: {e}")
            pass

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
    playlist_uuid = validate_uuid(id, "playlist ID")

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


class MetadataSnapshotResponse(BaseModel):
    """Response model for a metadata snapshot."""

    id: str
    source: str
    snapshot_data: dict
    raw_response: dict | None = None
    fetched_at: str
    confidence: float

    model_config = {"from_attributes": True}


class MetadataSourcesResponse(BaseModel):
    """Response model for all metadata sources for a song."""

    song_id: str
    sources: list[str]
    snapshots: list[MetadataSnapshotResponse]


@router.get("/songs/{song_id}/metadata-sources")
async def get_song_metadata_sources(
    song_id: Annotated[str, Path(description="Internal song UUID")],
    include_raw: Annotated[bool, Query(description="Include raw API responses")] = False,
    db: AsyncSession = Depends(get_db_session),
) -> MetadataSourcesResponse:
    """
    Get all available metadata sources for a song.

    Returns snapshots from different metadata providers (Spotify, MusicBrainz, Discogs, etc.)
    allowing users to view and compare metadata from multiple sources.

    Args:
        song_id: Internal song UUID
        include_raw: If true, includes the complete raw API responses (larger payload)
    """
    from sqlalchemy import select

    song_uuid = validate_uuid(song_id, "song ID")

    # Verify song exists
    song_repo = SongRepository(db)
    song = await song_repo.get_by_id(song_uuid)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Fetch all metadata snapshots for this song
    query = (
        select(MetadataSnapshot)
        .where(MetadataSnapshot.song_id == song_uuid)
        .order_by(MetadataSnapshot.confidence.desc())
    )
    result = await db.execute(query)
    snapshots = list(result.scalars().all())

    # If no snapshots exist, capture the primary platform snapshot so the UI
    # always has at least one concrete metadata source to display.
    if not snapshots:
        platform_snapshot = await _ensure_song_platform_snapshot(song, db)
        await db.commit()
        snapshots = [platform_snapshot]

    sources = sorted({s.source for s in snapshots})

    return MetadataSourcesResponse(
        song_id=str(song_uuid),
        sources=sources,
        snapshots=[
            MetadataSnapshotResponse(
                id=str(s.id),
                source=s.source,
                snapshot_data=s.snapshot_data,
                raw_response=s.raw_response if include_raw else None,
                fetched_at=s.fetched_at.isoformat(),
                confidence=s.confidence,
            )
            for s in snapshots
        ],
    )


class ResolvedFieldResponse(BaseModel):
    """Response model for a resolved metadata field."""

    field_id: str
    value: str | int | float | list | bool | None
    source: str | None
    enabled: bool


class ResolvedMetadataResponse(BaseModel):
    """Response model for resolved metadata."""

    song_id: str
    fields: dict[str, ResolvedFieldResponse]


@router.get("/songs/{song_id}/metadata-resolved")
async def get_song_resolved_metadata(
    song_id: Annotated[str, Path(description="Internal song UUID")],
    embed_preferences: Annotated[MetadataEmbedPreferences, Depends(get_embed_preferences)],
    db: AsyncSession = Depends(get_db_session),
) -> ResolvedMetadataResponse:
    """
    Get resolved metadata for a song using user's embed preferences.

    For each metadata field, returns the value from the highest-priority source
    that has data for that field, according to the user's configured preferences.

    Authenticated users get their custom field priorities applied.
    Unauthenticated users get default field priorities.

    This is the metadata that would be embedded when downloading the song.
    """
    from sqlalchemy import select
    from spotdl.core.services.metadata_resolver import MetadataResolver

    song_uuid = validate_uuid(song_id, "song ID")

    # Get song
    song_repo = SongRepository(db)
    song = await song_repo.get_by_id(song_uuid)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Fetch all metadata snapshots
    query = (
        select(MetadataSnapshot)
        .where(MetadataSnapshot.song_id == song_uuid)
    )
    result = await db.execute(query)
    snapshots = list(result.scalars().all())

    if not snapshots:
        platform_snapshot = await _ensure_song_platform_snapshot(song, db)
        await db.commit()
        snapshots = [platform_snapshot]

    # Resolve metadata using user's embed preferences
    resolver = MetadataResolver(preferences=embed_preferences)
    resolved = resolver.resolve_from_song(song, snapshots)

    return ResolvedMetadataResponse(
        song_id=str(song_uuid),
        fields={
            field_id: ResolvedFieldResponse(
                field_id=field_id,
                value=field.value,
                source=field.source,
                enabled=field.enabled,
            )
            for field_id, field in resolved.fields.items()
        },
    )


class RefreshResponse(BaseModel):
    """Response model for a refresh operation."""

    success: bool
    message: str
    cooldown_seconds: int | None = None  # Seconds until next refresh allowed


async def check_refresh_cooldown(
    entity_type: str,
    entity_id: uuid.UUID,
    user: User | None,
    db: AsyncSession,
) -> None:
    """
    Check if a refresh operation is on cooldown.

    Admins bypass cooldown. Non-admins must wait 4 hours between refreshes.

    Raises HTTPException with 429 status if on cooldown.
    """
    # Admins bypass cooldown
    if user and user.is_admin:
        return

    cooldown_repo = RefreshCooldownRepository(db)
    user_id = user.id if user else None

    is_on_cooldown, remaining_seconds = await cooldown_repo.is_on_cooldown(
        entity_type, entity_id, user_id
    )

    if is_on_cooldown:
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        raise HTTPException(
            status_code=429,
            detail=f"Refresh on cooldown. Try again in {hours}h {minutes}m.",
            headers={"Retry-After": str(remaining_seconds)},
        )


async def record_refresh_cooldown(
    entity_type: str,
    entity_id: uuid.UUID,
    user: User | None,
    db: AsyncSession,
) -> None:
    """Record a refresh action for cooldown tracking."""
    # Don't record cooldowns for admins
    if user and user.is_admin:
        return

    cooldown_repo = RefreshCooldownRepository(db)
    user_id = user.id if user else None
    await cooldown_repo.record_refresh(entity_type, entity_id, user_id)


def _raise_refresh_error(error: Exception) -> None:
    """Normalize provider/service refresh errors into actionable HTTP codes."""
    if isinstance(error, HTTPException):
        raise error

    detail = str(error)
    lowered = detail.lower()

    if isinstance(error, UnsupportedURLError) or "unsupported url" in lowered:
        status_code = 400
    elif "invalid" in lowered and "url" in lowered:
        status_code = 400
    elif "not found" in lowered:
        status_code = 404
    elif isinstance(error, SongServiceError):
        status_code = 502
    else:
        status_code = 500

    logger.error("Refresh failed (%s): %s", status_code, detail)
    raise HTTPException(status_code=status_code, detail=f"Failed to refresh: {detail}") from error


@router.post("/songs/{id}/refresh")
async def refresh_song(
    id: Annotated[str, Path(description="Internal song UUID")],
    db: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> RefreshResponse:
    """
    Refresh metadata for a song by fetching latest data from source.

    Cooldown: 4 hours for regular users, no limit for admins.
    """
    song_uuid = validate_uuid(id, "song ID")

    # Check cooldown (raises 429 if on cooldown)
    await check_refresh_cooldown("song", song_uuid, current_user, db)

    song_repo = SongRepository(db)
    song = await song_repo.get_by_id(song_uuid)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Use stored source URL first, then fallback to reconstructed URL.
    source_urls = []
    if song.platform_url and song.platform_url.strip():
        source_urls.append(song.platform_url.strip())
    rebuilt_url = _build_platform_url(song.platform, "track", song.platform_id)
    if rebuilt_url and rebuilt_url not in source_urls:
        source_urls.append(rebuilt_url)

    if not source_urls:
        raise HTTPException(status_code=400, detail="Cannot refresh from this platform")

    try:
        song_service = get_song_service()
        track = None
        for candidate_url in source_urls:
            try:
                track = await song_service.get_track(candidate_url)
                break
            except Exception as e:
                logger.debug("Song refresh candidate failed (%s): %s", candidate_url, e)

        if track is None:
            raise HTTPException(status_code=400, detail="Cannot refresh from this platform")

        # Update the existing song with fresh data
        entity_service = EntityPersistenceService(db)
        await entity_service.persist_song(
            track,
            artist_id=song.artist_id,
            album_id=song.album_id,
        )

        # Record cooldown
        await record_refresh_cooldown("song", song_uuid, current_user, db)

        await db.commit()

        return RefreshResponse(success=True, message="Song metadata refreshed successfully")
    except Exception as e:
        _raise_refresh_error(e)


@router.post("/albums/{id}/refresh")
async def refresh_album(
    id: Annotated[str, Path(description="Internal album UUID")],
    db: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> RefreshResponse:
    """
    Refresh metadata for an album by fetching latest data from source.

    Cooldown: 4 hours for regular users, no limit for admins.
    """
    album_uuid = validate_uuid(id, "album ID")

    # Check cooldown (raises 429 if on cooldown)
    await check_refresh_cooldown("album", album_uuid, current_user, db)

    album_repo = AlbumRepository(db)
    album = await album_repo.get_by_id_with_links(album_uuid)

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    try:
        song_service = get_song_service()
        song_list = None

        for link in album.platform_links:
            for candidate_url in _candidate_urls_for_link(link, "album"):
                try:
                    song_list = await song_service.get_album(candidate_url)
                    if song_list.songs:
                        break
                except Exception as e:
                    logger.debug(
                        "Album refresh candidate failed (%s): %s",
                        candidate_url,
                        e,
                    )
            if song_list and song_list.songs:
                break

        # Fallback for legacy rows with invalid synthetic platform links:
        # derive album candidates from existing songs linked to this album.
        if not song_list:
            from sqlalchemy import select

            song_rows = (
                await db.execute(
                    select(Song).where(Song.album_id == album_uuid).limit(100)
                )
            ).scalars().all()

            fallback_urls: list[str] = []
            for song_row in song_rows:
                metadata = song_row.metadata_json or {}
                list_url = metadata.get("list_url")
                if isinstance(list_url, str) and list_url.startswith("http"):
                    fallback_urls.append(list_url)

                if song_row.platform == "apple_music" and "/album/" in song_row.platform_url:
                    fallback_urls.append(song_row.platform_url.split("?", 1)[0])

                album_platform_id = metadata.get("album_id")
                if album_platform_id:
                    built_url = _build_platform_url(
                        song_row.platform,
                        "album",
                        str(album_platform_id),
                    )
                    if built_url:
                        fallback_urls.append(built_url)

            seen_urls: set[str] = set()
            for candidate_url in fallback_urls:
                if candidate_url in seen_urls:
                    continue
                seen_urls.add(candidate_url)
                try:
                    song_list = await song_service.get_album(candidate_url)
                    if song_list.songs:
                        break
                except Exception as e:
                    logger.debug(
                        "Album refresh metadata fallback failed (%s): %s",
                        candidate_url,
                        e,
                    )

        if not song_list:
            raise HTTPException(status_code=400, detail="Cannot refresh from this platform")

        if song_list.songs:
            entity_service = EntityPersistenceService(db)
            await entity_service.persist_from_search(song_list.songs)
            if len(song_list.songs) > (album.total_tracks or 0):
                album.total_tracks = len(song_list.songs)

            # Record cooldown
            await record_refresh_cooldown("album", album_uuid, current_user, db)

            await db.commit()
        else:
            raise HTTPException(status_code=404, detail="No tracks returned from source")

        return RefreshResponse(success=True, message="Album metadata refreshed successfully")
    except Exception as e:
        _raise_refresh_error(e)


@router.post("/artists/{id}/refresh")
async def refresh_artist(
    id: Annotated[str, Path(description="Internal artist UUID")],
    db: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> RefreshResponse:
    """
    Refresh metadata for an artist by fetching latest data from source.

    Cooldown: 4 hours for regular users, no limit for admins.
    """
    artist_uuid = validate_uuid(id, "artist ID")

    # Check cooldown (raises 429 if on cooldown)
    await check_refresh_cooldown("artist", artist_uuid, current_user, db)

    artist_repo = ArtistRepository(db)
    artist = await artist_repo.get_by_id_with_links(artist_uuid)

    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    try:
        song_service = get_song_service()
        song_list = None

        for link in artist.platform_links:
            for candidate_url in _candidate_urls_for_link(link, "artist"):
                try:
                    song_list = await song_service.get_artist(candidate_url)
                    if song_list.songs:
                        break
                except Exception as e:
                    logger.debug(
                        "Artist refresh candidate failed (%s): %s",
                        candidate_url,
                        e,
                    )
            if song_list and song_list.songs:
                break

        # Fallback for legacy rows with invalid synthetic platform links:
        # derive artist candidates from existing songs linked to this artist.
        if not song_list:
            from sqlalchemy import select

            song_rows = (
                await db.execute(
                    select(Song).where(Song.artist_id == artist_uuid).limit(100)
                )
            ).scalars().all()

            fallback_urls: list[str] = []
            for song_row in song_rows:
                metadata = song_row.metadata_json or {}
                list_url = metadata.get("list_url")
                if isinstance(list_url, str) and list_url.startswith("http"):
                    fallback_urls.append(list_url)

                artist_platform_id = metadata.get("artist_id")
                if artist_platform_id:
                    built_url = _build_platform_url(
                        song_row.platform,
                        "artist",
                        str(artist_platform_id),
                    )
                    if built_url:
                        fallback_urls.append(built_url)

            seen_urls: set[str] = set()
            for candidate_url in fallback_urls:
                if candidate_url in seen_urls:
                    continue
                seen_urls.add(candidate_url)
                try:
                    song_list = await song_service.get_artist(candidate_url)
                    if song_list.songs:
                        break
                except Exception as e:
                    logger.debug(
                        "Artist refresh metadata fallback failed (%s): %s",
                        candidate_url,
                        e,
                    )

        if not song_list:
            raise HTTPException(status_code=400, detail="Cannot refresh from this platform")
        if not song_list.songs:
            raise HTTPException(status_code=404, detail="No tracks returned from source")

        entity_service = EntityPersistenceService(db)
        await entity_service.persist_from_search(song_list.songs)

        spotify_link = next(
            (platform_link for platform_link in artist.platform_links if platform_link.platform == "spotify"),
            None,
        )
        # Fetch artist image from Spotify if a Spotify link exists
        if spotify_link is not None:
            try:
                import asyncio
                from spotdl.core.types.song import Platform
                spotify_provider = song_service._providers.get(Platform.SPOTIFY)
                if spotify_provider:
                    client = spotify_provider._get_client()
                    loop = asyncio.get_event_loop()
                    artist_data = await loop.run_in_executor(
                        None,
                        client.artist,
                        spotify_link.platform_id,
                    )
                else:
                    artist_data = None

                if artist_data:
                    images = artist_data.get("images", [])
                    if images:
                        # Get highest resolution image
                        sorted_images = sorted(
                            images,
                            key=lambda x: x.get("width", 0) * x.get("height", 0),
                            reverse=True,
                        )
                        image_url = sorted_images[0].get("url")
                        if image_url:
                            artist.image_url = image_url

                    # Also update genres if available
                    genres = artist_data.get("genres", [])
                    if genres:
                        existing_genres = set(artist.genres or [])
                        artist.genres = list(existing_genres.union(genres))

                    # Update followers count in platform link
                    followers = artist_data.get("followers", {}).get("total")
                    if followers:
                        spotify_link.followers = followers

                    # Ensure changes are tracked
                    db.add(artist)
                    logger.info(f"Updated artist {artist.name} with image: {artist.image_url}")

            except Exception as img_err:
                logger.warning(f"Failed to fetch artist image: {img_err}")

        # Record cooldown
        await record_refresh_cooldown("artist", artist_uuid, current_user, db)

        await db.commit()

        return RefreshResponse(success=True, message="Artist metadata refreshed successfully")
    except Exception as e:
        _raise_refresh_error(e)


@router.post("/playlists/{id}/refresh")
async def refresh_playlist(
    id: Annotated[str, Path(description="Internal playlist UUID")],
    db: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> RefreshResponse:
    """
    Refresh metadata for a playlist by fetching latest data from source.

    Cooldown: 4 hours for regular users, no limit for admins.
    """
    playlist_uuid = validate_uuid(id, "playlist ID")

    # Check cooldown (raises 429 if on cooldown)
    await check_refresh_cooldown("playlist", playlist_uuid, current_user, db)

    playlist_repo = PlaylistRepository(db)
    playlist = await playlist_repo.get_by_id_with_tracks(playlist_uuid)

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    try:
        song_service = get_song_service()
        song_list = None

        for link in playlist.platform_links:
            for candidate_url in _candidate_urls_for_link(link, "playlist"):
                try:
                    song_list = await song_service.get_playlist(candidate_url)
                    if song_list.songs:
                        break
                except Exception as e:
                    logger.debug(
                        "Playlist refresh candidate failed (%s): %s",
                        candidate_url,
                        e,
                    )
            if song_list and song_list.songs:
                break

        # Fallback for legacy rows with invalid synthetic platform links:
        # derive playlist candidates from existing track metadata.
        if not song_list:
            fallback_urls: list[str] = []
            for playlist_track in playlist.tracks:
                metadata = (playlist_track.song.metadata_json or {}) if playlist_track.song else {}
                list_url = metadata.get("list_url")
                if isinstance(list_url, str) and list_url.startswith("http"):
                    fallback_urls.append(list_url)

            seen_urls: set[str] = set()
            for candidate_url in fallback_urls:
                if candidate_url in seen_urls:
                    continue
                seen_urls.add(candidate_url)
                try:
                    song_list = await song_service.get_playlist(candidate_url)
                    if song_list.songs:
                        break
                except Exception as e:
                    logger.debug(
                        "Playlist refresh metadata fallback failed (%s): %s",
                        candidate_url,
                        e,
                    )

        if not song_list:
            raise HTTPException(status_code=400, detail="Cannot refresh from this platform")

        if song_list.songs:
            entity_service = EntityPersistenceService(db)
            persist_result = await entity_service.persist_from_search(song_list.songs)

            # Update playlist tracks
            await playlist_repo.clear_tracks(playlist.id)
            for i, song in enumerate(song_list.songs):
                song_key = f"{song.platform.value}:{song.platform_id}"
                song_id = persist_result.song_ids.get(song_key)
                if song_id:
                    await playlist_repo.add_track(playlist.id, song_id, i)

            if len(song_list.songs) > (playlist.total_tracks or 0):
                playlist.total_tracks = len(song_list.songs)

            # Record cooldown
            await record_refresh_cooldown("playlist", playlist_uuid, current_user, db)

            await db.commit()
        else:
            raise HTTPException(status_code=404, detail="No tracks returned from source")

        return RefreshResponse(success=True, message="Playlist metadata refreshed successfully")
    except Exception as e:
        _raise_refresh_error(e)


class EnrichResponse(BaseModel):
    """Response model for an enrichment operation."""

    success: bool
    message: str
    sources_used: list[str] = []
    fields_updated: list[str] = []
    snapshot_count: int = 0


@router.post("/songs/{id}/enrich")
async def enrich_song(
    id: Annotated[str, Path(description="Internal song UUID")],
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
    db: AsyncSession = Depends(get_db_session),
) -> EnrichResponse:
    """
    Enrich a song with metadata from external sources (MusicBrainz, Discogs).

    This fetches additional metadata like genres, labels, and external IDs
    from free metadata providers.

    Uses user's metadata source preferences to determine which providers to use
    and in what order. Unauthenticated users get default provider set.
    """
    from spotdl.core.services.metadata import MetadataService

    song_uuid = validate_uuid(id, "song ID")

    song_repo = SongRepository(db)
    song = await song_repo.get_by_id(song_uuid)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    try:
        # Always create/update the primary snapshot first.
        primary_snapshot = await _ensure_song_platform_snapshot(song, db)

        # Initialize metadata service with user preferences
        metadata_service = MetadataService(
            metadata_preferences=preferences["metadata"],
        )

        # Fetch and save snapshots from all metadata providers.
        provider_snapshots = await metadata_service.fetch_all_snapshots(
            song_id=song_uuid,
            isrc=song.isrc,
            name=song.name,
            artist=song.artists[0] if song.artists else "",
            album_name=song.album_name,
            session=db,
        )

        all_snapshots = [primary_snapshot, *provider_snapshots]
        fields_updated: list[str] = []
        if all_snapshots:
            best_snapshot = max(all_snapshots, key=lambda s: s.confidence)
            fields_updated = _apply_snapshot_to_song(song, best_snapshot)

        sources_used = sorted({snapshot.source for snapshot in all_snapshots})
        song.enriched_at = datetime.now(timezone.utc)

        await db.commit()

        return EnrichResponse(
            success=True,
            message=f"Enrichment complete. Updated {len(fields_updated)} fields.",
            sources_used=sources_used,
            fields_updated=fields_updated,
            snapshot_count=len(all_snapshots),
        )

    except Exception as e:
        logger.error(f"Failed to enrich song: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enrich: {str(e)}") from e


@router.get("/metadata-providers")
async def list_metadata_providers() -> dict:
    """
    List available metadata providers for enrichment.
    """
    return {
        "providers": [
            {
                "id": "spotify",
                "name": "Spotify (Primary Snapshot)",
                "description": "Snapshot of the song metadata from the primary source platform",
                "icon": "spotify",
                "features": ["name", "artists", "album", "isrc", "audio_features"],
                "rate_limit": "n/a",
                "auth_required": False,
            },
            {
                "id": "musicbrainz",
                "name": "MusicBrainz",
                "description": "Open music encyclopedia with accurate ISRC lookups",
                "icon": "musicbrainz",
                "features": ["isrc", "genres", "label", "year", "track_number"],
                "rate_limit": "1 request/second",
                "auth_required": False,
            },
            {
                "id": "discogs",
                "name": "Discogs",
                "description": "Comprehensive music database with genres and styles",
                "icon": "discogs",
                "features": ["genres", "styles", "label", "year", "country"],
                "rate_limit": "25 requests/minute (60 with token)",
                "auth_required": False,
            },
        ]
    }


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
            if platform_id.startswith("UC"):
                return f"https://music.youtube.com/channel/{platform_id}"
            return f"https://music.youtube.com/browse/{platform_id}"
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


def _candidate_urls_for_link(link, entity_type: str) -> list[str]:
    """Return preferred URL candidates for refreshing an entity link."""
    candidates: list[str] = []

    existing_url = (getattr(link, "platform_url", None) or "").strip()
    if existing_url:
        candidates.append(existing_url)

    built_url = _build_platform_url(link.platform, entity_type, link.platform_id)
    if built_url and built_url not in candidates:
        candidates.append(built_url)

    return candidates


class FullEnrichmentResponse(BaseModel):
    """Response model for full enrichment operation."""

    success: bool
    message: str
    metadata_sources_count: int = 0
    lyrics_sources_count: int = 0
    metadata_sources: list[str] = []


@router.post("/songs/{id}/enrich-all")
async def enrich_song_from_all_sources(
    id: Annotated[str, Path(description="Internal song UUID")],
    db: AsyncSession = Depends(get_db_session),
) -> FullEnrichmentResponse:
    """
    Fetch and store metadata from ALL available sources.

    This endpoint triggers comprehensive enrichment:
    - MusicBrainz, Discogs (metadata)
    - Genius, MusixMatch, AZLyrics, LRCLIB (lyrics)

    All raw API responses are preserved in MetadataSnapshots for future use.
    Returns summary of what was stored.
    """
    from spotdl.core.services.metadata import MetadataService
    from spotdl.core.services.lyrics import LyricsService

    song_uuid = validate_uuid(id, "song ID")

    song_repo = SongRepository(db)
    song = await song_repo.get_by_id(song_uuid)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    try:
        # First, create/update a snapshot from the current primary platform data.
        platform_snapshot = await _ensure_song_platform_snapshot(song, db)

        # Initialize services
        metadata_service = MetadataService(
            enable_musicbrainz=True,
            enable_discogs=True,
        )

        lyrics_service = LyricsService(
            session=db,
            genius_token=None,  # Use web scraping
            enable_cache=True,
        )

        # Use entity service for orchestration
        entity_service = EntityPersistenceService(db)
        result = await entity_service.full_enrich_song(
            song_id=song_uuid,
            metadata_service=metadata_service,
            lyrics_service=lyrics_service,
        )

        # Include the platform snapshot in the count
        total_metadata_sources = result.metadata_sources_count + 1
        all_sources = [platform_snapshot.source] + [s.source for s in result.metadata_snapshots]

        await db.commit()

        return FullEnrichmentResponse(
            success=True,
            message=f"Enrichment complete. {total_metadata_sources} metadata sources, {result.lyrics_sources_count} lyrics sources.",
            metadata_sources_count=total_metadata_sources,
            lyrics_sources_count=result.lyrics_sources_count,
            metadata_sources=all_sources,
        )

    except Exception as e:
        logger.error(f"Failed to fully enrich song: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enrich: {str(e)}") from e
