"""Vote service for managing votes on matches."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from spotdl.db.repositories.match import MatchRepository
    from spotdl.db.repositories.vote import VoteRepository


class VoteType(str, Enum):
    """Vote types."""

    UP = "up"
    DOWN = "down"


class VoteServiceError(Exception):
    """Base exception for vote service errors."""


class VoteNotFoundError(VoteServiceError):
    """Raised when vote is not found."""


class DuplicateVoteError(VoteServiceError):
    """Raised when user has already voted."""


class MatchNotFoundError(VoteServiceError):
    """Raised when match is not found."""


@dataclass
class VoteSummary:
    """Summary of votes on a match."""

    match_id: UUID
    upvotes: int
    downvotes: int
    score: int
    user_vote: VoteType | None = None

    @property
    def total_votes(self) -> int:
        """Get total number of votes."""
        return self.upvotes + self.downvotes

    @property
    def confidence(self) -> float:
        """Calculate confidence score based on votes."""
        if self.total_votes == 0:
            return 0.5

        # Wilson score interval lower bound
        # Simplified version for quick calculation
        positive_ratio = self.upvotes / self.total_votes
        z = 1.96  # 95% confidence

        n = self.total_votes
        phat = positive_ratio

        denominator = 1 + z * z / n
        center = phat + z * z / (2 * n)
        spread = z * ((phat * (1 - phat) + z * z / (4 * n)) / n) ** 0.5

        lower_bound = (center - spread) / denominator
        return max(0.0, min(1.0, lower_bound))


class VoteService:
    """
    Service for managing votes on matches.

    Handles vote creation, updates, and aggregation.
    Integrates with the database through repositories.
    """

    def __init__(
        self,
        session: "AsyncSession",
        vote_repo: "VoteRepository",
        match_repo: "MatchRepository",
    ) -> None:
        """
        Initialize the vote service.

        Args:
            session: Database session
            vote_repo: Vote repository
            match_repo: Match repository
        """
        self._session = session
        self._vote_repo = vote_repo
        self._match_repo = match_repo

    async def vote(
        self,
        match_id: UUID,
        user_id: UUID,
        vote_type: VoteType,
    ) -> VoteSummary:
        """
        Cast a vote on a match.

        Args:
            match_id: Match to vote on
            user_id: User casting the vote
            vote_type: Type of vote (up/down)

        Returns:
            Updated vote summary

        Raises:
            MatchNotFoundError: If match doesn't exist
        """
        # Check if match exists
        match = await self._match_repo.get_by_id(match_id)
        if match is None:
            raise MatchNotFoundError(f"Match not found: {match_id}")

        # Check for existing vote
        existing_vote = await self._vote_repo.get_user_vote(match_id, user_id)

        if existing_vote:
            # Update existing vote
            if existing_vote.vote_type == vote_type.value:
                # Same vote, no change needed
                pass
            else:
                # Change vote
                existing_vote.vote_type = vote_type.value
                await self._session.commit()

                # Update match vote counts
                if vote_type == VoteType.UP:
                    match.upvotes += 1
                    match.downvotes -= 1
                else:
                    match.upvotes -= 1
                    match.downvotes += 1
                await self._session.commit()
        else:
            # Create new vote
            await self._vote_repo.create(
                match_id=match_id,
                user_id=user_id,
                vote_type=vote_type.value,
            )

            # Update match vote counts
            if vote_type == VoteType.UP:
                match.upvotes += 1
            else:
                match.downvotes += 1
            await self._session.commit()

        return await self.get_vote_summary(match_id, user_id)

    async def remove_vote(
        self,
        match_id: UUID,
        user_id: UUID,
    ) -> VoteSummary:
        """
        Remove a vote from a match.

        Args:
            match_id: Match to remove vote from
            user_id: User who cast the vote

        Returns:
            Updated vote summary

        Raises:
            VoteNotFoundError: If vote doesn't exist
            MatchNotFoundError: If match doesn't exist
        """
        # Check if match exists
        match = await self._match_repo.get_by_id(match_id)
        if match is None:
            raise MatchNotFoundError(f"Match not found: {match_id}")

        # Find the vote
        vote = await self._vote_repo.get_user_vote(match_id, user_id)
        if vote is None:
            raise VoteNotFoundError(f"No vote found for user {user_id} on match {match_id}")

        # Update match counts before deleting
        if vote.vote_type == VoteType.UP.value:
            match.upvotes -= 1
        else:
            match.downvotes -= 1

        # Delete the vote
        await self._vote_repo.delete(vote.id)
        await self._session.commit()

        return await self.get_vote_summary(match_id, user_id)

    async def get_vote_summary(
        self,
        match_id: UUID,
        user_id: UUID | None = None,
    ) -> VoteSummary:
        """
        Get vote summary for a match.

        Args:
            match_id: Match to get summary for
            user_id: Optional user to get their vote

        Returns:
            Vote summary

        Raises:
            MatchNotFoundError: If match doesn't exist
        """
        match = await self._match_repo.get_by_id(match_id)
        if match is None:
            raise MatchNotFoundError(f"Match not found: {match_id}")

        user_vote = None
        if user_id:
            vote = await self._vote_repo.get_user_vote(match_id, user_id)
            if vote:
                user_vote = VoteType(vote.vote_type)

        return VoteSummary(
            match_id=match_id,
            upvotes=match.upvotes,
            downvotes=match.downvotes,
            score=match.upvotes - match.downvotes,
            user_vote=user_vote,
        )

    async def get_user_votes(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[UUID, VoteType]]:
        """
        Get all votes by a user.

        Args:
            user_id: User to get votes for
            limit: Maximum number of votes
            offset: Offset for pagination

        Returns:
            List of (match_id, vote_type) tuples
        """
        votes = await self._vote_repo.get_user_votes(user_id, skip=offset, limit=limit)
        return [(v.match_id, VoteType(v.vote_type)) for v in votes]

    async def get_top_voted_matches(
        self,
        limit: int = 10,
    ) -> list[tuple[UUID, int]]:
        """
        Get matches with highest vote scores.

        Args:
            limit: Maximum number of matches

        Returns:
            List of (match_id, score) tuples
        """
        matches = await self._match_repo.get_top_voted(limit=limit)
        return [(m.id, m.upvotes - m.downvotes) for m in matches]
