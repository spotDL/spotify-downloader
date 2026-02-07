"""Tests for database repositories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.db.models.album import Album
from spotdl.db.models.artist import Artist
from spotdl.db.models.playlist import Playlist
from spotdl.db.models.lyrics import Lyrics
from spotdl.db.repositories.album import AlbumRepository
from spotdl.db.repositories.artist import ArtistRepository
from spotdl.db.repositories.playlist import PlaylistRepository
from spotdl.db.repositories.lyrics import LyricsRepository


pytestmark = pytest.mark.asyncio


class TestAlbumRepository:
    """Tests for AlbumRepository."""

    async def test_create_album(self, db_session: AsyncSession) -> None:
        """Test creating an album."""
        repo = AlbumRepository(db_session)
        album = await repo.create(
            spotify_id="album123",
            name="Test Album",
            artist_name="Test Artist",
            release_date="2024-01-01",
            total_tracks=10,
        )

        assert album.id is not None
        assert album.spotify_id == "album123"
        assert album.name == "Test Album"

    async def test_get_album_by_spotify_id(self, db_session: AsyncSession) -> None:
        """Test getting album by Spotify ID."""
        repo = AlbumRepository(db_session)
        await repo.create(
            spotify_id="album456",
            name="Another Album",
            artist_name="Artist",
        )

        album = await repo.get_by_spotify_id("album456")
        assert album is not None
        assert album.spotify_id == "album456"

    async def test_get_album_by_nonexistent_id(self, db_session: AsyncSession) -> None:
        """Test getting nonexistent album returns None."""
        repo = AlbumRepository(db_session)
        album = await repo.get_by_spotify_id("nonexistent")
        assert album is None


class TestArtistRepository:
    """Tests for ArtistRepository."""

    async def test_create_artist(self, db_session: AsyncSession) -> None:
        """Test creating an artist."""
        repo = ArtistRepository(db_session)
        artist = await repo.create(
            spotify_id="artist123",
            name="Test Artist",
        )

        assert artist.id is not None
        assert artist.spotify_id == "artist123"
        assert artist.name == "Test Artist"

    async def test_get_artist_by_spotify_id(self, db_session: AsyncSession) -> None:
        """Test getting artist by Spotify ID."""
        repo = ArtistRepository(db_session)
        await repo.create(spotify_id="artist456", name="Another Artist")

        artist = await repo.get_by_spotify_id("artist456")
        assert artist is not None
        assert artist.spotify_id == "artist456"


class TestPlaylistRepository:
    """Tests for PlaylistRepository."""

    async def test_create_playlist(self, db_session: AsyncSession) -> None:
        """Test creating a playlist."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            spotify_id="playlist123",
            name="Test Playlist",
            owner="User1",
        )

        assert playlist.id is not None
        assert playlist.spotify_id == "playlist123"
        assert playlist.name == "Test Playlist"


class TestLyricsRepository:
    """Tests for LyricsRepository."""

    async def test_get_lyrics_by_isrc(self, db_session: AsyncSession) -> None:
        """Test getting lyrics by ISRC."""
        repo = LyricsRepository(db_session)

        # Create lyrics entry
        lyrics = Lyrics(
            isrc="USABC1234567",
            text="Test lyrics content",
            source="test_source",
        )
        db_session.add(lyrics)
        await db_session.commit()

        # Retrieve
        found = await repo.get_by_isrc("USABC1234567")
        assert found is not None
        assert found.text == "Test lyrics content"
