"""Tests for database repositories."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.db.models.match import Match, MatchType
from spotdl.db.models.song import Song
from spotdl.db.models.user import User
from spotdl.db.models.vote import Vote, VoteType
from spotdl.db.repositories.base import BaseRepository
from spotdl.db.repositories.match import MatchRepository
from spotdl.db.repositories.song import SongRepository
from spotdl.db.repositories.user import UserRepository
from spotdl.db.repositories.vote import VoteRepository


pytestmark = pytest.mark.asyncio


class TestUserRepository:
    """Tests for UserRepository."""

    async def test_create_user(self, db_session: AsyncSession) -> None:
        """Test creating a user."""
        repo = UserRepository(db_session)
        user = await repo.create(
            username="newuser",
            email="new@example.com",
            hashed_password="hashed123",
        )
        await db_session.commit()

        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"

    async def test_get_by_username(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test getting user by username."""
        repo = UserRepository(db_session)
        user = await repo.get_by_username("testuser")

        assert user is not None
        assert user.username == "testuser"

    async def test_get_by_username_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting non-existent user by username."""
        repo = UserRepository(db_session)
        user = await repo.get_by_username("nonexistent")

        assert user is None

    async def test_get_by_email(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test getting user by email."""
        repo = UserRepository(db_session)
        user = await repo.get_by_email("test@example.com")

        assert user is not None
        assert user.email == "test@example.com"

    async def test_get_by_email_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting non-existent user by email."""
        repo = UserRepository(db_session)
        user = await repo.get_by_email("nonexistent@example.com")

        assert user is None

    async def test_username_exists(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test checking if username exists."""
        repo = UserRepository(db_session)

        assert await repo.username_exists("testuser") is True
        assert await repo.username_exists("nonexistent") is False

    async def test_email_exists(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test checking if email exists."""
        repo = UserRepository(db_session)

        assert await repo.email_exists("test@example.com") is True
        assert await repo.email_exists("nonexistent@example.com") is False

    async def test_update_reputation(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test updating user reputation."""
        repo = UserRepository(db_session)

        # Increase reputation
        updated = await repo.update_reputation(test_user.id, 10)
        await db_session.commit()

        assert updated is not None
        assert updated.reputation_score == 10

        # Decrease reputation
        updated = await repo.update_reputation(test_user.id, -5)
        await db_session.commit()

        assert updated.reputation_score == 5

    async def test_update_reputation_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test updating reputation for non-existent user."""
        repo = UserRepository(db_session)
        result = await repo.update_reputation(uuid.uuid4(), 10)

        assert result is None


class TestSongRepository:
    """Tests for SongRepository."""

    @pytest_asyncio.fixture
    async def test_song(self, db_session: AsyncSession) -> Song:
        """Create a test song."""
        song = Song(
            platform="spotify",
            platform_id="test123",
            platform_url="https://open.spotify.com/track/test123",
            name="Test Song",
            artists=["Artist 1", "Artist 2"],
            duration_seconds=200,
            isrc="USABC1234567",
        )
        db_session.add(song)
        await db_session.commit()
        await db_session.refresh(song)
        return song

    async def test_create_song(self, db_session: AsyncSession) -> None:
        """Test creating a song."""
        repo = SongRepository(db_session)
        song = await repo.create(
            platform="deezer",
            platform_id="456789",
            platform_url="https://deezer.com/track/456789",
            name="New Song",
            artists=["Artist"],
            duration_seconds=180,
        )
        await db_session.commit()

        assert song.id is not None
        assert song.platform == "deezer"
        assert song.name == "New Song"

    async def test_get_by_platform_id(
        self, db_session: AsyncSession, test_song: Song
    ) -> None:
        """Test getting song by platform and ID."""
        repo = SongRepository(db_session)
        song = await repo.get_by_platform_id("spotify", "test123")

        assert song is not None
        assert song.name == "Test Song"

    async def test_get_by_platform_id_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting non-existent song by platform and ID."""
        repo = SongRepository(db_session)
        song = await repo.get_by_platform_id("spotify", "nonexistent")

        assert song is None

    async def test_get_by_url(
        self, db_session: AsyncSession, test_song: Song
    ) -> None:
        """Test getting song by URL."""
        repo = SongRepository(db_session)
        song = await repo.get_by_url("https://open.spotify.com/track/test123")

        assert song is not None
        assert song.name == "Test Song"

    async def test_get_by_url_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting non-existent song by URL."""
        repo = SongRepository(db_session)
        song = await repo.get_by_url("https://example.com/nonexistent")

        assert song is None

    async def test_get_by_isrc(
        self, db_session: AsyncSession, test_song: Song
    ) -> None:
        """Test getting songs by ISRC."""
        repo = SongRepository(db_session)
        songs = await repo.get_by_isrc("USABC1234567")

        assert len(songs) == 1
        assert songs[0].name == "Test Song"

    async def test_get_by_isrc_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting songs by non-existent ISRC."""
        repo = SongRepository(db_session)
        songs = await repo.get_by_isrc("NONEXISTENT123")

        assert len(songs) == 0

    async def test_search_by_name(
        self, db_session: AsyncSession, test_song: Song
    ) -> None:
        """Test searching songs by name."""
        repo = SongRepository(db_session)
        songs = await repo.search_by_name("Test")

        assert len(songs) == 1
        assert songs[0].name == "Test Song"

    async def test_search_by_name_with_platform(
        self, db_session: AsyncSession, test_song: Song
    ) -> None:
        """Test searching songs by name with platform filter."""
        repo = SongRepository(db_session)

        # Should find with correct platform
        songs = await repo.search_by_name("Test", platform="spotify")
        assert len(songs) == 1

        # Should not find with wrong platform
        songs = await repo.search_by_name("Test", platform="deezer")
        assert len(songs) == 0

    async def test_search_by_name_case_insensitive(
        self, db_session: AsyncSession, test_song: Song
    ) -> None:
        """Test searching songs is case insensitive."""
        repo = SongRepository(db_session)

        songs = await repo.search_by_name("test song")
        assert len(songs) == 1

        songs = await repo.search_by_name("TEST SONG")
        assert len(songs) == 1

    async def test_search_by_name_limit(
        self, db_session: AsyncSession
    ) -> None:
        """Test searching songs respects limit."""
        repo = SongRepository(db_session)

        # Create multiple songs
        for i in range(5):
            await repo.create(
                platform="spotify",
                platform_id=f"id{i}",
                platform_url=f"https://spotify.com/track/id{i}",
                name=f"Song {i}",
                artists=["Artist"],
                duration_seconds=180,
            )
        await db_session.commit()

        songs = await repo.search_by_name("Song", limit=3)
        assert len(songs) == 3


class TestMatchRepository:
    """Tests for MatchRepository."""

    @pytest_asyncio.fixture
    async def user_match(
        self, db_session: AsyncSession, test_user: User
    ) -> Match:
        """Create a user-submitted match."""
        match = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/user123",
            target_platform="youtube",
            target_url="https://www.youtube.com/watch?v=user456",
            match_type=MatchType.USER,
            submitted_by=test_user.id,
        )
        db_session.add(match)
        await db_session.commit()
        await db_session.refresh(match)
        return match

    async def test_get_by_source_url(
        self, db_session: AsyncSession, test_match: Match
    ) -> None:
        """Test getting matches by source URL."""
        repo = MatchRepository(db_session)
        matches = await repo.get_by_source_url(
            "https://open.spotify.com/track/test123"
        )

        assert len(matches) == 1
        assert matches[0].target_platform == "youtube"

    async def test_get_by_source_url_with_platform(
        self, db_session: AsyncSession, test_match: Match
    ) -> None:
        """Test getting matches by source URL with platform filter."""
        repo = MatchRepository(db_session)

        # Should find with correct platform
        matches = await repo.get_by_source_url(
            "https://open.spotify.com/track/test123",
            target_platform="youtube",
        )
        assert len(matches) == 1

        # Should not find with wrong platform
        matches = await repo.get_by_source_url(
            "https://open.spotify.com/track/test123",
            target_platform="soundcloud",
        )
        assert len(matches) == 0

    async def test_get_by_source_and_target(
        self, db_session: AsyncSession, test_match: Match
    ) -> None:
        """Test getting specific match."""
        repo = MatchRepository(db_session)
        match = await repo.get_by_source_and_target(
            source_url="https://open.spotify.com/track/test123",
            target_platform="youtube",
            target_url="https://www.youtube.com/watch?v=xyz789",
        )

        assert match is not None
        assert match.match_score == 85.0

    async def test_get_by_source_and_target_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting non-existent match."""
        repo = MatchRepository(db_session)
        match = await repo.get_by_source_and_target(
            source_url="https://nonexistent.com/track/123",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=xyz",
        )

        assert match is None

    async def test_get_user_submissions(
        self, db_session: AsyncSession, test_user: User, user_match: Match
    ) -> None:
        """Test getting user submissions."""
        repo = MatchRepository(db_session)
        matches = await repo.get_user_submissions(test_user.id)

        assert len(matches) == 1
        assert matches[0].match_type == MatchType.USER

    async def test_get_user_submissions_pagination(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test pagination of user submissions."""
        repo = MatchRepository(db_session)

        # Create multiple matches
        for i in range(5):
            await repo.create(
                source_platform="spotify",
                source_url=f"https://spotify.com/track/sub{i}",
                target_platform="youtube",
                target_url=f"https://youtube.com/watch?v=sub{i}",
                match_type=MatchType.USER,
                submitted_by=test_user.id,
            )
        await db_session.commit()

        # Get with pagination
        matches = await repo.get_user_submissions(test_user.id, limit=3)
        assert len(matches) == 3

        matches = await repo.get_user_submissions(test_user.id, skip=3, limit=3)
        assert len(matches) == 2

    async def test_get_pending_verification(
        self, db_session: AsyncSession, test_user: User, user_match: Match
    ) -> None:
        """Test getting matches pending verification."""
        repo = MatchRepository(db_session)
        matches = await repo.get_pending_verification()

        assert len(matches) >= 1
        # All should be user type without verification
        for match in matches:
            assert match.match_type == MatchType.USER
            assert match.verified_by is None

    async def test_update_vote_counts(
        self, db_session: AsyncSession, test_user: User, test_match: Match
    ) -> None:
        """Test updating vote counts from votes table."""
        # Add votes
        vote1 = Vote(
            match_id=test_match.id,
            user_id=test_user.id,
            vote_type=VoteType.UP,
        )
        db_session.add(vote1)
        await db_session.commit()

        repo = MatchRepository(db_session)
        updated = await repo.update_vote_counts(test_match.id)
        await db_session.commit()

        assert updated is not None
        assert updated.upvotes == 1
        assert updated.downvotes == 0

    async def test_update_vote_counts_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test updating vote counts for non-existent match."""
        repo = MatchRepository(db_session)
        result = await repo.update_vote_counts(uuid.uuid4())

        assert result is None


class TestVoteRepository:
    """Tests for VoteRepository."""

    @pytest_asyncio.fixture
    async def test_vote(
        self, db_session: AsyncSession, test_user: User, test_match: Match
    ) -> Vote:
        """Create a test vote."""
        vote = Vote(
            match_id=test_match.id,
            user_id=test_user.id,
            vote_type=VoteType.UP,
        )
        db_session.add(vote)
        await db_session.commit()
        await db_session.refresh(vote)
        return vote

    async def test_get_user_vote(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_match: Match,
        test_vote: Vote,
    ) -> None:
        """Test getting user's vote on a match."""
        repo = VoteRepository(db_session)
        vote = await repo.get_user_vote(test_match.id, test_user.id)

        assert vote is not None
        assert vote.vote_type == VoteType.UP

    async def test_get_user_vote_not_found(
        self, db_session: AsyncSession, test_user: User, test_match: Match
    ) -> None:
        """Test getting non-existent vote."""
        repo = VoteRepository(db_session)
        vote = await repo.get_user_vote(test_match.id, uuid.uuid4())

        assert vote is None

    async def test_get_match_votes(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_match: Match,
        test_vote: Vote,
    ) -> None:
        """Test getting all votes for a match."""
        repo = VoteRepository(db_session)
        votes = await repo.get_match_votes(test_match.id)

        assert len(votes) == 1
        assert votes[0].vote_type == VoteType.UP

    async def test_get_user_votes(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_match: Match,
        test_vote: Vote,
    ) -> None:
        """Test getting all votes by a user."""
        repo = VoteRepository(db_session)
        votes = await repo.get_user_votes(test_user.id)

        assert len(votes) == 1
        assert votes[0].match_id == test_match.id

    async def test_upsert_vote_create(
        self, db_session: AsyncSession, test_user: User, test_match: Match
    ) -> None:
        """Test creating a vote via upsert."""
        repo = VoteRepository(db_session)
        vote = await repo.upsert_vote(
            test_match.id, test_user.id, VoteType.UP
        )
        await db_session.commit()

        assert vote is not None
        assert vote.vote_type == VoteType.UP

    async def test_upsert_vote_update(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_match: Match,
        test_vote: Vote,
    ) -> None:
        """Test updating a vote via upsert."""
        repo = VoteRepository(db_session)
        vote = await repo.upsert_vote(
            test_match.id, test_user.id, VoteType.DOWN
        )
        await db_session.commit()

        assert vote is not None
        assert vote.vote_type == VoteType.DOWN

    async def test_delete_vote(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_match: Match,
        test_vote: Vote,
    ) -> None:
        """Test deleting a vote."""
        repo = VoteRepository(db_session)
        result = await repo.delete_vote(test_match.id, test_user.id)
        await db_session.commit()

        assert result is True

        # Verify it's deleted
        vote = await repo.get_user_vote(test_match.id, test_user.id)
        assert vote is None

    async def test_delete_vote_not_found(
        self, db_session: AsyncSession, test_user: User, test_match: Match
    ) -> None:
        """Test deleting non-existent vote."""
        repo = VoteRepository(db_session)
        result = await repo.delete_vote(test_match.id, uuid.uuid4())

        assert result is False


class TestBaseRepository:
    """Tests for BaseRepository common operations."""

    async def test_get_by_id(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test getting record by ID."""
        repo = UserRepository(db_session)
        user = await repo.get_by_id(test_user.id)

        assert user is not None
        assert user.username == "testuser"

    async def test_get_by_id_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting non-existent record by ID."""
        repo = UserRepository(db_session)
        user = await repo.get_by_id(uuid.uuid4())

        assert user is None

    async def test_get_all(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test getting all records."""
        repo = UserRepository(db_session)

        # Create additional users
        await repo.create(
            username="user2",
            email="user2@example.com",
            hashed_password="hash2",
        )
        await db_session.commit()

        users = await repo.get_all()
        assert len(users) == 2

    async def test_get_all_pagination(
        self, db_session: AsyncSession
    ) -> None:
        """Test pagination of get_all."""
        repo = UserRepository(db_session)

        # Create multiple users
        for i in range(5):
            await repo.create(
                username=f"puser{i}",
                email=f"puser{i}@example.com",
                hashed_password=f"hash{i}",
            )
        await db_session.commit()

        # Test limit
        users = await repo.get_all(limit=3)
        assert len(users) == 3

        # Test skip
        users = await repo.get_all(skip=3, limit=3)
        assert len(users) == 2

    async def test_update(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test updating a record."""
        repo = UserRepository(db_session)
        updated = await repo.update(test_user.id, username="updateduser")
        await db_session.commit()

        assert updated is not None
        assert updated.username == "updateduser"

    async def test_update_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test updating non-existent record."""
        repo = UserRepository(db_session)
        result = await repo.update(uuid.uuid4(), username="test")

        assert result is None

    async def test_update_ignores_invalid_fields(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that update ignores fields that don't exist."""
        repo = UserRepository(db_session)
        updated = await repo.update(
            test_user.id,
            username="newname",
            nonexistent_field="ignored",
        )
        await db_session.commit()

        assert updated is not None
        assert updated.username == "newname"

    async def test_delete(
        self, db_session: AsyncSession
    ) -> None:
        """Test deleting a record."""
        repo = UserRepository(db_session)

        # Create a user to delete
        user = await repo.create(
            username="todelete",
            email="todelete@example.com",
            hashed_password="hash",
        )
        await db_session.commit()

        # Delete it
        result = await repo.delete(user.id)
        await db_session.commit()

        assert result is True

        # Verify it's deleted
        deleted = await repo.get_by_id(user.id)
        assert deleted is None

    async def test_delete_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Test deleting non-existent record."""
        repo = UserRepository(db_session)
        result = await repo.delete(uuid.uuid4())

        assert result is False
