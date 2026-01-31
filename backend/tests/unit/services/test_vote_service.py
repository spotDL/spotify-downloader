"""Tests for VoteService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from spotdl.core.services.vote import (
    DuplicateVoteError,
    MatchNotFoundError,
    VoteNotFoundError,
    VoteServiceError,
    VoteSummary,
    VoteType,
)


class TestVoteType:
    """Tests for VoteType enum."""

    def test_vote_type_up(self) -> None:
        """Test UP vote type."""
        assert VoteType.UP.value == "up"

    def test_vote_type_down(self) -> None:
        """Test DOWN vote type."""
        assert VoteType.DOWN.value == "down"

    def test_vote_type_from_string(self) -> None:
        """Test creating VoteType from string."""
        assert VoteType("up") == VoteType.UP
        assert VoteType("down") == VoteType.DOWN


class TestVoteSummary:
    """Tests for VoteSummary dataclass."""

    def test_vote_summary_score(self) -> None:
        """Test vote summary score calculation."""
        summary = VoteSummary(
            match_id=uuid.uuid4(),
            upvotes=10,
            downvotes=3,
            score=7,
        )
        assert summary.score == 7

    def test_vote_summary_total_votes(self) -> None:
        """Test total_votes property."""
        summary = VoteSummary(
            match_id=uuid.uuid4(),
            upvotes=10,
            downvotes=5,
            score=5,
        )
        assert summary.total_votes == 15

    def test_vote_summary_confidence_no_votes(self) -> None:
        """Test confidence with no votes."""
        summary = VoteSummary(
            match_id=uuid.uuid4(),
            upvotes=0,
            downvotes=0,
            score=0,
        )
        assert summary.confidence == 0.5

    def test_vote_summary_confidence_all_upvotes(self) -> None:
        """Test confidence with all upvotes."""
        summary = VoteSummary(
            match_id=uuid.uuid4(),
            upvotes=100,
            downvotes=0,
            score=100,
        )
        assert summary.confidence > 0.9

    def test_vote_summary_confidence_all_downvotes(self) -> None:
        """Test confidence with all downvotes."""
        summary = VoteSummary(
            match_id=uuid.uuid4(),
            upvotes=0,
            downvotes=100,
            score=-100,
        )
        assert summary.confidence < 0.1

    def test_vote_summary_confidence_mixed(self) -> None:
        """Test confidence with mixed votes."""
        summary = VoteSummary(
            match_id=uuid.uuid4(),
            upvotes=60,
            downvotes=40,
            score=20,
        )
        # Should be around 0.5 for balanced votes
        assert 0.4 < summary.confidence < 0.6

    def test_vote_summary_user_vote(self) -> None:
        """Test user_vote property."""
        summary = VoteSummary(
            match_id=uuid.uuid4(),
            upvotes=5,
            downvotes=2,
            score=3,
            user_vote=VoteType.UP,
        )
        assert summary.user_vote == VoteType.UP


class TestVoteServiceErrors:
    """Tests for VoteService exceptions."""

    def test_vote_service_error(self) -> None:
        """Test VoteServiceError."""
        error = VoteServiceError("Test error")
        assert str(error) == "Test error"

    def test_vote_not_found_error(self) -> None:
        """Test VoteNotFoundError."""
        error = VoteNotFoundError("Vote not found")
        assert isinstance(error, VoteServiceError)
        assert str(error) == "Vote not found"

    def test_duplicate_vote_error(self) -> None:
        """Test DuplicateVoteError."""
        error = DuplicateVoteError("Already voted")
        assert isinstance(error, VoteServiceError)
        assert str(error) == "Already voted"

    def test_match_not_found_error(self) -> None:
        """Test MatchNotFoundError."""
        error = MatchNotFoundError("Match not found")
        assert isinstance(error, VoteServiceError)
        assert str(error) == "Match not found"


class TestVoteSummaryEdgeCases:
    """Tests for VoteSummary edge cases."""

    def test_vote_summary_single_upvote(self) -> None:
        """Test confidence with single upvote."""
        summary = VoteSummary(
            match_id=uuid.uuid4(),
            upvotes=1,
            downvotes=0,
            score=1,
        )
        # With only 1 vote, confidence should be low
        assert summary.confidence < 0.8

    def test_vote_summary_many_votes_high_confidence(self) -> None:
        """Test confidence increases with more votes."""
        # Few votes
        summary_few = VoteSummary(
            match_id=uuid.uuid4(),
            upvotes=9,
            downvotes=1,
            score=8,
        )

        # Many votes
        summary_many = VoteSummary(
            match_id=uuid.uuid4(),
            upvotes=90,
            downvotes=10,
            score=80,
        )

        # More votes should give higher confidence
        assert summary_many.confidence > summary_few.confidence
