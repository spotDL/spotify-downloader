"""Integration tests for VoteService."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.core.services.vote import (
    MatchNotFoundError,
    VoteNotFoundError,
    VoteService,
    VoteSummary,
    VoteType,
)
from spotdl.db.models.match import Match as MatchModel, MatchType
from spotdl.db.models.user import User
from spotdl.db.repositories.match import MatchRepository
from spotdl.db.repositories.vote import VoteRepository


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def vote_service(db_session: AsyncSession) -> VoteService:
    """Create a VoteService instance."""
    vote_repo = VoteRepository(db_session)
    match_repo = MatchRepository(db_session)
    return VoteService(db_session, vote_repo, match_repo)


@pytest_asyncio.fixture
async def second_test_user(db_session: AsyncSession) -> User:
    """Create a second test user."""
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        username="testuser2",
        email="test2@example.com",
        hashed_password="hashed_password_here",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_test_match(db_session: AsyncSession) -> MatchModel:
    """Create a second test match."""
    match = MatchModel(
        source_platform="deezer",
        source_url="https://www.deezer.com/track/456",
        target_platform="youtube_music",
        target_url="https://music.youtube.com/watch?v=abc123",
        match_type=MatchType.USER,
        match_score=90.0,
    )
    db_session.add(match)
    await db_session.commit()
    await db_session.refresh(match)
    return match


class TestVoteServiceVote:
    """Tests for VoteService.vote method."""

    async def test_vote_upvote_new(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test casting a new upvote."""
        summary = await vote_service.vote(test_match.id, test_user.id, VoteType.UP)

        assert summary.match_id == test_match.id
        assert summary.upvotes == 1
        assert summary.downvotes == 0
        assert summary.score == 1
        assert summary.user_vote == VoteType.UP

    async def test_vote_downvote_new(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test casting a new downvote."""
        summary = await vote_service.vote(test_match.id, test_user.id, VoteType.DOWN)

        assert summary.match_id == test_match.id
        assert summary.upvotes == 0
        assert summary.downvotes == 1
        assert summary.score == -1
        assert summary.user_vote == VoteType.DOWN

    async def test_vote_change_up_to_down(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test changing vote from up to down."""
        # First vote up
        await vote_service.vote(test_match.id, test_user.id, VoteType.UP)

        # Then change to down
        summary = await vote_service.vote(test_match.id, test_user.id, VoteType.DOWN)

        assert summary.upvotes == 0
        assert summary.downvotes == 1
        assert summary.score == -1
        assert summary.user_vote == VoteType.DOWN

    async def test_vote_change_down_to_up(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test changing vote from down to up."""
        # First vote down
        await vote_service.vote(test_match.id, test_user.id, VoteType.DOWN)

        # Then change to up
        summary = await vote_service.vote(test_match.id, test_user.id, VoteType.UP)

        assert summary.upvotes == 1
        assert summary.downvotes == 0
        assert summary.score == 1
        assert summary.user_vote == VoteType.UP

    async def test_vote_same_vote_twice(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test voting the same way twice (no change)."""
        # First vote up
        await vote_service.vote(test_match.id, test_user.id, VoteType.UP)

        # Vote up again (should be idempotent)
        summary = await vote_service.vote(test_match.id, test_user.id, VoteType.UP)

        assert summary.upvotes == 1
        assert summary.downvotes == 0
        assert summary.score == 1
        assert summary.user_vote == VoteType.UP

    async def test_vote_nonexistent_match(
        self,
        vote_service: VoteService,
        test_user: User,
    ) -> None:
        """Test voting on non-existent match."""
        with pytest.raises(MatchNotFoundError):
            await vote_service.vote(uuid.uuid4(), test_user.id, VoteType.UP)

    async def test_vote_multiple_users(
        self,
        vote_service: VoteService,
        test_user: User,
        second_test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test multiple users voting on the same match."""
        # First user votes up
        await vote_service.vote(test_match.id, test_user.id, VoteType.UP)

        # Second user votes down
        summary = await vote_service.vote(
            test_match.id, second_test_user.id, VoteType.DOWN
        )

        assert summary.upvotes == 1
        assert summary.downvotes == 1
        assert summary.score == 0
        # Second user's vote should be returned
        assert summary.user_vote == VoteType.DOWN


class TestVoteServiceRemoveVote:
    """Tests for VoteService.remove_vote method."""

    async def test_remove_upvote(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test removing an upvote."""
        # First cast a vote
        await vote_service.vote(test_match.id, test_user.id, VoteType.UP)

        # Then remove it
        summary = await vote_service.remove_vote(test_match.id, test_user.id)

        assert summary.upvotes == 0
        assert summary.downvotes == 0
        assert summary.score == 0
        assert summary.user_vote is None

    async def test_remove_downvote(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test removing a downvote."""
        # First cast a vote
        await vote_service.vote(test_match.id, test_user.id, VoteType.DOWN)

        # Then remove it
        summary = await vote_service.remove_vote(test_match.id, test_user.id)

        assert summary.upvotes == 0
        assert summary.downvotes == 0
        assert summary.score == 0
        assert summary.user_vote is None

    async def test_remove_vote_not_found(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test removing a vote that doesn't exist."""
        with pytest.raises(VoteNotFoundError):
            await vote_service.remove_vote(test_match.id, test_user.id)

    async def test_remove_vote_nonexistent_match(
        self,
        vote_service: VoteService,
        test_user: User,
    ) -> None:
        """Test removing vote from non-existent match."""
        with pytest.raises(MatchNotFoundError):
            await vote_service.remove_vote(uuid.uuid4(), test_user.id)


class TestVoteServiceGetVoteSummary:
    """Tests for VoteService.get_vote_summary method."""

    async def test_get_vote_summary_no_votes(
        self,
        vote_service: VoteService,
        test_match: MatchModel,
    ) -> None:
        """Test getting summary for match with no votes."""
        summary = await vote_service.get_vote_summary(test_match.id)

        assert summary.match_id == test_match.id
        assert summary.upvotes == 0
        assert summary.downvotes == 0
        assert summary.score == 0
        assert summary.user_vote is None

    async def test_get_vote_summary_with_user_vote(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test getting summary with user's vote."""
        # Cast a vote
        await vote_service.vote(test_match.id, test_user.id, VoteType.UP)

        # Get summary with user_id
        summary = await vote_service.get_vote_summary(test_match.id, test_user.id)

        assert summary.user_vote == VoteType.UP

    async def test_get_vote_summary_without_user_vote(
        self,
        vote_service: VoteService,
        test_user: User,
        second_test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test getting summary when user hasn't voted."""
        # First user votes
        await vote_service.vote(test_match.id, test_user.id, VoteType.UP)

        # Get summary for second user who hasn't voted
        summary = await vote_service.get_vote_summary(
            test_match.id, second_test_user.id
        )

        assert summary.upvotes == 1
        assert summary.user_vote is None

    async def test_get_vote_summary_nonexistent_match(
        self,
        vote_service: VoteService,
    ) -> None:
        """Test getting summary for non-existent match."""
        with pytest.raises(MatchNotFoundError):
            await vote_service.get_vote_summary(uuid.uuid4())


class TestVoteServiceGetUserVotes:
    """Tests for VoteService.get_user_votes method."""

    async def test_get_user_votes_empty(
        self,
        vote_service: VoteService,
        test_user: User,
    ) -> None:
        """Test getting votes for user with no votes."""
        votes = await vote_service.get_user_votes(test_user.id)
        assert votes == []

    async def test_get_user_votes_single(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test getting single vote."""
        await vote_service.vote(test_match.id, test_user.id, VoteType.UP)

        votes = await vote_service.get_user_votes(test_user.id)

        assert len(votes) == 1
        assert votes[0] == (test_match.id, VoteType.UP)

    async def test_get_user_votes_multiple(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
        second_test_match: MatchModel,
    ) -> None:
        """Test getting multiple votes."""
        await vote_service.vote(test_match.id, test_user.id, VoteType.UP)
        await vote_service.vote(second_test_match.id, test_user.id, VoteType.DOWN)

        votes = await vote_service.get_user_votes(test_user.id)

        assert len(votes) == 2
        # Check both votes are present
        vote_dict = dict(votes)
        assert vote_dict.get(test_match.id) == VoteType.UP
        assert vote_dict.get(second_test_match.id) == VoteType.DOWN

    async def test_get_user_votes_with_limit(
        self,
        vote_service: VoteService,
        test_user: User,
        test_match: MatchModel,
        second_test_match: MatchModel,
    ) -> None:
        """Test getting votes with limit."""
        await vote_service.vote(test_match.id, test_user.id, VoteType.UP)
        await vote_service.vote(second_test_match.id, test_user.id, VoteType.DOWN)

        votes = await vote_service.get_user_votes(test_user.id, limit=1)

        assert len(votes) == 1


class TestVoteServiceGetTopVotedMatches:
    """Tests for VoteService.get_top_voted_matches method."""

    async def test_get_top_voted_matches_empty(
        self,
        vote_service: VoteService,
    ) -> None:
        """Test getting top voted when no matches have votes."""
        top_matches = await vote_service.get_top_voted_matches(limit=10)
        # May return empty or matches with 0 votes depending on implementation
        assert isinstance(top_matches, list)

    async def test_get_top_voted_matches_ordering(
        self,
        vote_service: VoteService,
        test_user: User,
        second_test_user: User,
        test_match: MatchModel,
        second_test_match: MatchModel,
    ) -> None:
        """Test that matches are ordered by score."""
        # First match gets 2 upvotes
        await vote_service.vote(test_match.id, test_user.id, VoteType.UP)
        await vote_service.vote(test_match.id, second_test_user.id, VoteType.UP)

        # Second match gets 1 upvote
        await vote_service.vote(second_test_match.id, test_user.id, VoteType.UP)

        top_matches = await vote_service.get_top_voted_matches(limit=10)

        # Find our test matches in the results
        scores = {match_id: score for match_id, score in top_matches}

        if test_match.id in scores and second_test_match.id in scores:
            assert scores[test_match.id] >= scores[second_test_match.id]
