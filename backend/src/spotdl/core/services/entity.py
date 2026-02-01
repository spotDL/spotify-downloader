"""Entity persistence service for managing cross-platform entities."""

from __future__ import annotations

import logging
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.db.models.album import Album, AlbumPlatformLink
from spotdl.db.models.artist import Artist, ArtistPlatformLink
from spotdl.db.models.playlist import Playlist, PlaylistPlatformLink
from spotdl.db.models.song import Song as SongModel
from spotdl.db.repositories.album import AlbumRepository
from spotdl.db.repositories.artist import ArtistRepository
from spotdl.db.repositories.playlist import PlaylistRepository
from spotdl.db.repositories.song import SongRepository

if TYPE_CHECKING:
    from spotdl.core.services.lyrics import LyricsService
    from spotdl.core.services.metadata import MetadataService
    from spotdl.core.types.song import Song
    from spotdl.db.models.metadata_snapshot import MetadataSnapshot

logger = logging.getLogger(__name__)


class EntityPersistenceError(Exception):
    """Base exception for entity persistence errors."""


@dataclass
class PersistResult:
    """Result of persisting entities from search results."""

    artists_created: int = 0
    artists_linked: int = 0
    albums_created: int = 0
    albums_linked: int = 0
    songs_created: int = 0
    songs_linked: int = 0

    # Mappings from platform data to internal IDs
    artist_ids: dict[str, uuid.UUID] = field(default_factory=dict)  # normalized_name -> id
    album_ids: dict[str, uuid.UUID] = field(default_factory=dict)  # normalized_name -> id
    song_ids: dict[str, uuid.UUID] = field(default_factory=dict)  # platform:platform_id -> id

    @property
    def total_created(self) -> int:
        return self.artists_created + self.albums_created + self.songs_created

    @property
    def total_linked(self) -> int:
        return self.artists_linked + self.albums_linked + self.songs_linked


class EntityPersistenceService:
    """
    Service for persisting and linking entities across platforms.

    This service:
    - Creates internal Artist, Album, and Song records
    - Links them to platform-specific IDs (Spotify, Deezer, etc.)
    - Uses name normalization for cross-platform matching
    - Returns internal UUIDs for frontend use
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with a database session."""
        self.session = session
        self.artist_repo = ArtistRepository(session)
        self.album_repo = AlbumRepository(session)
        self.playlist_repo = PlaylistRepository(session)
        self.song_repo = SongRepository(session)

    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize a name for matching across platforms.

        - Convert to lowercase
        - Remove accents/diacritics
        - Remove special characters
        - Collapse whitespace
        """
        # Convert to lowercase
        name = name.lower()

        # Decompose unicode and remove combining characters (accents)
        name = unicodedata.normalize("NFKD", name)
        name = "".join(c for c in name if not unicodedata.combining(c))

        # Remove special characters, keep alphanumeric and spaces
        name = re.sub(r"[^a-z0-9\s]", "", name)

        # Collapse whitespace
        name = re.sub(r"\s+", " ", name).strip()

        return name

    async def find_or_create_artist(
        self,
        name: str,
        platform: str,
        platform_id: str,
        platform_url: str,
        image_url: str | None = None,
        genres: list[str] | None = None,
        followers: int | None = None,
    ) -> tuple[Artist, bool]:
        """
        Find an existing artist or create a new one.

        Matching logic:
        1. Check if platform_link exists → return existing artist
        2. Find artist by normalized name → link to existing
        3. Create new artist + platform_link

        Args:
            name: Artist name
            platform: Platform identifier (spotify, deezer, etc.)
            platform_id: Platform-specific ID
            platform_url: Platform-specific URL
            image_url: Artist image URL
            genres: Artist genres
            followers: Follower count on this platform

        Returns:
            Tuple of (Artist, created_flag)
        """
        # 1. Check if platform link already exists
        existing_link = await self.artist_repo.get_platform_link(platform, platform_id)
        if existing_link:
            artist = await self.artist_repo.get_by_id_with_links(existing_link.artist_id)
            if artist:
                return artist, False

        # 2. Try to find by normalized name
        name_normalized = self.normalize_name(name)
        artist = await self.artist_repo.get_by_normalized_name(name_normalized)

        if artist:
            # Link existing artist to this platform
            await self.artist_repo.add_platform_link(
                artist_id=artist.id,
                platform=platform,
                platform_id=platform_id,
                platform_url=platform_url,
                followers=followers,
            )
            # Update image if we don't have one
            if image_url and not artist.image_url:
                artist.image_url = image_url
            # Merge genres
            if genres:
                existing_genres = set(artist.genres or [])
                artist.genres = list(existing_genres | set(genres))
            await self.session.flush()
            return artist, False

        # 3. Create new artist
        artist = await self.artist_repo.create(
            name=name,
            name_normalized=name_normalized,
            image_url=image_url,
            genres=genres or [],
        )
        await self.artist_repo.add_platform_link(
            artist_id=artist.id,
            platform=platform,
            platform_id=platform_id,
            platform_url=platform_url,
            followers=followers,
        )
        return artist, True

    async def find_or_create_album(
        self,
        name: str,
        artist_name: str,
        platform: str,
        platform_id: str,
        platform_url: str,
        artist_id: uuid.UUID | None = None,
        cover_url: str | None = None,
        year: int | None = None,
        total_tracks: int = 0,
    ) -> tuple[Album, bool]:
        """
        Find an existing album or create a new one.

        Args:
            name: Album name
            artist_name: Primary artist name
            platform: Platform identifier
            platform_id: Platform-specific ID
            platform_url: Platform-specific URL
            artist_id: Internal artist UUID (if known)
            cover_url: Album cover URL
            year: Release year
            total_tracks: Number of tracks

        Returns:
            Tuple of (Album, created_flag)
        """
        # 1. Check if platform link already exists
        existing_link = await self.album_repo.get_platform_link(platform, platform_id)
        if existing_link:
            album = await self.album_repo.get_by_id_with_links(existing_link.album_id)
            if album:
                return album, False

        # 2. Try to find by normalized name and artist
        name_normalized = self.normalize_name(name)
        album = await self.album_repo.get_by_normalized_name_and_artist(
            name_normalized, artist_id
        )

        if album:
            # Link existing album to this platform
            await self.album_repo.add_platform_link(
                album_id=album.id,
                platform=platform,
                platform_id=platform_id,
                platform_url=platform_url,
            )
            # Update cover if we don't have one
            if cover_url and not album.cover_url:
                album.cover_url = cover_url
            await self.session.flush()
            return album, False

        # 3. Create new album
        album = await self.album_repo.create(
            name=name,
            name_normalized=name_normalized,
            artist_id=artist_id,
            artist_name=artist_name,
            cover_url=cover_url,
            year=year,
            total_tracks=total_tracks,
        )
        await self.album_repo.add_platform_link(
            album_id=album.id,
            platform=platform,
            platform_id=platform_id,
            platform_url=platform_url,
        )
        return album, True

    async def find_or_create_playlist(
        self,
        name: str,
        platform: str,
        platform_id: str,
        platform_url: str,
        owner_name: str | None = None,
        description: str | None = None,
        cover_url: str | None = None,
        total_tracks: int = 0,
        followers: int | None = None,
    ) -> tuple[Playlist, bool]:
        """
        Find an existing playlist or create a new one.

        Playlists are matched by platform link only (no cross-platform matching).

        Args:
            name: Playlist name
            platform: Platform identifier
            platform_id: Platform-specific ID
            platform_url: Platform-specific URL
            owner_name: Playlist owner name
            description: Playlist description
            cover_url: Cover image URL
            total_tracks: Number of tracks
            followers: Follower count

        Returns:
            Tuple of (Playlist, created_flag)
        """
        # Check if platform link already exists
        existing_link = await self.playlist_repo.get_platform_link(platform, platform_id)
        if existing_link:
            playlist = await self.playlist_repo.get_by_id_with_links(
                existing_link.playlist_id
            )
            if playlist:
                return playlist, False

        # Create new playlist
        playlist = await self.playlist_repo.create(
            name=name,
            name_normalized=self.normalize_name(name),
            owner_name=owner_name,
            description=description,
            cover_url=cover_url,
            total_tracks=total_tracks,
        )
        await self.playlist_repo.add_platform_link(
            playlist_id=playlist.id,
            platform=platform,
            platform_id=platform_id,
            platform_url=platform_url,
            followers=followers,
        )
        return playlist, True

    async def persist_song(
        self,
        song: Song,
        artist_id: uuid.UUID | None = None,
        album_id: uuid.UUID | None = None,
    ) -> tuple[SongModel, bool]:
        """
        Persist a song to the database.

        Args:
            song: Song object from provider
            artist_id: Internal artist UUID to link
            album_id: Internal album UUID to link

        Returns:
            Tuple of (SongModel, created_flag)
        """
        # Check if song already exists
        existing = await self.song_repo.get_by_platform_id(
            song.platform.value, song.platform_id
        )
        if existing:
            # Update links if provided and not set
            if artist_id and not existing.artist_id:
                existing.artist_id = artist_id
            if album_id and not existing.album_id:
                existing.album_id = album_id
            await self.session.flush()
            return existing, False

        # Create new song - extract all enriched fields
        from datetime import datetime, timezone, date as date_type

        # Convert year to date if available
        release_date = None
        if song.year and song.year > 0:
            try:
                release_date = date_type(song.year, 1, 1)
            except ValueError:
                pass

        song_model = await self.song_repo.create(
            platform=song.platform.value,
            platform_id=song.platform_id,
            platform_url=song.url,
            name=song.name,
            artists=song.artists,
            album_name=song.album_name,
            duration_seconds=song.duration,
            isrc=song.isrc,
            metadata_json=song.json,
            artist_id=artist_id,
            album_id=album_id,
            # Enriched fields from Song DTO
            genres=song.genres if song.genres else None,
            release_date=release_date,
            explicit=song.explicit if song.explicit else None,
            copyright_text=song.copyright_text,
            # Mark as enriched if we have enriched data
            enriched_at=datetime.now(timezone.utc) if song.genres else None,
        )
        return song_model, True

    async def persist_from_search(self, songs: list[Song]) -> PersistResult:
        """
        Extract and persist entities from search results.

        This method:
        - Groups songs by artist and album
        - Creates/links Artist records
        - Creates/links Album records
        - Creates/links Song records
        - Returns internal IDs for all entities

        Args:
            songs: List of Song objects from search

        Returns:
            PersistResult with counts and ID mappings
        """
        result = PersistResult()

        for song in songs:
            try:
                # Handle primary artist
                primary_artist = song.artists[0] if song.artists else "Unknown Artist"
                artist_normalized = self.normalize_name(primary_artist)

                # Get or create artist
                if artist_normalized not in result.artist_ids:
                    # Use song's artist_id if available, otherwise generate one
                    artist_platform_id = song.artist_id or f"artist_{song.platform_id}"
                    # Build artist URL from song URL pattern
                    artist_url = f"https://{song.platform.value}.com/artist/{artist_platform_id}"

                    artist, created = await self.find_or_create_artist(
                        name=primary_artist,
                        platform=song.platform.value,
                        platform_id=artist_platform_id,
                        platform_url=artist_url,
                        image_url=None,
                    )
                    result.artist_ids[artist_normalized] = artist.id
                    if created:
                        result.artists_created += 1
                    else:
                        result.artists_linked += 1

                artist_id = result.artist_ids.get(artist_normalized)

                # Handle album if present
                album_id = None
                if song.album_name:
                    album_normalized = self.normalize_name(song.album_name)
                    album_key = f"{artist_normalized}:{album_normalized}"

                    if album_key not in result.album_ids:
                        # Use song's album_id if available, otherwise generate one
                        album_platform_id = song.album_id or f"album_{song.platform_id}"
                        # Build album URL from song URL pattern
                        album_url = f"https://{song.platform.value}.com/album/{album_platform_id}"
                        album_cover = song.cover_url
                        album_year = song.year if song.year else None

                        album, created = await self.find_or_create_album(
                            name=song.album_name,
                            artist_name=primary_artist,
                            platform=song.platform.value,
                            platform_id=album_platform_id,
                            platform_url=album_url,
                            artist_id=artist_id,
                            cover_url=album_cover,
                            year=album_year,
                        )
                        result.album_ids[album_key] = album.id
                        if created:
                            result.albums_created += 1
                        else:
                            result.albums_linked += 1

                    album_id = result.album_ids.get(album_key)

                # Persist the song
                song_key = f"{song.platform.value}:{song.platform_id}"
                song_model, created = await self.persist_song(
                    song, artist_id=artist_id, album_id=album_id
                )
                result.song_ids[song_key] = song_model.id
                if created:
                    result.songs_created += 1
                else:
                    result.songs_linked += 1

            except Exception as e:
                logger.warning(f"Failed to persist song {song.name}: {e}")
                continue

        await self.session.flush()
        return result

    async def get_artist_by_internal_id(self, id: uuid.UUID) -> Artist | None:
        """Get an artist by internal UUID."""
        return await self.artist_repo.get_by_id_with_links(id)

    async def get_album_by_internal_id(self, id: uuid.UUID) -> Album | None:
        """Get an album by internal UUID."""
        return await self.album_repo.get_by_id_with_links(id)

    async def get_playlist_by_internal_id(self, id: uuid.UUID) -> Playlist | None:
        """Get a playlist by internal UUID with tracks."""
        return await self.playlist_repo.get_by_id_with_tracks(id)

    async def get_song_by_internal_id(self, id: uuid.UUID) -> SongModel | None:
        """Get a song by internal UUID."""
        return await self.song_repo.get_by_id(id)

    async def enrich_artists_with_images(
        self,
        artist_ids: list[uuid.UUID],
        song_service: "SongService",
    ) -> int:
        """
        Fetch and update artist images from Spotify for artists without images.

        Args:
            artist_ids: List of internal artist UUIDs to check
            song_service: SongService instance with configured Spotify provider

        Returns:
            Number of artists updated with images
        """
        import asyncio
        from spotdl.core.types.song import Platform

        spotify_provider = song_service._providers.get(Platform.SPOTIFY)
        if not spotify_provider:
            logger.warning("Spotify provider not available for artist image enrichment")
            return 0

        updated_count = 0
        client = spotify_provider._get_client()
        loop = asyncio.get_event_loop()

        for artist_id in artist_ids:
            try:
                artist = await self.artist_repo.get_by_id_with_links(artist_id)
                if not artist or artist.image_url:
                    # Skip if artist not found or already has image
                    continue

                # Find Spotify platform link
                spotify_link = None
                for link in (artist.platform_links or []):
                    if link.platform == "spotify":
                        spotify_link = link
                        break

                if not spotify_link:
                    continue

                # Fetch artist data from Spotify
                artist_data = await loop.run_in_executor(
                    None, client.artist, spotify_link.platform_id
                )

                if not artist_data:
                    continue

                # Update image
                images = artist_data.get("images", [])
                if images:
                    sorted_images = sorted(
                        images,
                        key=lambda x: x.get("width", 0) * x.get("height", 0),
                        reverse=True,
                    )
                    artist.image_url = sorted_images[0].get("url")

                # Update genres
                genres = artist_data.get("genres", [])
                if genres:
                    existing_genres = set(artist.genres or [])
                    artist.genres = list(existing_genres.union(genres))

                # Update followers
                followers = artist_data.get("followers", {}).get("total")
                if followers and spotify_link:
                    spotify_link.followers = followers

                self.session.add(artist)
                updated_count += 1
                logger.debug(f"Enriched artist {artist.name} with image and genres")

            except Exception as e:
                logger.warning(f"Failed to enrich artist {artist_id}: {e}")
                continue

        if updated_count > 0:
            await self.session.flush()

        return updated_count

    async def full_enrich_song(
        self,
        song_id: uuid.UUID,
        metadata_service: MetadataService,
        lyrics_service: LyricsService,
    ) -> EnrichmentResult:
        """
        Perform full enrichment from ALL sources.

        This method:
        1. Fetches metadata from MusicBrainz, Discogs (and stores snapshots)
        2. Fetches lyrics from Genius, MusixMatch, AZLyrics, LRCLIB
        3. Updates song's enriched_at timestamp

        All raw responses are preserved in MetadataSnapshots for future use.

        Args:
            song_id: Internal song UUID
            metadata_service: MetadataService instance
            lyrics_service: LyricsService instance

        Returns:
            EnrichmentResult with counts of what was fetched

        Raises:
            EntityPersistenceError: If song not found
        """
        song_model = await self.song_repo.get_by_id(song_id)
        if not song_model:
            raise EntityPersistenceError(f"Song not found: {song_id}")

        result = EnrichmentResult()

        # 1. Fetch metadata from all providers and save snapshots
        try:
            snapshots = await metadata_service.fetch_all_snapshots(
                song_id=song_id,
                isrc=song_model.isrc,
                name=song_model.name,
                artist=song_model.artists[0] if song_model.artists else "",
                album_name=song_model.album_name,
                session=self.session,
            )
            result.metadata_snapshots = snapshots
            result.metadata_sources_count = len(snapshots)

            # Update song with merged data from best snapshot
            if snapshots:
                best_snapshot = max(snapshots, key=lambda s: s.confidence)
                data = best_snapshot.snapshot_data

                # Update song fields if not already set
                if not song_model.genres and data.get("genres"):
                    song_model.genres = data["genres"]
                if not song_model.isrc and data.get("isrc"):
                    song_model.isrc = data["isrc"]
                if not song_model.release_date and data.get("year"):
                    from datetime import date as date_type
                    try:
                        song_model.release_date = date_type(data["year"], 1, 1)
                    except ValueError:
                        pass

        except Exception as e:
            logger.warning(f"Metadata enrichment failed for {song_id}: {e}")

        # 2. Fetch lyrics from all providers
        try:
            async with lyrics_service:
                lyrics_results = await lyrics_service.fetch_all_lyrics(
                    song_id=song_id,
                    name=song_model.name,
                    artists=song_model.artists or [],
                    album_name=song_model.album_name,
                    duration=song_model.duration_seconds,
                )
                result.lyrics_sources_count = len(lyrics_results)

        except Exception as e:
            logger.warning(f"Lyrics enrichment failed for {song_id}: {e}")

        # 3. Update enriched_at timestamp
        song_model.enriched_at = datetime.now(timezone.utc)
        await self.session.flush()

        logger.info(
            f"Full enrichment completed for {song_id}: "
            f"{result.metadata_sources_count} metadata sources, "
            f"{result.lyrics_sources_count} lyrics sources"
        )

        return result


@dataclass
class EnrichmentResult:
    """Result of full enrichment operation."""

    metadata_snapshots: list[MetadataSnapshot] = field(default_factory=list)
    metadata_sources_count: int = 0
    lyrics_sources_count: int = 0


if TYPE_CHECKING:
    from spotdl.core.services.song import SongService
