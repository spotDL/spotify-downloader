"""Tests for database repositories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from slugify import slugify

from spotdl.db.models.album import Album, AlbumPlatformLink
from spotdl.db.models.artist import Artist
from spotdl.db.models.playlist import Playlist
from spotdl.db.models.lyrics import Lyrics
from spotdl.db.models.user_settings import UserSettings
from spotdl.db.models.refresh_cooldown import RefreshCooldown
from spotdl.db.repositories.album import AlbumRepository
from spotdl.db.repositories.artist import ArtistRepository
from spotdl.db.repositories.playlist import PlaylistRepository
from spotdl.db.repositories.lyrics import LyricsRepository
from spotdl.db.repositories.user_settings import UserSettingsRepository
from spotdl.db.repositories.refresh_cooldown import RefreshCooldownRepository


pytestmark = pytest.mark.asyncio


class TestAlbumRepository:
    """Tests for AlbumRepository."""

    async def test_create_album(self, db_session: AsyncSession) -> None:
        """Test creating an album."""
        repo = AlbumRepository(db_session)
        album = Album(
            name="Test Album",
            name_normalized=slugify("Test Album"),
            artist_name="Test Artist",
            total_tracks=10,
        )
        db_session.add(album)
        await db_session.commit()
        await db_session.refresh(album)

        assert album.id is not None
        assert album.name == "Test Album"
        assert album.artist_name == "Test Artist"

    async def test_get_by_normalized_name_and_artist(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting album by normalized name."""
        repo = AlbumRepository(db_session)
        album = Album(
            name="Another Album",
            name_normalized=slugify("Another Album"),
            artist_name="Artist",
        )
        db_session.add(album)
        await db_session.commit()

        found = await repo.get_by_normalized_name_and_artist(slugify("Another Album"))
        assert found is not None
        assert found.name == "Another Album"

    async def test_get_album_by_platform_id(self, db_session: AsyncSession) -> None:
        """Test getting album by platform ID."""
        repo = AlbumRepository(db_session)
        album = Album(
            name="Platform Album",
            name_normalized=slugify("Platform Album"),
            artist_name="Artist",
        )
        db_session.add(album)
        await db_session.flush()

        link = AlbumPlatformLink(
            album_id=album.id,
            platform="spotify",
            platform_id="album789",
            platform_url="https://open.spotify.com/album/album789",
        )
        db_session.add(link)
        await db_session.commit()

        found = await repo.get_by_platform_id("spotify", "album789")
        assert found is not None
        assert found.name == "Platform Album"


class TestArtistRepository:
    """Tests for ArtistRepository."""

    async def test_create_artist(self, db_session: AsyncSession) -> None:
        """Test creating an artist."""
        artist = Artist(
            name="Test Artist",
            name_normalized=slugify("Test Artist"),
        )
        db_session.add(artist)
        await db_session.commit()
        await db_session.refresh(artist)

        assert artist.id is not None
        assert artist.name == "Test Artist"

    async def test_get_artist_by_normalized_name(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting artist by normalized name."""
        repo = ArtistRepository(db_session)
        artist = Artist(
            name="Another Artist",
            name_normalized=slugify("Another Artist"),
        )
        db_session.add(artist)
        await db_session.commit()

        found = await repo.get_by_normalized_name(slugify("Another Artist"))
        assert found is not None
        assert found.name == "Another Artist"


class TestPlaylistRepository:
    """Tests for PlaylistRepository."""

    async def test_create_playlist(self, db_session: AsyncSession) -> None:
        """Test creating a playlist."""
        playlist = Playlist(
            name="Test Playlist",
            name_normalized=slugify("Test Playlist"),
            owner_name="User1",
        )
        db_session.add(playlist)
        await db_session.commit()
        await db_session.refresh(playlist)

        assert playlist.id is not None
        assert playlist.name == "Test Playlist"
        assert playlist.owner_name == "User1"


class TestLyricsRepository:
    """Tests for LyricsRepository."""

    async def test_lyrics_repository_exists(self, db_session: AsyncSession) -> None:
        """Test lyrics repository can be instantiated."""
        repo = LyricsRepository(db_session)
        assert repo is not None
