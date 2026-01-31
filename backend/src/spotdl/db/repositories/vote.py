"""Vote repository for vote data access."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from spotdl.db.models.vote import Vote, VoteType
from spotdl.db.repositories.base import BaseRepository


class VoteRepository(BaseRepository[Vote]):
    """Repository for Vote model operations."""

    model = Vote

    async def get_user_vote(
        self, match_id: uuid.UUID, user_id: uuid.UUID
    ) -> Vote | None:
        """Get a user's vote on a match."""
        query = select(Vote).where(
            Vote.match_id == match_id,
            Vote.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_match_votes(
        self, match_id: uuid.UUID
    ) -> list[Vote]:
        """Get all votes for a match."""
        query = select(Vote).where(Vote.match_id == match_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_votes(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Vote]:
        """Get all votes by a user."""
        query = (
            select(Vote)
            .where(Vote.user_id == user_id)
            .order_by(Vote.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def upsert_vote(
        self,
        match_id: uuid.UUID,
        user_id: uuid.UUID,
        vote_type: VoteType,
    ) -> Vote:
        """Create or update a vote."""
        existing = await self.get_user_vote(match_id, user_id)

        if existing:
            existing.vote_type = vote_type
            await self.session.flush()
            return existing

        return await self.create(
            match_id=match_id,
            user_id=user_id,
            vote_type=vote_type,
        )

    async def delete_vote(
        self, match_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete a user's vote on a match."""
        vote = await self.get_user_vote(match_id, user_id)
        if vote is None:
            return False

        await self.session.delete(vote)
        await self.session.flush()
        return True
