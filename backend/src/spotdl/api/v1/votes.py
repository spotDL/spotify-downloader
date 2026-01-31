"""Vote API endpoints."""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.api.v1.auth import get_current_user_id, get_current_user_id_optional
from spotdl.db.database import get_db_session
from spotdl.db.models.vote import VoteType
from spotdl.db.repositories.match import MatchRepository
from spotdl.db.repositories.vote import VoteRepository

router = APIRouter(prefix="/votes")


class VoteRequest(BaseModel):
    """Request model for casting a vote."""

    match_id: UUID
    vote_type: str  # 'up' or 'down'


class VoteResponse(BaseModel):
    """Response model for a vote operation."""

    match_id: UUID
    upvotes: int
    downvotes: int
    score: int
    user_vote: str | None = None
    confidence: float


class VoteSummaryResponse(BaseModel):
    """Response model for vote summary."""

    match_id: UUID
    upvotes: int
    downvotes: int
    score: int
    total_votes: int
    confidence: float
    user_vote: str | None = None


class UserVoteItem(BaseModel):
    """A single user vote item."""

    match_id: str
    vote_type: str
    created_at: str


class UserVotesResponse(BaseModel):
    """Response model for user votes list."""

    votes: list[UserVoteItem]


def calculate_wilson_score(upvotes: int, downvotes: int) -> float:
    """
    Calculate Wilson score confidence interval.

    This gives a lower bound on the true proportion of positive votes.
    """
    n = upvotes + downvotes
    if n == 0:
        return 0.0

    p = upvotes / n
    z = 1.96  # 95% confidence

    denominator = 1 + z * z / n
    centre_adjusted_probability = p + z * z / (2 * n)
    adjusted_standard_deviation = math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)

    lower_bound = (
        centre_adjusted_probability - z * adjusted_standard_deviation
    ) / denominator

    return max(0.0, min(1.0, lower_bound))


@router.post("")
async def cast_vote(
    request: VoteRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> VoteResponse:
    """
    Cast a vote on a match.

    Requires authentication.

    Args:
        request: Match ID and vote type
        user_id: Current user ID (from auth)
        db: Database session

    Returns:
        Updated vote summary
    """
    # Validate vote type
    try:
        vote_type = VoteType(request.vote_type)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Invalid vote type. Must be 'up' or 'down'",
        ) from e

    match_repo = MatchRepository(db)
    vote_repo = VoteRepository(db)

    # Check if match exists
    match = await match_repo.get_by_id(request.match_id)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found",
        )

    # Create or update the vote
    await vote_repo.upsert_vote(
        match_id=request.match_id,
        user_id=user_id,
        vote_type=vote_type,
    )

    # Update vote counts on the match
    updated_match = await match_repo.update_vote_counts(request.match_id)
    if updated_match is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to update vote counts",
        )

    confidence = calculate_wilson_score(updated_match.upvotes, updated_match.downvotes)

    return VoteResponse(
        match_id=request.match_id,
        upvotes=updated_match.upvotes,
        downvotes=updated_match.downvotes,
        score=updated_match.upvotes - updated_match.downvotes,
        user_vote=vote_type.value,
        confidence=confidence,
    )


@router.delete("/{match_id}")
async def remove_vote(
    match_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> VoteResponse:
    """
    Remove a vote from a match.

    Requires authentication.

    Args:
        match_id: Match to remove vote from
        user_id: Current user ID (from auth)
        db: Database session

    Returns:
        Updated vote summary
    """
    match_repo = MatchRepository(db)
    vote_repo = VoteRepository(db)

    # Check if match exists
    match = await match_repo.get_by_id(match_id)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found",
        )

    # Delete the vote
    await vote_repo.delete_vote(match_id=match_id, user_id=user_id)

    # Update vote counts on the match
    updated_match = await match_repo.update_vote_counts(match_id)
    if updated_match is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to update vote counts",
        )

    confidence = calculate_wilson_score(updated_match.upvotes, updated_match.downvotes)

    return VoteResponse(
        match_id=match_id,
        upvotes=updated_match.upvotes,
        downvotes=updated_match.downvotes,
        score=updated_match.upvotes - updated_match.downvotes,
        user_vote=None,
        confidence=confidence,
    )


@router.get("/{match_id}")
async def get_vote_summary(
    match_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[UUID | None, Depends(get_current_user_id_optional)] = None,
) -> VoteSummaryResponse:
    """
    Get vote summary for a match.

    Args:
        match_id: Match to get votes for
        db: Database session
        user_id: Optional current user ID (from auth)

    Returns:
        Vote summary
    """
    match_repo = MatchRepository(db)
    vote_repo = VoteRepository(db)

    # Get match
    match = await match_repo.get_by_id(match_id)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found",
        )

    # Get user's vote if authenticated
    user_vote = None
    if user_id:
        vote = await vote_repo.get_user_vote(match_id=match_id, user_id=user_id)
        if vote:
            user_vote = vote.vote_type

    confidence = calculate_wilson_score(match.upvotes, match.downvotes)

    return VoteSummaryResponse(
        match_id=match_id,
        upvotes=match.upvotes,
        downvotes=match.downvotes,
        score=match.upvotes - match.downvotes,
        total_votes=match.upvotes + match.downvotes,
        confidence=confidence,
        user_vote=user_vote,
    )


@router.get("/user/me")
async def get_my_votes(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 50,
    offset: int = 0,
) -> UserVotesResponse:
    """
    Get current user's votes.

    Requires authentication.

    Args:
        user_id: Current user ID (from auth)
        db: Database session
        limit: Maximum number of votes to return
        offset: Offset for pagination

    Returns:
        List of user's votes
    """
    vote_repo = VoteRepository(db)

    votes = await vote_repo.get_user_votes(
        user_id=user_id,
        skip=offset,
        limit=limit,
    )

    return UserVotesResponse(
        votes=[
            UserVoteItem(
                match_id=str(vote.match_id),
                vote_type=vote.vote_type,
                created_at=vote.created_at.isoformat() if vote.created_at else "",
            )
            for vote in votes
        ]
    )
