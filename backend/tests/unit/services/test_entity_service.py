"""Tests for EntityPersistenceService."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spotdl.core.services.entity import (
    EnrichmentResult,
    EntityPersistenceError,
    EntityPersistenceService,
    PersistResult,
)
from spotdl.core.types.song import Platform, Song
from spotdl.db.models.album import Album, AlbumPlatformLink
from spotdl.db.models.artist import Artist, ArtistPlatformLink
from spotdl.db.models.playlist import Playlist, PlaylistPlatformLink
from spotdl.db.models.song import Song as SongModel


class TestNormalizeName:
    """Tests for the normalize_name static method."""

    def test_lowercase(self) -> None:
        """Test conversion to lowercase."""
        assert EntityPersistenceService.normalize_name("TEST") == "test"
        assert EntityPersistenceService.normalize_name("TeSt") == "test"

    def test_remove_accents(self) -> None:
        """Test removal of accents and diacritics."""
        assert EntityPersistenceService.normalize_name("café") == "cafe"
        assert EntityPersistenceService.normalize_name("naïve") == "naive"
        assert EntityPersistenceService.normalize_name("Zürich") == "zurich"

    def test_remove_special_chars(self) -> None:
        """Test removal of special characters."""
        assert EntityPersistenceService.normalize_name("AC/DC") == "acdc"
        assert EntityPersistenceService.normalize_name("Guns N' Roses") == "guns n roses"
        assert EntityPersistenceService.normalize_name("Panic! at the Disco") == "panic at the disco"

    def test_collapse_whitespace(self) -> None:
        """Test collapsing multiple spaces."""
        assert EntityPersistenceService.normalize_name("The   Beatles") == "the beatles"
        assert EntityPersistenceService.normalize_name("  trimmed  ") == "trimmed"

    def test_combined_normalization(self) -> None:
        """Test combined normalization operations."""
        assert EntityPersistenceService.normalize_name("Björk") == "bjork"
        assert EntityPersistenceService.normalize_name("Twenty Øne Piløts") == "twenty ne pilts"


class TestPersistResult:
    """Tests for PersistResult dataclass."""

    def test_empty_result(self) -> None:
        """Test empty result initialization."""
        result = PersistResult()
        assert result.artists_created == 0
        assert result.total_created == 0
        assert result.total_linked == 0

    def test_total_created(self) -> None:
        """Test total_created property."""
        result = PersistResult(
            artists_created=2,
            albums_created=3,
            songs_created=5,
        )
        assert result.total_created == 10

    def test_total_linked(self) -> None:
        """Test total_linked property."""
        result = PersistResult(
            artists_linked=1,
            albums_linked=2,
            songs_linked=3,
        )
        assert result.total_linked == 6

    def test_mappings(self) -> None:
        """Test ID mappings."""
        artist_id = uuid.uuid4()
        album_id = uuid.uuid4()
        song_id = uuid.uuid4()

        result = PersistResult()
        result.artist_ids["the beatles"] = artist_id
        result.album_ids["abbey road"] = album_id
        result.song_ids["spotify:abc123"] = song_id

        assert result.artist_ids["the beatles"] == artist_id
        assert result.album_ids["abbey road"] == album_id
        assert result.song_ids["spotify:abc123"] == song_id


@pytest.mark.asyncio
class TestFindOrCreateArtist:
    """Tests for find_or_create_artist method."""

    async def test_create_new_artist(self, db_session) -> None:
        """Test creating a new artist."""
        service = EntityPersistenceService(db_session)

        artist, created = await service.find_or_create_artist(
            name="The Beatles",
            platform="spotify",
            platform_id="3WrFJ7ztbogyGnTHbHJFl2",
            platform_url="https://open.spotify.com/artist/3WrFJ7ztbogyGnTHbHJFl2",
            image_url="https://example.com/image.jpg",
            genres=["rock", "pop"],
            followers=10000,
        )

        assert created is True
        assert artist.name == "The Beatles"
        assert artist.name_normalized == "the beatles"
        assert artist.image_url == "https://example.com/image.jpg"
        assert set(artist.genres) == {"rock", "pop"}

        # Check platform link was created
        link = await service.artist_repo.get_platform_link("spotify", "3WrFJ7ztbogyGnTHbHJFl2")
        assert link is not None
        assert link.artist_id == artist.id
        assert link.followers == 10000

    async def test_find_by_platform_link(self, db_session) -> None:
        """Test finding existing artist by platform link."""
        service = EntityPersistenceService(db_session)

        # Create artist first
        artist1, created1 = await service.find_or_create_artist(
            name="Pink Floyd",
            platform="spotify",
            platform_id="0k17h0D3J5VfsdmQ1iZtE9",
            platform_url="https://open.spotify.com/artist/0k17h0D3J5VfsdmQ1iZtE9",
        )
        assert created1 is True

        # Try to create again with same platform link
        artist2, created2 = await service.find_or_create_artist(
            name="Pink Floyd",
            platform="spotify",
            platform_id="0k17h0D3J5VfsdmQ1iZtE9",
            platform_url="https://open.spotify.com/artist/0k17h0D3J5VfsdmQ1iZtE9",
        )

        assert created2 is False
        assert artist2.id == artist1.id

    async def test_find_by_normalized_name(self, db_session) -> None:
        """Test finding existing artist by normalized name."""
        service = EntityPersistenceService(db_session)

        # Create on Spotify
        artist1, created1 = await service.find_or_create_artist(
            name="Radiohead",
            platform="spotify",
            platform_id="4Z8W4fKeB5YxbusRsdQVPb",
            platform_url="https://open.spotify.com/artist/4Z8W4fKeB5YxbusRsdQVPb",
        )
        assert created1 is True

        # Link to Deezer with slightly different name
        artist2, created2 = await service.find_or_create_artist(
            name="RADIOHEAD",
            platform="deezer",
            platform_id="deezer123",
            platform_url="https://deezer.com/artist/deezer123",
        )

        assert created2 is False
        assert artist2.id == artist1.id

        # Should have both platform links
        spotify_link = await service.artist_repo.get_platform_link("spotify", "4Z8W4fKeB5YxbusRsdQVPb")
        deezer_link = await service.artist_repo.get_platform_link("deezer", "deezer123")
        assert spotify_link.artist_id == artist1.id
        assert deezer_link.artist_id == artist1.id

    async def test_update_image_when_missing(self, db_session) -> None:
        """Test updating image when artist doesn't have one."""
        service = EntityPersistenceService(db_session)

        # Create without image
        artist1, _ = await service.find_or_create_artist(
            name="Nirvana",
            platform="spotify",
            platform_id="spotify123",
            platform_url="https://open.spotify.com/artist/spotify123",
        )
        assert artist1.image_url is None

        # Link with image
        artist2, created = await service.find_or_create_artist(
            name="Nirvana",
            platform="deezer",
            platform_id="deezer123",
            platform_url="https://deezer.com/artist/deezer123",
            image_url="https://example.com/nirvana.jpg",
        )

        assert created is False
        assert artist2.id == artist1.id
        assert artist2.image_url == "https://example.com/nirvana.jpg"

    async def test_merge_genres(self, db_session) -> None:
        """Test merging genres from different platforms."""
        service = EntityPersistenceService(db_session)

        # Create with rock genre
        artist1, _ = await service.find_or_create_artist(
            name="Led Zeppelin",
            platform="spotify",
            platform_id="spotify123",
            platform_url="https://open.spotify.com/artist/spotify123",
            genres=["rock", "hard rock"],
        )
        assert set(artist1.genres) == {"rock", "hard rock"}

        # Link with additional genres
        artist2, created = await service.find_or_create_artist(
            name="Led Zeppelin",
            platform="deezer",
            platform_id="deezer123",
            platform_url="https://deezer.com/artist/deezer123",
            genres=["rock", "blues", "metal"],
        )

        assert created is False
        assert artist2.id == artist1.id
        assert set(artist2.genres) == {"rock", "hard rock", "blues", "metal"}


@pytest.mark.asyncio
class TestFindOrCreateAlbum:
    """Tests for find_or_create_album method."""

    async def test_create_new_album(self, db_session) -> None:
        """Test creating a new album."""
        service = EntityPersistenceService(db_session)

        # Create artist first
        artist, _ = await service.find_or_create_artist(
            name="The Beatles",
            platform="spotify",
            platform_id="artist123",
            platform_url="https://open.spotify.com/artist/artist123",
        )

        album, created = await service.find_or_create_album(
            name="Abbey Road",
            artist_name="The Beatles",
            platform="spotify",
            platform_id="album123",
            platform_url="https://open.spotify.com/album/album123",
            artist_id=artist.id,
            cover_url="https://example.com/cover.jpg",
            year=1969,
            total_tracks=17,
        )

        assert created is True
        assert album.name == "Abbey Road"
        assert album.name_normalized == "abbey road"
        assert album.artist_id == artist.id
        assert album.cover_url == "https://example.com/cover.jpg"
        assert album.year == 1969
        assert album.total_tracks == 17

    async def test_find_by_platform_link(self, db_session) -> None:
        """Test finding existing album by platform link."""
        service = EntityPersistenceService(db_session)

        album1, created1 = await service.find_or_create_album(
            name="Dark Side of the Moon",
            artist_name="Pink Floyd",
            platform="spotify",
            platform_id="album456",
            platform_url="https://open.spotify.com/album/album456",
        )
        assert created1 is True

        album2, created2 = await service.find_or_create_album(
            name="Dark Side of the Moon",
            artist_name="Pink Floyd",
            platform="spotify",
            platform_id="album456",
            platform_url="https://open.spotify.com/album/album456",
        )

        assert created2 is False
        assert album2.id == album1.id

    async def test_find_by_normalized_name_and_artist(self, db_session) -> None:
        """Test finding existing album by normalized name and artist."""
        service = EntityPersistenceService(db_session)

        artist, _ = await service.find_or_create_artist(
            name="Radiohead",
            platform="spotify",
            platform_id="artist789",
            platform_url="https://open.spotify.com/artist/artist789",
        )

        # Create on Spotify
        album1, created1 = await service.find_or_create_album(
            name="OK Computer",
            artist_name="Radiohead",
            platform="spotify",
            platform_id="spotify_album",
            platform_url="https://open.spotify.com/album/spotify_album",
            artist_id=artist.id,
        )
        assert created1 is True

        # Link to Deezer
        album2, created2 = await service.find_or_create_album(
            name="OK Computer",
            artist_name="Radiohead",
            platform="deezer",
            platform_id="deezer_album",
            platform_url="https://deezer.com/album/deezer_album",
            artist_id=artist.id,
        )

        assert created2 is False
        assert album2.id == album1.id

    async def test_update_cover_when_missing(self, db_session) -> None:
        """Test updating cover when album doesn't have one."""
        service = EntityPersistenceService(db_session)

        # Create without cover
        album1, _ = await service.find_or_create_album(
            name="Nevermind",
            artist_name="Nirvana",
            platform="spotify",
            platform_id="spotify_album",
            platform_url="https://open.spotify.com/album/spotify_album",
        )
        assert album1.cover_url is None

        # Link with cover
        album2, created = await service.find_or_create_album(
            name="Nevermind",
            artist_name="Nirvana",
            platform="deezer",
            platform_id="deezer_album",
            platform_url="https://deezer.com/album/deezer_album",
            artist_id=album1.artist_id,
            cover_url="https://example.com/nevermind.jpg",
        )

        assert created is False
        assert album2.cover_url == "https://example.com/nevermind.jpg"


@pytest.mark.asyncio
class TestFindOrCreatePlaylist:
    """Tests for find_or_create_playlist method."""

    async def test_create_new_playlist(self, db_session) -> None:
        """Test creating a new playlist."""
        service = EntityPersistenceService(db_session)

        playlist, created = await service.find_or_create_playlist(
            name="Top 50 Global",
            platform="spotify",
            platform_id="playlist123",
            platform_url="https://open.spotify.com/playlist/playlist123",
            owner_name="Spotify",
            description="The best tracks right now",
            cover_url="https://example.com/cover.jpg",
            total_tracks=50,
            followers=1000000,
        )

        assert created is True
        assert playlist.name == "Top 50 Global"
        assert playlist.owner_name == "Spotify"
        assert playlist.description == "The best tracks right now"
        assert playlist.total_tracks == 50

    async def test_find_by_platform_link(self, db_session) -> None:
        """Test finding existing playlist by platform link."""
        service = EntityPersistenceService(db_session)

        playlist1, created1 = await service.find_or_create_playlist(
            name="My Playlist",
            platform="spotify",
            platform_id="playlist456",
            platform_url="https://open.spotify.com/playlist/playlist456",
        )
        assert created1 is True

        playlist2, created2 = await service.find_or_create_playlist(
            name="My Playlist",
            platform="spotify",
            platform_id="playlist456",
            platform_url="https://open.spotify.com/playlist/playlist456",
        )

        assert created2 is False
        assert playlist2.id == playlist1.id

    async def test_no_cross_platform_matching(self, db_session) -> None:
        """Test that playlists don't match across platforms."""
        service = EntityPersistenceService(db_session)

        # Create on Spotify
        playlist1, created1 = await service.find_or_create_playlist(
            name="Chill Vibes",
            platform="spotify",
            platform_id="spotify_playlist",
            platform_url="https://open.spotify.com/playlist/spotify_playlist",
        )
        assert created1 is True

        # Create on Deezer with same name (should be different)
        playlist2, created2 = await service.find_or_create_playlist(
            name="Chill Vibes",
            platform="deezer",
            platform_id="deezer_playlist",
            platform_url="https://deezer.com/playlist/deezer_playlist",
        )

        assert created2 is True
        assert playlist2.id != playlist1.id


@pytest.mark.asyncio
class TestPersistSong:
    """Tests for persist_song method."""

    async def test_create_new_song(self, db_session) -> None:
        """Test creating a new song."""
        service = EntityPersistenceService(db_session)

        song = Song(
            name="Bohemian Rhapsody",
            artists=["Queen"],
            artist="Queen",
            duration=354,
            platform=Platform.SPOTIFY,
            platform_id="song123",
            url="https://open.spotify.com/track/song123",
            album_name="A Night at the Opera",
            year=1975,
            isrc="GBUM71029604",
            genres=["rock", "progressive rock"],
            explicit=False,
            copyright_text="© 1975 Queen Productions Ltd",
        )

        song_model, created = await service.persist_song(song)

        assert created is True
        assert song_model.name == "Bohemian Rhapsody"
        assert song_model.artists == ["Queen"]
        assert song_model.duration_seconds == 354
        assert song_model.platform == "spotify"
        assert song_model.platform_id == "song123"
        assert song_model.isrc == "GBUM71029604"
        assert song_model.genres == ["rock", "progressive rock"]
        # explicit is None when False due to logic in persist_song
        assert song_model.explicit is None
        assert song_model.copyright_text == "© 1975 Queen Productions Ltd"

    async def test_find_existing_song(self, db_session) -> None:
        """Test finding existing song by platform ID."""
        service = EntityPersistenceService(db_session)

        song = Song(
            name="Imagine",
            artists=["John Lennon"],
            artist="John Lennon",
            duration=183,
            platform=Platform.SPOTIFY,
            platform_id="song456",
            url="https://open.spotify.com/track/song456",
        )

        # Create first time
        song_model1, created1 = await service.persist_song(song)
        assert created1 is True

        # Try to create again
        song_model2, created2 = await service.persist_song(song)
        assert created2 is False
        assert song_model2.id == song_model1.id

    async def test_update_links_when_missing(self, db_session) -> None:
        """Test updating artist/album links when they're missing."""
        service = EntityPersistenceService(db_session)

        artist, _ = await service.find_or_create_artist(
            name="The Beatles",
            platform="spotify",
            platform_id="artist123",
            platform_url="https://open.spotify.com/artist/artist123",
        )

        album, _ = await service.find_or_create_album(
            name="Let It Be",
            artist_name="The Beatles",
            platform="spotify",
            platform_id="album123",
            platform_url="https://open.spotify.com/album/album123",
            artist_id=artist.id,
        )

        song = Song(
            name="Let It Be",
            artists=["The Beatles"],
            artist="The Beatles",
            duration=243,
            platform=Platform.SPOTIFY,
            platform_id="song789",
            url="https://open.spotify.com/track/song789",
            album_name="Let It Be",
        )

        # Create without links
        song_model1, _ = await service.persist_song(song)
        assert song_model1.artist_id is None
        assert song_model1.album_id is None

        # Update with links
        song_model2, created = await service.persist_song(
            song, artist_id=artist.id, album_id=album.id
        )
        assert created is False
        assert song_model2.artist_id == artist.id
        assert song_model2.album_id == album.id

    async def test_enriched_at_set_when_genres_present(self, db_session) -> None:
        """Test that enriched_at is set when genres are present."""
        service = EntityPersistenceService(db_session)

        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="song_enriched",
            url="https://open.spotify.com/track/song_enriched",
            genres=["rock", "pop"],
        )

        song_model, created = await service.persist_song(song)
        assert created is True
        assert song_model.enriched_at is not None

    async def test_enriched_at_not_set_without_genres(self, db_session) -> None:
        """Test that enriched_at is not set when genres are missing."""
        service = EntityPersistenceService(db_session)

        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="song_not_enriched",
            url="https://open.spotify.com/track/song_not_enriched",
        )

        song_model, created = await service.persist_song(song)
        assert created is True
        assert song_model.enriched_at is None

    async def test_handle_invalid_year(self, db_session) -> None:
        """Test handling invalid year gracefully."""
        service = EntityPersistenceService(db_session)

        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="song_bad_year",
            url="https://open.spotify.com/track/song_bad_year",
            year=99999,  # Invalid year
        )

        # Should not raise exception
        song_model, created = await service.persist_song(song)
        assert created is True
        assert song_model.release_date is None


@pytest.mark.asyncio
class TestPersistFromSearch:
    """Tests for persist_from_search method."""

    async def test_persist_single_song(self, db_session) -> None:
        """Test persisting a single song from search results."""
        service = EntityPersistenceService(db_session)

        songs = [
            Song(
                name="Stairway to Heaven",
                artists=["Led Zeppelin"],
                artist="Led Zeppelin",
                duration=482,
                platform=Platform.SPOTIFY,
                platform_id="song1",
                url="https://open.spotify.com/track/song1",
                album_name="Led Zeppelin IV",
                artist_id="artist1",
                album_id="album1",
                year=1971,
            )
        ]

        result = await service.persist_from_search(songs)

        assert result.artists_created == 1
        assert result.albums_created == 1
        assert result.songs_created == 1
        assert result.total_created == 3
        assert "led zeppelin" in result.artist_ids
        assert "led zeppelin:led zeppelin iv" in result.album_ids
        assert "spotify:song1" in result.song_ids

    async def test_persist_multiple_songs_same_artist(self, db_session) -> None:
        """Test persisting multiple songs from same artist."""
        service = EntityPersistenceService(db_session)

        songs = [
            Song(
                name="Song 1",
                artists=["Artist One"],
                artist="Artist One",
                duration=200,
                platform=Platform.SPOTIFY,
                platform_id="song1",
                url="https://open.spotify.com/track/song1",
                album_name="Album One",
                artist_id="artist1",
                album_id="album1",
            ),
            Song(
                name="Song 2",
                artists=["Artist One"],
                artist="Artist One",
                duration=220,
                platform=Platform.SPOTIFY,
                platform_id="song2",
                url="https://open.spotify.com/track/song2",
                album_name="Album One",
                artist_id="artist1",
                album_id="album1",
            ),
        ]

        result = await service.persist_from_search(songs)

        assert result.artists_created == 1
        assert result.albums_created == 1
        assert result.songs_created == 2

    async def test_persist_songs_different_albums(self, db_session) -> None:
        """Test persisting songs from different albums."""
        service = EntityPersistenceService(db_session)

        songs = [
            Song(
                name="Song 1",
                artists=["Artist"],
                artist="Artist",
                duration=200,
                platform=Platform.SPOTIFY,
                platform_id="song1",
                url="https://open.spotify.com/track/song1",
                album_name="Album One",
                artist_id="artist1",
                album_id="album1",
            ),
            Song(
                name="Song 2",
                artists=["Artist"],
                artist="Artist",
                duration=220,
                platform=Platform.SPOTIFY,
                platform_id="song2",
                url="https://open.spotify.com/track/song2",
                album_name="Album Two",
                artist_id="artist1",
                album_id="album2",
            ),
        ]

        result = await service.persist_from_search(songs)

        assert result.artists_created == 1
        assert result.albums_created == 2
        assert result.songs_created == 2

    async def test_persist_songs_without_album(self, db_session) -> None:
        """Test persisting songs without album information."""
        service = EntityPersistenceService(db_session)

        songs = [
            Song(
                name="Single Track",
                artists=["Solo Artist"],
                artist="Solo Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id="single1",
                url="https://open.spotify.com/track/single1",
                artist_id="artist1",
            )
        ]

        result = await service.persist_from_search(songs)

        assert result.artists_created == 1
        assert result.albums_created == 0
        assert result.songs_created == 1

    async def test_persist_handles_errors_gracefully(self, db_session) -> None:
        """Test that persist_from_search handles individual song errors."""
        service = EntityPersistenceService(db_session)

        songs = [
            Song(
                name="Good Song",
                artists=["Artist"],
                artist="Artist",
                duration=200,
                platform=Platform.SPOTIFY,
                platform_id="good1",
                url="https://open.spotify.com/track/good1",
            ),
            Song(
                name="Bad Song",
                artists=[],  # Missing artist - might cause issues
                artist="",
                duration=0,
                platform=Platform.SPOTIFY,
                platform_id="bad1",
                url="https://open.spotify.com/track/bad1",
            ),
        ]

        # Should not raise exception
        result = await service.persist_from_search(songs)

        # At least the good song should be persisted
        assert result.songs_created >= 1

    async def test_deduplication_same_song(self, db_session) -> None:
        """Test that same song is not created twice."""
        service = EntityPersistenceService(db_session)

        songs = [
            Song(
                name="Test Song",
                artists=["Test Artist"],
                artist="Test Artist",
                duration=200,
                platform=Platform.SPOTIFY,
                platform_id="same1",
                url="https://open.spotify.com/track/same1",
            ),
            Song(
                name="Test Song",
                artists=["Test Artist"],
                artist="Test Artist",
                duration=200,
                platform=Platform.SPOTIFY,
                platform_id="same1",
                url="https://open.spotify.com/track/same1",
            ),
        ]

        result = await service.persist_from_search(songs)

        assert result.songs_created == 1
        assert result.songs_linked == 1


@pytest.mark.asyncio
class TestGetMethods:
    """Tests for get_*_by_internal_id methods."""

    async def test_get_artist_by_internal_id(self, db_session) -> None:
        """Test getting artist by internal UUID."""
        service = EntityPersistenceService(db_session)

        artist, _ = await service.find_or_create_artist(
            name="Test Artist",
            platform="spotify",
            platform_id="artist1",
            platform_url="https://open.spotify.com/artist/artist1",
        )

        retrieved = await service.get_artist_by_internal_id(artist.id)
        assert retrieved is not None
        assert retrieved.id == artist.id
        assert retrieved.name == "Test Artist"

    async def test_get_artist_not_found(self, db_session) -> None:
        """Test getting non-existent artist."""
        service = EntityPersistenceService(db_session)

        retrieved = await service.get_artist_by_internal_id(uuid.uuid4())
        assert retrieved is None

    async def test_get_album_by_internal_id(self, db_session) -> None:
        """Test getting album by internal UUID."""
        service = EntityPersistenceService(db_session)

        album, _ = await service.find_or_create_album(
            name="Test Album",
            artist_name="Test Artist",
            platform="spotify",
            platform_id="album1",
            platform_url="https://open.spotify.com/album/album1",
        )

        retrieved = await service.get_album_by_internal_id(album.id)
        assert retrieved is not None
        assert retrieved.id == album.id
        assert retrieved.name == "Test Album"

    async def test_get_playlist_by_internal_id(self, db_session) -> None:
        """Test getting playlist by internal UUID."""
        service = EntityPersistenceService(db_session)

        playlist, _ = await service.find_or_create_playlist(
            name="Test Playlist",
            platform="spotify",
            platform_id="playlist1",
            platform_url="https://open.spotify.com/playlist/playlist1",
        )

        retrieved = await service.get_playlist_by_internal_id(playlist.id)
        assert retrieved is not None
        assert retrieved.id == playlist.id
        assert retrieved.name == "Test Playlist"

    async def test_get_song_by_internal_id(self, db_session) -> None:
        """Test getting song by internal UUID."""
        service = EntityPersistenceService(db_session)

        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="song1",
            url="https://open.spotify.com/track/song1",
        )

        song_model, _ = await service.persist_song(song)

        retrieved = await service.get_song_by_internal_id(song_model.id)
        assert retrieved is not None
        assert retrieved.id == song_model.id
        assert retrieved.name == "Test Song"


@pytest.mark.asyncio
class TestEnrichArtistsWithImages:
    """Tests for enrich_artists_with_images method."""

    async def test_no_spotify_provider(self, db_session) -> None:
        """Test enrichment when Spotify provider is not available."""
        service = EntityPersistenceService(db_session)

        mock_song_service = MagicMock()
        mock_song_service._providers = {}

        count = await service.enrich_artists_with_images([], mock_song_service)
        assert count == 0

    async def test_skip_artist_with_image(self, db_session) -> None:
        """Test that artists with images are skipped."""
        service = EntityPersistenceService(db_session)

        artist, _ = await service.find_or_create_artist(
            name="Test Artist",
            platform="spotify",
            platform_id="spotify123",
            platform_url="https://open.spotify.com/artist/spotify123",
            image_url="https://example.com/existing.jpg",
        )

        mock_song_service = MagicMock()
        mock_provider = MagicMock()
        mock_song_service._providers = {Platform.SPOTIFY: mock_provider}

        count = await service.enrich_artists_with_images([artist.id], mock_song_service)
        assert count == 0

    async def test_skip_artist_without_spotify_link(self, db_session) -> None:
        """Test that artists without Spotify links are skipped."""
        service = EntityPersistenceService(db_session)

        artist, _ = await service.find_or_create_artist(
            name="Test Artist",
            platform="deezer",
            platform_id="deezer123",
            platform_url="https://deezer.com/artist/deezer123",
        )

        mock_song_service = MagicMock()
        mock_provider = MagicMock()
        mock_song_service._providers = {Platform.SPOTIFY: mock_provider}

        count = await service.enrich_artists_with_images([artist.id], mock_song_service)
        assert count == 0

    async def test_enrich_artist_with_image(self, db_session) -> None:
        """Test successful artist enrichment with image."""
        service = EntityPersistenceService(db_session)

        artist, _ = await service.find_or_create_artist(
            name="Test Artist",
            platform="spotify",
            platform_id="spotify123",
            platform_url="https://open.spotify.com/artist/spotify123",
        )

        # Mock Spotify client response
        mock_client = MagicMock()
        mock_client.artist.return_value = {
            "images": [
                {"url": "https://example.com/small.jpg", "width": 160, "height": 160},
                {"url": "https://example.com/large.jpg", "width": 640, "height": 640},
            ],
            "genres": ["rock", "pop"],
            "followers": {"total": 50000},
        }

        mock_provider = MagicMock()
        mock_provider._get_client.return_value = mock_client

        mock_song_service = MagicMock()
        mock_song_service._providers = {Platform.SPOTIFY: mock_provider}

        count = await service.enrich_artists_with_images([artist.id], mock_song_service)
        assert count == 1

        # Verify artist was updated
        updated_artist = await service.get_artist_by_internal_id(artist.id)
        assert updated_artist.image_url == "https://example.com/large.jpg"
        assert "rock" in updated_artist.genres
        assert "pop" in updated_artist.genres

    async def test_handle_enrichment_errors_gracefully(self, db_session) -> None:
        """Test that errors during enrichment are handled gracefully."""
        service = EntityPersistenceService(db_session)

        artist, _ = await service.find_or_create_artist(
            name="Test Artist",
            platform="spotify",
            platform_id="spotify123",
            platform_url="https://open.spotify.com/artist/spotify123",
        )

        # Mock client to raise exception
        mock_client = MagicMock()
        mock_client.artist.side_effect = Exception("API error")

        mock_provider = MagicMock()
        mock_provider._get_client.return_value = mock_client

        mock_song_service = MagicMock()
        mock_song_service._providers = {Platform.SPOTIFY: mock_provider}

        # Should not raise exception
        count = await service.enrich_artists_with_images([artist.id], mock_song_service)
        assert count == 0


@pytest.mark.asyncio
class TestFullEnrichSong:
    """Tests for full_enrich_song method."""

    async def test_song_not_found(self, db_session) -> None:
        """Test enrichment fails when song is not found."""
        service = EntityPersistenceService(db_session)

        mock_metadata_service = MagicMock()
        mock_lyrics_service = MagicMock()

        with pytest.raises(EntityPersistenceError, match="Song not found"):
            await service.full_enrich_song(
                uuid.uuid4(), mock_metadata_service, mock_lyrics_service
            )

    async def test_full_enrichment_success(self, db_session) -> None:
        """Test successful full enrichment."""
        service = EntityPersistenceService(db_session)

        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="song1",
            url="https://open.spotify.com/track/song1",
            isrc="USRC12345678",
        )

        song_model, _ = await service.persist_song(song)
        assert song_model.enriched_at is None

        # Mock metadata service
        mock_metadata_service = AsyncMock()
        mock_snapshot = MagicMock()
        mock_snapshot.confidence = 0.9
        mock_snapshot.snapshot_data = {
            "genres": ["rock", "pop"],
            "year": 2020,
            "isrc": "USRC12345678",
        }
        mock_metadata_service.fetch_all_snapshots = AsyncMock(return_value=[mock_snapshot])

        # Mock lyrics service
        mock_lyrics_service = AsyncMock()
        mock_lyrics_service.__aenter__ = AsyncMock(return_value=mock_lyrics_service)
        mock_lyrics_service.__aexit__ = AsyncMock(return_value=None)
        mock_lyrics_service.fetch_all_lyrics = AsyncMock(
            return_value=[{"source": "genius", "lyrics": "test lyrics"}]
        )

        result = await service.full_enrich_song(
            song_model.id, mock_metadata_service, mock_lyrics_service
        )

        assert result.metadata_sources_count == 1
        assert result.lyrics_sources_count == 1

        # Verify song was updated
        updated_song = await service.get_song_by_internal_id(song_model.id)
        assert updated_song.enriched_at is not None
        assert updated_song.genres == ["rock", "pop"]

    async def test_enrichment_handles_metadata_errors(self, db_session) -> None:
        """Test that metadata errors are handled gracefully."""
        service = EntityPersistenceService(db_session)

        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="song1",
            url="https://open.spotify.com/track/song1",
        )

        song_model, _ = await service.persist_song(song)

        # Mock metadata service to fail
        mock_metadata_service = AsyncMock()
        mock_metadata_service.fetch_all_snapshots = AsyncMock(
            side_effect=Exception("Metadata error")
        )

        # Mock lyrics service
        mock_lyrics_service = AsyncMock()
        mock_lyrics_service.__aenter__ = AsyncMock(return_value=mock_lyrics_service)
        mock_lyrics_service.__aexit__ = AsyncMock(return_value=None)
        mock_lyrics_service.fetch_all_lyrics = AsyncMock(return_value=[])

        # Should not raise exception
        result = await service.full_enrich_song(
            song_model.id, mock_metadata_service, mock_lyrics_service
        )

        assert result.metadata_sources_count == 0
        assert result.lyrics_sources_count == 0

        # enriched_at should still be set
        updated_song = await service.get_song_by_internal_id(song_model.id)
        assert updated_song.enriched_at is not None

    async def test_enrichment_handles_lyrics_errors(self, db_session) -> None:
        """Test that lyrics errors are handled gracefully."""
        service = EntityPersistenceService(db_session)

        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="song1",
            url="https://open.spotify.com/track/song1",
        )

        song_model, _ = await service.persist_song(song)

        # Mock metadata service
        mock_metadata_service = AsyncMock()
        mock_metadata_service.fetch_all_snapshots = AsyncMock(return_value=[])

        # Mock lyrics service to fail
        mock_lyrics_service = AsyncMock()
        mock_lyrics_service.__aenter__ = AsyncMock(return_value=mock_lyrics_service)
        mock_lyrics_service.__aexit__ = AsyncMock(return_value=None)
        mock_lyrics_service.fetch_all_lyrics = AsyncMock(side_effect=Exception("Lyrics error"))

        # Should not raise exception
        result = await service.full_enrich_song(
            song_model.id, mock_metadata_service, mock_lyrics_service
        )

        assert result.metadata_sources_count == 0
        assert result.lyrics_sources_count == 0


class TestEnrichmentResult:
    """Tests for EnrichmentResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        result = EnrichmentResult()
        assert result.metadata_sources_count == 0
        assert result.lyrics_sources_count == 0
        assert len(result.metadata_snapshots) == 0


class TestEntityPersistenceError:
    """Tests for EntityPersistenceError exception."""

    def test_error_message(self) -> None:
        """Test error message."""
        error = EntityPersistenceError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
