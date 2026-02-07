"""Tests for database repositories."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from slugify import slugify

from spotdl.db.models.album import Album, AlbumPlatformLink
from spotdl.db.models.artist import Artist, ArtistPlatformLink
from spotdl.db.models.playlist import Playlist, PlaylistPlatformLink, PlaylistTrack
from spotdl.db.models.lyrics import Lyrics
from spotdl.db.models.user_settings import UserSettings
from spotdl.db.models.song import Song
from spotdl.db.models.metadata_snapshot import MetadataSnapshot
from spotdl.db.models.user import User
from spotdl.db.repositories.album import AlbumRepository
from spotdl.db.repositories.artist import ArtistRepository
from spotdl.db.repositories.playlist import PlaylistRepository
from spotdl.db.repositories.lyrics import LyricsRepository
from spotdl.db.repositories.user_settings import UserSettingsRepository
from spotdl.db.repositories.metadata_snapshot import MetadataSnapshotRepository


pytestmark = pytest.mark.asyncio


def create_test_song(name: str = "Song", platform_id: str = "test123") -> Song:
    """Helper to create a test song."""
    return Song(
        name=name,
        artists=["Artist"],
        platform="spotify",
        platform_id=platform_id,
        platform_url=f"https://open.spotify.com/track/{platform_id}",
        duration_seconds=180
    )


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

    async def test_get_by_id(self, db_session: AsyncSession) -> None:
        """Test getting album by ID."""
        repo = AlbumRepository(db_session)
        album = await repo.create(
            name="Get By ID Album",
            name_normalized=slugify("Get By ID Album"),
            artist_name="Test Artist",
        )
        await db_session.commit()

        found = await repo.get_by_id(album.id)
        assert found is not None
        assert found.id == album.id
        assert found.name == "Get By ID Album"

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        """Test getting non-existent album by ID."""
        repo = AlbumRepository(db_session)
        found = await repo.get_by_id(uuid.uuid4())
        assert found is None

    async def test_get_by_id_with_links(self, db_session: AsyncSession) -> None:
        """Test getting album by ID with platform links loaded."""
        repo = AlbumRepository(db_session)
        album = await repo.create(
            name="Links Album",
            name_normalized=slugify("Links Album"),
            artist_name="Test Artist",
        )
        await db_session.flush()

        await repo.add_platform_link(
            album.id, "spotify", "spotify123", "https://open.spotify.com/album/spotify123"
        )
        await repo.add_platform_link(
            album.id, "youtube", "youtube123", "https://music.youtube.com/album/youtube123"
        )
        await db_session.commit()

        found = await repo.get_by_id_with_links(album.id)
        assert found is not None
        assert len(found.platform_links) == 2

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

    async def test_get_by_normalized_name_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting non-existent album by normalized name."""
        repo = AlbumRepository(db_session)
        found = await repo.get_by_normalized_name_and_artist("nonexistent-album")
        assert found is None

    async def test_get_by_normalized_name_with_artist_id(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting album by normalized name and artist ID."""
        repo = AlbumRepository(db_session)

        artist = Artist(name="Test Artist", name_normalized=slugify("Test Artist"))
        db_session.add(artist)
        await db_session.flush()

        album = await repo.create(
            name="Artist Album",
            name_normalized=slugify("Artist Album"),
            artist_name="Test Artist",
            artist_id=artist.id,
        )
        await db_session.commit()

        found = await repo.get_by_normalized_name_and_artist(
            slugify("Artist Album"), artist.id
        )
        assert found is not None
        assert found.artist_id == artist.id

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

    async def test_get_by_platform_id_not_found(self, db_session: AsyncSession) -> None:
        """Test getting album by non-existent platform ID."""
        repo = AlbumRepository(db_session)
        found = await repo.get_by_platform_id("spotify", "nonexistent")
        assert found is None

    async def test_get_by_artist_id(self, db_session: AsyncSession) -> None:
        """Test getting albums by artist ID."""
        repo = AlbumRepository(db_session)

        artist = Artist(name="Artist", name_normalized=slugify("Artist"))
        db_session.add(artist)
        await db_session.flush()

        album1 = await repo.create(
            name="Album 1", name_normalized=slugify("Album 1"),
            artist_name="Artist", artist_id=artist.id
        )
        album2 = await repo.create(
            name="Album 2", name_normalized=slugify("Album 2"),
            artist_name="Artist", artist_id=artist.id
        )
        await db_session.commit()

        albums = await repo.get_by_artist_id(artist.id)
        assert len(albums) == 2
        assert {a.name for a in albums} == {"Album 1", "Album 2"}

    async def test_get_by_artist_id_with_limit(self, db_session: AsyncSession) -> None:
        """Test getting albums by artist ID with limit."""
        repo = AlbumRepository(db_session)

        artist = Artist(name="Artist", name_normalized=slugify("Artist"))
        db_session.add(artist)
        await db_session.flush()

        for i in range(5):
            await repo.create(
                name=f"Album {i}", name_normalized=slugify(f"Album {i}"),
                artist_name="Artist", artist_id=artist.id
            )
        await db_session.commit()

        albums = await repo.get_by_artist_id(artist.id, limit=3)
        assert len(albums) == 3

    async def test_search_by_name(self, db_session: AsyncSession) -> None:
        """Test searching albums by name."""
        repo = AlbumRepository(db_session)

        await repo.create(
            name="Dark Side of the Moon",
            name_normalized=slugify("Dark Side of the Moon"),
            artist_name="Pink Floyd",
        )
        await repo.create(
            name="The Dark Knight Soundtrack",
            name_normalized=slugify("The Dark Knight Soundtrack"),
            artist_name="Hans Zimmer",
        )
        await repo.create(
            name="Abbey Road",
            name_normalized=slugify("Abbey Road"),
            artist_name="The Beatles",
        )
        await db_session.commit()

        results = await repo.search_by_name("dark")
        assert len(results) == 2
        assert all("dark" in r.name.lower() for r in results)

    async def test_search_by_name_case_insensitive(
        self, db_session: AsyncSession
    ) -> None:
        """Test search is case-insensitive."""
        repo = AlbumRepository(db_session)

        await repo.create(
            name="Test Album",
            name_normalized=slugify("Test Album"),
            artist_name="Artist",
        )
        await db_session.commit()

        results = await repo.search_by_name("TEST")
        assert len(results) == 1

    async def test_search_by_name_with_limit(self, db_session: AsyncSession) -> None:
        """Test searching albums with limit."""
        repo = AlbumRepository(db_session)

        for i in range(10):
            await repo.create(
                name=f"Album {i}",
                name_normalized=slugify(f"Album {i}"),
                artist_name="Artist",
            )
        await db_session.commit()

        results = await repo.search_by_name("Album", limit=5)
        assert len(results) == 5

    async def test_add_platform_link(self, db_session: AsyncSession) -> None:
        """Test adding a platform link to an album."""
        repo = AlbumRepository(db_session)
        album = await repo.create(
            name="Album", name_normalized=slugify("Album"), artist_name="Artist"
        )
        await db_session.flush()

        link = await repo.add_platform_link(
            album.id, "spotify", "abc123", "https://open.spotify.com/album/abc123"
        )
        await db_session.commit()

        assert link.album_id == album.id
        assert link.platform == "spotify"
        assert link.platform_id == "abc123"

    async def test_add_platform_link_duplicate(self, db_session: AsyncSession) -> None:
        """Test adding duplicate platform link returns existing one."""
        repo = AlbumRepository(db_session)
        album = await repo.create(
            name="Album", name_normalized=slugify("Album"), artist_name="Artist"
        )
        await db_session.flush()

        link1 = await repo.add_platform_link(
            album.id, "spotify", "abc123", "https://open.spotify.com/album/abc123"
        )
        await db_session.commit()

        link2 = await repo.add_platform_link(
            album.id, "spotify", "abc123", "https://open.spotify.com/album/abc123"
        )
        assert link1.id == link2.id

    async def test_get_platform_link(self, db_session: AsyncSession) -> None:
        """Test getting a platform link."""
        repo = AlbumRepository(db_session)
        album = await repo.create(
            name="Album", name_normalized=slugify("Album"), artist_name="Artist"
        )
        await db_session.flush()

        await repo.add_platform_link(
            album.id, "spotify", "xyz789", "https://open.spotify.com/album/xyz789"
        )
        await db_session.commit()

        link = await repo.get_platform_link("spotify", "xyz789")
        assert link is not None
        assert link.platform_id == "xyz789"

    async def test_get_platform_link_not_found(self, db_session: AsyncSession) -> None:
        """Test getting non-existent platform link."""
        repo = AlbumRepository(db_session)
        link = await repo.get_platform_link("spotify", "nonexistent")
        assert link is None

    async def test_get_song_counts_by_album_ids(self, db_session: AsyncSession) -> None:
        """Test getting song counts for albums."""
        repo = AlbumRepository(db_session)

        album1 = await repo.create(
            name="Album 1", name_normalized=slugify("Album 1"), artist_name="Artist"
        )
        album2 = await repo.create(
            name="Album 2", name_normalized=slugify("Album 2"), artist_name="Artist"
        )
        await db_session.flush()

        # Add songs to albums
        for i in range(3):
            song = Song(
                name=f"Song {i}",
                artists=["Artist"],
                platform="spotify",
                platform_id=f"song{i}",
                platform_url=f"https://open.spotify.com/track/song{i}",
                duration_seconds=180,
                album_id=album1.id
            )
            db_session.add(song)

        for i in range(5):
            song = Song(
                name=f"Song {i+3}",
                artists=["Artist"],
                platform="spotify",
                platform_id=f"song{i+3}",
                platform_url=f"https://open.spotify.com/track/song{i+3}",
                duration_seconds=180,
                album_id=album2.id
            )
            db_session.add(song)
        await db_session.commit()

        counts = await repo.get_song_counts_by_album_ids([album1.id, album2.id])
        assert counts[album1.id] == 3
        assert counts[album2.id] == 5

    async def test_get_song_counts_empty_list(self, db_session: AsyncSession) -> None:
        """Test getting song counts with empty list."""
        repo = AlbumRepository(db_session)
        counts = await repo.get_song_counts_by_album_ids([])
        assert counts == {}

    async def test_get_all(self, db_session: AsyncSession) -> None:
        """Test getting all albums."""
        repo = AlbumRepository(db_session)

        for i in range(5):
            await repo.create(
                name=f"Album {i}", name_normalized=slugify(f"Album {i}"),
                artist_name="Artist"
            )
        await db_session.commit()

        albums = await repo.get_all()
        assert len(albums) == 5

    async def test_get_all_with_pagination(self, db_session: AsyncSession) -> None:
        """Test getting all albums with pagination."""
        repo = AlbumRepository(db_session)

        for i in range(10):
            await repo.create(
                name=f"Album {i}", name_normalized=slugify(f"Album {i}"),
                artist_name="Artist"
            )
        await db_session.commit()

        albums = await repo.get_all(skip=2, limit=5)
        assert len(albums) == 5

    async def test_count(self, db_session: AsyncSession) -> None:
        """Test counting albums."""
        repo = AlbumRepository(db_session)

        for i in range(7):
            await repo.create(
                name=f"Album {i}", name_normalized=slugify(f"Album {i}"),
                artist_name="Artist"
            )
        await db_session.commit()

        count = await repo.count()
        assert count == 7

    async def test_update(self, db_session: AsyncSession) -> None:
        """Test updating an album."""
        repo = AlbumRepository(db_session)
        album = await repo.create(
            name="Old Name", name_normalized=slugify("Old Name"), artist_name="Artist"
        )
        await db_session.commit()

        updated = await repo.update(album.id, name="New Name")
        assert updated is not None
        assert updated.name == "New Name"

    async def test_update_not_found(self, db_session: AsyncSession) -> None:
        """Test updating non-existent album."""
        repo = AlbumRepository(db_session)
        updated = await repo.update(uuid.uuid4(), name="New Name")
        assert updated is None

    async def test_delete(self, db_session: AsyncSession) -> None:
        """Test deleting an album."""
        repo = AlbumRepository(db_session)
        album = await repo.create(
            name="To Delete", name_normalized=slugify("To Delete"), artist_name="Artist"
        )
        await db_session.commit()

        result = await repo.delete(album.id)
        assert result is True

        found = await repo.get_by_id(album.id)
        assert found is None

    async def test_delete_not_found(self, db_session: AsyncSession) -> None:
        """Test deleting non-existent album."""
        repo = AlbumRepository(db_session)
        result = await repo.delete(uuid.uuid4())
        assert result is False


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

    async def test_get_by_id(self, db_session: AsyncSession) -> None:
        """Test getting artist by ID."""
        repo = ArtistRepository(db_session)
        artist = await repo.create(
            name="Test Artist", name_normalized=slugify("Test Artist")
        )
        await db_session.commit()

        found = await repo.get_by_id(artist.id)
        assert found is not None
        assert found.id == artist.id

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        """Test getting non-existent artist by ID."""
        repo = ArtistRepository(db_session)
        found = await repo.get_by_id(uuid.uuid4())
        assert found is None

    async def test_get_by_id_with_links(self, db_session: AsyncSession) -> None:
        """Test getting artist with platform links."""
        repo = ArtistRepository(db_session)
        artist = await repo.create(
            name="Artist", name_normalized=slugify("Artist")
        )
        await db_session.flush()

        await repo.add_platform_link(
            artist.id, "spotify", "spot123", "https://open.spotify.com/artist/spot123"
        )
        await db_session.commit()

        found = await repo.get_by_id_with_links(artist.id)
        assert found is not None
        assert len(found.platform_links) == 1

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

    async def test_get_by_normalized_name_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting non-existent artist by normalized name."""
        repo = ArtistRepository(db_session)
        found = await repo.get_by_normalized_name("nonexistent-artist")
        assert found is None

    async def test_get_by_platform_id(self, db_session: AsyncSession) -> None:
        """Test getting artist by platform ID."""
        repo = ArtistRepository(db_session)
        artist = await repo.create(
            name="Platform Artist", name_normalized=slugify("Platform Artist")
        )
        await db_session.flush()

        await repo.add_platform_link(
            artist.id, "spotify", "artist123", "https://open.spotify.com/artist/artist123"
        )
        await db_session.commit()

        found = await repo.get_by_platform_id("spotify", "artist123")
        assert found is not None
        assert found.name == "Platform Artist"

    async def test_get_by_platform_id_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting artist by non-existent platform ID."""
        repo = ArtistRepository(db_session)
        found = await repo.get_by_platform_id("spotify", "nonexistent")
        assert found is None

    async def test_search_by_name(self, db_session: AsyncSession) -> None:
        """Test searching artists by name."""
        repo = ArtistRepository(db_session)

        await repo.create(name="The Beatles", name_normalized=slugify("The Beatles"))
        await repo.create(name="Beat Happening", name_normalized=slugify("Beat Happening"))
        await repo.create(name="Pink Floyd", name_normalized=slugify("Pink Floyd"))
        await db_session.commit()

        results = await repo.search_by_name("beat")
        assert len(results) == 2
        assert all("beat" in r.name.lower() for r in results)

    async def test_search_by_name_case_insensitive(
        self, db_session: AsyncSession
    ) -> None:
        """Test search is case-insensitive."""
        repo = ArtistRepository(db_session)

        await repo.create(name="Artist", name_normalized=slugify("Artist"))
        await db_session.commit()

        results = await repo.search_by_name("ARTIST")
        assert len(results) == 1

    async def test_search_by_name_with_limit(self, db_session: AsyncSession) -> None:
        """Test searching artists with limit."""
        repo = ArtistRepository(db_session)

        for i in range(10):
            await repo.create(name=f"Artist {i}", name_normalized=slugify(f"Artist {i}"))
        await db_session.commit()

        results = await repo.search_by_name("Artist", limit=5)
        assert len(results) == 5

    async def test_add_platform_link(self, db_session: AsyncSession) -> None:
        """Test adding a platform link."""
        repo = ArtistRepository(db_session)
        artist = await repo.create(name="Artist", name_normalized=slugify("Artist"))
        await db_session.flush()

        link = await repo.add_platform_link(
            artist.id, "spotify", "abc123", "https://open.spotify.com/artist/abc123",
            followers=1000
        )
        await db_session.commit()

        assert link.artist_id == artist.id
        assert link.platform == "spotify"
        assert link.followers == 1000

    async def test_add_platform_link_duplicate(self, db_session: AsyncSession) -> None:
        """Test adding duplicate platform link returns existing one."""
        repo = ArtistRepository(db_session)
        artist = await repo.create(name="Artist", name_normalized=slugify("Artist"))
        await db_session.flush()

        link1 = await repo.add_platform_link(
            artist.id, "spotify", "abc123", "https://open.spotify.com/artist/abc123"
        )
        await db_session.commit()

        link2 = await repo.add_platform_link(
            artist.id, "spotify", "abc123", "https://open.spotify.com/artist/abc123"
        )
        assert link1.id == link2.id

    async def test_get_platform_link(self, db_session: AsyncSession) -> None:
        """Test getting a platform link."""
        repo = ArtistRepository(db_session)
        artist = await repo.create(name="Artist", name_normalized=slugify("Artist"))
        await db_session.flush()

        await repo.add_platform_link(
            artist.id, "spotify", "xyz789", "https://open.spotify.com/artist/xyz789"
        )
        await db_session.commit()

        link = await repo.get_platform_link("spotify", "xyz789")
        assert link is not None
        assert link.platform_id == "xyz789"

    async def test_get_platform_link_not_found(self, db_session: AsyncSession) -> None:
        """Test getting non-existent platform link."""
        repo = ArtistRepository(db_session)
        link = await repo.get_platform_link("spotify", "nonexistent")
        assert link is None

    async def test_get_all(self, db_session: AsyncSession) -> None:
        """Test getting all artists."""
        repo = ArtistRepository(db_session)

        for i in range(5):
            await repo.create(name=f"Artist {i}", name_normalized=slugify(f"Artist {i}"))
        await db_session.commit()

        artists = await repo.get_all()
        assert len(artists) == 5

    async def test_count(self, db_session: AsyncSession) -> None:
        """Test counting artists."""
        repo = ArtistRepository(db_session)

        for i in range(3):
            await repo.create(name=f"Artist {i}", name_normalized=slugify(f"Artist {i}"))
        await db_session.commit()

        count = await repo.count()
        assert count == 3

    async def test_update(self, db_session: AsyncSession) -> None:
        """Test updating an artist."""
        repo = ArtistRepository(db_session)
        artist = await repo.create(name="Old Name", name_normalized=slugify("Old Name"))
        await db_session.commit()

        updated = await repo.update(artist.id, name="New Name")
        assert updated is not None
        assert updated.name == "New Name"

    async def test_delete(self, db_session: AsyncSession) -> None:
        """Test deleting an artist."""
        repo = ArtistRepository(db_session)
        artist = await repo.create(name="To Delete", name_normalized=slugify("To Delete"))
        await db_session.commit()

        result = await repo.delete(artist.id)
        assert result is True

        found = await repo.get_by_id(artist.id)
        assert found is None


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

    async def test_get_by_id(self, db_session: AsyncSession) -> None:
        """Test getting playlist by ID."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Test Playlist",
            name_normalized=slugify("Test Playlist"),
            owner_name="User1",
        )
        await db_session.commit()

        found = await repo.get_by_id(playlist.id)
        assert found is not None
        assert found.id == playlist.id

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        """Test getting non-existent playlist by ID."""
        repo = PlaylistRepository(db_session)
        found = await repo.get_by_id(uuid.uuid4())
        assert found is None

    async def test_get_by_id_with_links(self, db_session: AsyncSession) -> None:
        """Test getting playlist with platform links."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Playlist", name_normalized=slugify("Playlist"), owner_name="User"
        )
        await db_session.flush()

        await repo.add_platform_link(
            playlist.id, "spotify", "play123", "https://open.spotify.com/playlist/play123"
        )
        await db_session.commit()

        found = await repo.get_by_id_with_links(playlist.id)
        assert found is not None
        assert len(found.platform_links) == 1

    async def test_get_by_id_with_tracks(self, db_session: AsyncSession) -> None:
        """Test getting playlist with tracks loaded."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Playlist", name_normalized=slugify("Playlist"), owner_name="User"
        )
        await db_session.flush()

        # Create songs and add to playlist
        for i in range(3):
            song = Song(
                name=f"Song {i}",
                artists=["Artist"],
                platform="spotify",
                platform_id=f"song{i}",
                platform_url=f"https://open.spotify.com/track/song{i}",
                duration_seconds=180
            )
            db_session.add(song)
            await db_session.flush()
            await repo.add_track(playlist.id, song.id, i)

        await db_session.commit()

        found = await repo.get_by_id_with_tracks(playlist.id)
        assert found is not None
        assert len(found.tracks) == 3

    async def test_get_by_platform_id(self, db_session: AsyncSession) -> None:
        """Test getting playlist by platform ID."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Platform Playlist",
            name_normalized=slugify("Platform Playlist"),
            owner_name="User",
        )
        await db_session.flush()

        await repo.add_platform_link(
            playlist.id, "spotify", "play789", "https://open.spotify.com/playlist/play789"
        )
        await db_session.commit()

        found = await repo.get_by_platform_id("spotify", "play789")
        assert found is not None
        assert found.name == "Platform Playlist"

    async def test_get_by_platform_id_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting playlist by non-existent platform ID."""
        repo = PlaylistRepository(db_session)
        found = await repo.get_by_platform_id("spotify", "nonexistent")
        assert found is None

    async def test_search_by_name(self, db_session: AsyncSession) -> None:
        """Test searching playlists by name."""
        repo = PlaylistRepository(db_session)

        await repo.create(
            name="Chill Vibes", name_normalized=slugify("Chill Vibes"), owner_name="User1"
        )
        await repo.create(
            name="Chillout Mix", name_normalized=slugify("Chillout Mix"), owner_name="User2"
        )
        await repo.create(
            name="Rock Classics", name_normalized=slugify("Rock Classics"), owner_name="User3"
        )
        await db_session.commit()

        results = await repo.search_by_name("chill")
        assert len(results) == 2

    async def test_search_by_name_with_limit(self, db_session: AsyncSession) -> None:
        """Test searching playlists with limit."""
        repo = PlaylistRepository(db_session)

        for i in range(10):
            await repo.create(
                name=f"Playlist {i}",
                name_normalized=slugify(f"Playlist {i}"),
                owner_name="User",
            )
        await db_session.commit()

        results = await repo.search_by_name("Playlist", limit=5)
        assert len(results) == 5

    async def test_add_platform_link(self, db_session: AsyncSession) -> None:
        """Test adding a platform link."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Playlist", name_normalized=slugify("Playlist"), owner_name="User"
        )
        await db_session.flush()

        link = await repo.add_platform_link(
            playlist.id,
            "spotify",
            "abc123",
            "https://open.spotify.com/playlist/abc123",
            followers=500,
        )
        await db_session.commit()

        assert link.playlist_id == playlist.id
        assert link.platform == "spotify"
        assert link.followers == 500

    async def test_add_platform_link_duplicate(self, db_session: AsyncSession) -> None:
        """Test adding duplicate platform link returns existing one."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Playlist", name_normalized=slugify("Playlist"), owner_name="User"
        )
        await db_session.flush()

        link1 = await repo.add_platform_link(
            playlist.id, "spotify", "abc123", "https://open.spotify.com/playlist/abc123"
        )
        await db_session.commit()

        link2 = await repo.add_platform_link(
            playlist.id, "spotify", "abc123", "https://open.spotify.com/playlist/abc123"
        )
        assert link1.id == link2.id

    async def test_get_platform_link(self, db_session: AsyncSession) -> None:
        """Test getting a platform link."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Playlist", name_normalized=slugify("Playlist"), owner_name="User"
        )
        await db_session.flush()

        await repo.add_platform_link(
            playlist.id, "spotify", "xyz789", "https://open.spotify.com/playlist/xyz789"
        )
        await db_session.commit()

        link = await repo.get_platform_link("spotify", "xyz789")
        assert link is not None
        assert link.platform_id == "xyz789"

    async def test_get_platform_link_not_found(self, db_session: AsyncSession) -> None:
        """Test getting non-existent platform link."""
        repo = PlaylistRepository(db_session)
        link = await repo.get_platform_link("spotify", "nonexistent")
        assert link is None

    async def test_add_track(self, db_session: AsyncSession) -> None:
        """Test adding a track to a playlist."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Playlist", name_normalized=slugify("Playlist"), owner_name="User"
        )
        song = Song(
            name="Song",
            artists=["Artist"],
            platform="spotify",
            platform_id="song1",
            platform_url="https://open.spotify.com/track/song1",
            duration_seconds=180
        )
        db_session.add(song)
        await db_session.flush()

        track = await repo.add_track(playlist.id, song.id, 0)
        await db_session.commit()

        assert track.playlist_id == playlist.id
        assert track.song_id == song.id
        assert track.position == 0

    async def test_add_multiple_tracks(self, db_session: AsyncSession) -> None:
        """Test adding multiple tracks to a playlist."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Playlist", name_normalized=slugify("Playlist"), owner_name="User"
        )
        await db_session.flush()

        for i in range(5):
            song = Song(
                name=f"Song {i}",
                artists=["Artist"],
                platform="spotify",
                platform_id=f"song{i}",
                platform_url=f"https://open.spotify.com/track/song{i}",
                duration_seconds=180
            )
            db_session.add(song)
            await db_session.flush()
            await repo.add_track(playlist.id, song.id, i)

        await db_session.commit()

        found = await repo.get_by_id_with_tracks(playlist.id)
        assert len(found.tracks) == 5

    async def test_clear_tracks(self, db_session: AsyncSession) -> None:
        """Test clearing all tracks from a playlist."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Playlist", name_normalized=slugify("Playlist"), owner_name="User"
        )
        await db_session.flush()

        for i in range(3):
            song = Song(
                name=f"Song {i}",
                artists=["Artist"],
                platform="spotify",
                platform_id=f"song{i}",
                platform_url=f"https://open.spotify.com/track/song{i}",
                duration_seconds=180
            )
            db_session.add(song)
            await db_session.flush()
            await repo.add_track(playlist.id, song.id, i)

        await db_session.commit()

        count = await repo.clear_tracks(playlist.id)
        await db_session.commit()

        assert count == 3

        found = await repo.get_by_id_with_tracks(playlist.id)
        assert len(found.tracks) == 0

    async def test_clear_tracks_empty_playlist(self, db_session: AsyncSession) -> None:
        """Test clearing tracks from empty playlist."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Playlist", name_normalized=slugify("Playlist"), owner_name="User"
        )
        await db_session.commit()

        count = await repo.clear_tracks(playlist.id)
        assert count == 0

    async def test_get_all(self, db_session: AsyncSession) -> None:
        """Test getting all playlists."""
        repo = PlaylistRepository(db_session)

        for i in range(5):
            await repo.create(
                name=f"Playlist {i}",
                name_normalized=slugify(f"Playlist {i}"),
                owner_name="User",
            )
        await db_session.commit()

        playlists = await repo.get_all()
        assert len(playlists) == 5

    async def test_count(self, db_session: AsyncSession) -> None:
        """Test counting playlists."""
        repo = PlaylistRepository(db_session)

        for i in range(3):
            await repo.create(
                name=f"Playlist {i}",
                name_normalized=slugify(f"Playlist {i}"),
                owner_name="User",
            )
        await db_session.commit()

        count = await repo.count()
        assert count == 3

    async def test_update(self, db_session: AsyncSession) -> None:
        """Test updating a playlist."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="Old Name", name_normalized=slugify("Old Name"), owner_name="User"
        )
        await db_session.commit()

        updated = await repo.update(playlist.id, name="New Name")
        assert updated is not None
        assert updated.name == "New Name"

    async def test_delete(self, db_session: AsyncSession) -> None:
        """Test deleting a playlist."""
        repo = PlaylistRepository(db_session)
        playlist = await repo.create(
            name="To Delete", name_normalized=slugify("To Delete"), owner_name="User"
        )
        await db_session.commit()

        result = await repo.delete(playlist.id)
        assert result is True

        found = await repo.get_by_id(playlist.id)
        assert found is None


class TestLyricsRepository:
    """Tests for LyricsRepository."""

    async def test_lyrics_repository_exists(self, db_session: AsyncSession) -> None:
        """Test lyrics repository can be instantiated."""
        repo = LyricsRepository(db_session)
        assert repo is not None

    async def test_upsert_create(self, db_session: AsyncSession) -> None:
        """Test creating lyrics with upsert."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song1")
        db_session.add(song)
        await db_session.flush()

        lyrics = await repo.upsert(
            song.id,
            "genius",
            "Test lyrics text",
            quality_score=0.95,
            is_verified=True,
        )
        await db_session.commit()

        assert lyrics.song_id == song.id
        assert lyrics.source == "genius"
        assert lyrics.lyrics_text == "Test lyrics text"
        assert lyrics.quality_score == 0.95
        assert lyrics.is_verified is True

    async def test_upsert_update(self, db_session: AsyncSession) -> None:
        """Test updating lyrics with upsert."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song2")
        db_session.add(song)
        await db_session.flush()

        lyrics1 = await repo.upsert(song.id, "genius", "Old lyrics")
        await db_session.commit()

        lyrics2 = await repo.upsert(song.id, "genius", "New lyrics", quality_score=0.9)
        await db_session.commit()

        assert lyrics1.id == lyrics2.id
        assert lyrics2.lyrics_text == "New lyrics"
        assert lyrics2.quality_score == 0.9

    async def test_upsert_with_synced_lyrics(self, db_session: AsyncSession) -> None:
        """Test upserting lyrics with synced content."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song3")
        db_session.add(song)
        await db_session.flush()

        synced_lrc = "[00:12.00]Test line 1\n[00:15.50]Test line 2"
        lyrics = await repo.upsert(
            song.id, "lrclib", "Test lyrics", lyrics_synced=synced_lrc
        )
        await db_session.commit()

        assert lyrics.lyrics_synced == synced_lrc

    async def test_get_by_source(self, db_session: AsyncSession) -> None:
        """Test getting lyrics by source."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song4")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "genius", "Genius lyrics")
        await repo.upsert(song.id, "musixmatch", "Musixmatch lyrics")
        await db_session.commit()

        genius_lyrics = await repo.get_by_source(song.id, "genius")
        assert genius_lyrics is not None
        assert genius_lyrics.lyrics_text == "Genius lyrics"

    async def test_get_by_source_not_found(self, db_session: AsyncSession) -> None:
        """Test getting lyrics by non-existent source."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song5")
        db_session.add(song)
        await db_session.flush()

        lyrics = await repo.get_by_source(song.id, "nonexistent")
        assert lyrics is None

    async def test_get_all_for_song(self, db_session: AsyncSession) -> None:
        """Test getting all lyrics for a song."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song6")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "genius", "Genius lyrics", quality_score=0.9)
        await repo.upsert(song.id, "musixmatch", "Musixmatch lyrics", quality_score=0.8)
        await repo.upsert(song.id, "lrclib", "LRCLib lyrics", quality_score=0.95)
        await db_session.commit()

        all_lyrics = await repo.get_all_for_song(song.id)
        assert len(all_lyrics) == 3

    async def test_get_all_for_song_ordered_by_quality(
        self, db_session: AsyncSession
    ) -> None:
        """Test lyrics are ordered by quality score."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song7")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "source1", "Lyrics 1", quality_score=0.5)
        await repo.upsert(song.id, "source2", "Lyrics 2", quality_score=0.9)
        await repo.upsert(song.id, "source3", "Lyrics 3", quality_score=0.7)
        await db_session.commit()

        all_lyrics = await repo.get_all_for_song(song.id, order_by_quality=True)
        assert all_lyrics[0].quality_score == 0.9
        assert all_lyrics[1].quality_score == 0.7
        assert all_lyrics[2].quality_score == 0.5

    async def test_get_all_for_song_synced_preferred(
        self, db_session: AsyncSession
    ) -> None:
        """Test synced lyrics are preferred in ordering."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song8")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "source1", "Lyrics 1", quality_score=0.95)
        await repo.upsert(
            song.id, "source2", "Lyrics 2", lyrics_synced="[00:00.00]Synced",
            quality_score=0.8
        )
        await db_session.commit()

        all_lyrics = await repo.get_all_for_song(song.id, order_by_quality=True)
        assert all_lyrics[0].lyrics_synced is not None

    async def test_get_best_for_song(self, db_session: AsyncSession) -> None:
        """Test getting best quality lyrics for a song."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song9")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "source1", "Lyrics 1", quality_score=0.5)
        await repo.upsert(song.id, "source2", "Lyrics 2", quality_score=0.95)
        await db_session.commit()

        best = await repo.get_best_for_song(song.id)
        assert best is not None
        assert best.quality_score == 0.95

    async def test_get_best_for_song_no_lyrics(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting best lyrics when none exist."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song10")
        db_session.add(song)
        await db_session.flush()

        best = await repo.get_best_for_song(song.id)
        assert best is None

    async def test_get_sources_for_song(self, db_session: AsyncSession) -> None:
        """Test getting available sources for a song."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song11")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "genius", "Lyrics 1")
        await repo.upsert(song.id, "musixmatch", "Lyrics 2")
        await repo.upsert(song.id, "lrclib", "Lyrics 3")
        await db_session.commit()

        sources = await repo.get_sources_for_song(song.id)
        assert len(sources) == 3
        assert set(sources) == {"genius", "musixmatch", "lrclib"}

    async def test_has_synced_lyrics_true(self, db_session: AsyncSession) -> None:
        """Test checking if song has synced lyrics."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song12")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "lrclib", "Lyrics", lyrics_synced="[00:00.00]Test")
        await db_session.commit()

        has_synced = await repo.has_synced_lyrics(song.id)
        assert has_synced is True

    async def test_has_synced_lyrics_false(self, db_session: AsyncSession) -> None:
        """Test checking if song has synced lyrics when it doesn't."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song13")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "genius", "Lyrics")
        await db_session.commit()

        has_synced = await repo.has_synced_lyrics(song.id)
        assert has_synced is False

    async def test_delete_for_song(self, db_session: AsyncSession) -> None:
        """Test deleting all lyrics for a song."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song14")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "source1", "Lyrics 1")
        await repo.upsert(song.id, "source2", "Lyrics 2")
        await db_session.commit()

        count = await repo.delete_for_song(song.id)
        await db_session.commit()

        assert count == 2

        all_lyrics = await repo.get_all_for_song(song.id)
        assert len(all_lyrics) == 0

    async def test_upsert_with_all_fields(self, db_session: AsyncSession) -> None:
        """Test upserting lyrics with all optional fields."""
        repo = LyricsRepository(db_session)
        song = create_test_song("Song", "song15")
        db_session.add(song)
        await db_session.flush()

        lyrics = await repo.upsert(
            song.id,
            "genius",
            "Full lyrics text",
            lyrics_synced="[00:00.00]Synced",
            quality_score=0.95,
            is_verified=True,
            line_count=20,
            content_hash="abc123hash",
            provider_track_id="track_123",
            has_translations=True,
            language="en",
        )
        await db_session.commit()

        assert lyrics.line_count == 20
        assert lyrics.content_hash == "abc123hash"
        assert lyrics.provider_track_id == "track_123"
        assert lyrics.has_translations is True
        assert lyrics.language == "en"


class TestMetadataSnapshotRepository:
    """Tests for MetadataSnapshotRepository."""

    async def test_repository_exists(self, db_session: AsyncSession) -> None:
        """Test repository can be instantiated."""
        repo = MetadataSnapshotRepository(db_session)
        assert repo is not None

    async def test_upsert_create(self, db_session: AsyncSession) -> None:
        """Test creating metadata snapshot with upsert."""
        repo = MetadataSnapshotRepository(db_session)
        song = create_test_song("Song", "Song_id")
        db_session.add(song)
        await db_session.flush()

        snapshot_data = {"title": "Test Song", "year": 2024}
        snapshot = await repo.upsert(
            song.id, "musicbrainz", snapshot_data, confidence=0.9
        )
        await db_session.commit()

        assert snapshot.song_id == song.id
        assert snapshot.source == "musicbrainz"
        assert snapshot.snapshot_data == snapshot_data
        assert snapshot.confidence == 0.9

    async def test_upsert_update(self, db_session: AsyncSession) -> None:
        """Test updating metadata snapshot with upsert."""
        repo = MetadataSnapshotRepository(db_session)
        song = create_test_song("Song", "Song_id")
        db_session.add(song)
        await db_session.flush()

        old_data = {"title": "Old Title"}
        snapshot1 = await repo.upsert(song.id, "musicbrainz", old_data)
        await db_session.commit()

        new_data = {"title": "New Title", "year": 2024}
        snapshot2 = await repo.upsert(song.id, "musicbrainz", new_data, confidence=0.95)
        await db_session.commit()

        assert snapshot1.id == snapshot2.id
        assert snapshot2.snapshot_data == new_data
        assert snapshot2.confidence == 0.95

    async def test_upsert_with_raw_response(self, db_session: AsyncSession) -> None:
        """Test upserting with raw API response."""
        repo = MetadataSnapshotRepository(db_session)
        song = create_test_song("Song", "Song_id")
        db_session.add(song)
        await db_session.flush()

        snapshot_data = {"title": "Song"}
        raw_response = {"api_version": "1.0", "data": {"title": "Song"}}
        snapshot = await repo.upsert(
            song.id, "discogs", snapshot_data, raw_response=raw_response
        )
        await db_session.commit()

        assert snapshot.raw_response == raw_response

    async def test_get_by_source(self, db_session: AsyncSession) -> None:
        """Test getting snapshot by source."""
        repo = MetadataSnapshotRepository(db_session)
        song = create_test_song("Song", "Song_id")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "musicbrainz", {"title": "MB Data"})
        await repo.upsert(song.id, "discogs", {"title": "Discogs Data"})
        await db_session.commit()

        snapshot = await repo.get_by_source(song.id, "musicbrainz")
        assert snapshot is not None
        assert snapshot.snapshot_data["title"] == "MB Data"

    async def test_get_by_source_not_found(self, db_session: AsyncSession) -> None:
        """Test getting snapshot by non-existent source."""
        repo = MetadataSnapshotRepository(db_session)
        song = create_test_song("Song", "Song_id")
        db_session.add(song)
        await db_session.flush()

        snapshot = await repo.get_by_source(song.id, "nonexistent")
        assert snapshot is None

    async def test_get_for_song(self, db_session: AsyncSession) -> None:
        """Test getting all snapshots for a song."""
        repo = MetadataSnapshotRepository(db_session)
        song = create_test_song("Song", "Song_id")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "source1", {"data": "1"}, confidence=0.8)
        await repo.upsert(song.id, "source2", {"data": "2"}, confidence=0.9)
        await repo.upsert(song.id, "source3", {"data": "3"}, confidence=0.7)
        await db_session.commit()

        snapshots = await repo.get_for_song(song.id)
        assert len(snapshots) == 3

    async def test_get_for_song_ordered_by_confidence(
        self, db_session: AsyncSession
    ) -> None:
        """Test snapshots are ordered by confidence."""
        repo = MetadataSnapshotRepository(db_session)
        song = create_test_song("Song", "Song_id")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "source1", {"data": "1"}, confidence=0.5)
        await repo.upsert(song.id, "source2", {"data": "2"}, confidence=0.95)
        await repo.upsert(song.id, "source3", {"data": "3"}, confidence=0.7)
        await db_session.commit()

        snapshots = await repo.get_for_song(song.id, order_by_confidence=True)
        assert snapshots[0].confidence == 0.95
        assert snapshots[1].confidence == 0.7
        assert snapshots[2].confidence == 0.5

    async def test_get_sources_for_song(self, db_session: AsyncSession) -> None:
        """Test getting available sources for a song."""
        repo = MetadataSnapshotRepository(db_session)
        song = create_test_song("Song", "Song_id")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "musicbrainz", {"data": "1"})
        await repo.upsert(song.id, "discogs", {"data": "2"})
        await repo.upsert(song.id, "lastfm", {"data": "3"})
        await db_session.commit()

        sources = await repo.get_sources_for_song(song.id)
        assert len(sources) == 3
        assert set(sources) == {"musicbrainz", "discogs", "lastfm"}

    async def test_delete_for_song(self, db_session: AsyncSession) -> None:
        """Test deleting all snapshots for a song."""
        repo = MetadataSnapshotRepository(db_session)
        song = create_test_song("Song", "Song_id")
        db_session.add(song)
        await db_session.flush()

        await repo.upsert(song.id, "source1", {"data": "1"})
        await repo.upsert(song.id, "source2", {"data": "2"})
        await db_session.commit()

        count = await repo.delete_for_song(song.id)
        await db_session.commit()

        assert count == 2

        snapshots = await repo.get_for_song(song.id)
        assert len(snapshots) == 0


class TestUserSettingsRepository:
    """Tests for UserSettingsRepository."""

    async def test_repository_exists(self, db_session: AsyncSession) -> None:
        """Test repository can be instantiated."""
        repo = UserSettingsRepository(db_session)
        assert repo is not None

    async def test_create(self, db_session: AsyncSession) -> None:
        """Test creating user settings."""
        repo = UserSettingsRepository(db_session)
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        db_session.add(user)
        await db_session.flush()

        settings = await repo.create(user.id)
        assert settings.user_id == user.id
        assert settings.id is not None

    async def test_create_with_custom_values(self, db_session: AsyncSession) -> None:
        """Test creating user settings with custom values."""
        repo = UserSettingsRepository(db_session)
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        db_session.add(user)
        await db_session.flush()

        settings = await repo.create(user.id, audio_format="flac", bitrate="320k")
        assert settings.audio_format == "flac"
        assert settings.bitrate == "320k"

    async def test_get_by_user_id(self, db_session: AsyncSession) -> None:
        """Test getting settings by user ID."""
        repo = UserSettingsRepository(db_session)
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        db_session.add(user)
        await db_session.flush()

        created = await repo.create(user.id)

        found = await repo.get_by_user_id(user.id)
        assert found is not None
        assert found.id == created.id

    async def test_get_by_user_id_not_found(self, db_session: AsyncSession) -> None:
        """Test getting settings for user without settings."""
        repo = UserSettingsRepository(db_session)
        found = await repo.get_by_user_id(uuid.uuid4())
        assert found is None

    async def test_update(self, db_session: AsyncSession) -> None:
        """Test updating user settings."""
        repo = UserSettingsRepository(db_session)
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        db_session.add(user)
        await db_session.flush()

        settings = await repo.create(user.id, audio_format="mp3")

        updated = await repo.update(settings, audio_format="flac", bitrate="320k")
        assert updated.audio_format == "flac"
        assert updated.bitrate == "320k"

    async def test_get_or_create_existing(self, db_session: AsyncSession) -> None:
        """Test get_or_create returns existing settings."""
        repo = UserSettingsRepository(db_session)
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        db_session.add(user)
        await db_session.flush()

        created = await repo.create(user.id)

        settings, is_new = await repo.get_or_create(user.id)
        assert is_new is False
        assert settings.id == created.id

    async def test_get_or_create_new(self, db_session: AsyncSession) -> None:
        """Test get_or_create creates new settings."""
        repo = UserSettingsRepository(db_session)
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        db_session.add(user)
        await db_session.flush()

        settings, is_new = await repo.get_or_create(user.id, audio_format="flac")
        assert is_new is True
        assert settings.user_id == user.id
        assert settings.audio_format == "flac"

    async def test_delete(self, db_session: AsyncSession) -> None:
        """Test deleting user settings."""
        repo = UserSettingsRepository(db_session)
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        db_session.add(user)
        await db_session.flush()

        settings = await repo.create(user.id)
        await repo.delete(settings)

        found = await repo.get_by_user_id(user.id)
        assert found is None

    async def test_reset_to_defaults_existing(self, db_session: AsyncSession) -> None:
        """Test resetting existing settings to defaults."""
        repo = UserSettingsRepository(db_session)
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        db_session.add(user)
        await db_session.flush()

        settings = await repo.create(user.id, audio_format="flac", bitrate="320k")
        old_id = settings.id

        reset_settings = await repo.reset_to_defaults(user.id)
        assert reset_settings.id != old_id
        assert reset_settings.user_id == user.id

    async def test_reset_to_defaults_no_existing(
        self, db_session: AsyncSession
    ) -> None:
        """Test resetting to defaults when no settings exist."""
        repo = UserSettingsRepository(db_session)
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        db_session.add(user)
        await db_session.flush()

        reset_settings = await repo.reset_to_defaults(user.id)
        assert reset_settings.user_id == user.id
