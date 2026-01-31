"""Match repository for match data access."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from spotdl.db.models.match import Match, MatchType
from spotdl.db.repositories.base import BaseRepository


class MatchRepository(BaseRepository[Match]):
    """Repository for Match model operations."""

    model = Match

    async def get_by_source_url(
        self,
        source_url: str,
        target_platform: str | None = None,
    ) -> list[Match]:
        """Get all matches for a source URL."""
        query = select(Match).where(Match.source_url == source_url)

        if target_platform:
            query = query.where(Match.target_platform == target_platform)

        # Order by score and votes
        query = query.order_by(
            Match.match_score.desc().nullslast(),
            (Match.upvotes - Match.downvotes).desc(),
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_source_and_target(
        self,
        source_url: str,
        target_platform: str,
        target_url: str,
    ) -> Match | None:
        """Get a specific match by source and target."""
        query = select(Match).where(
            Match.source_url == source_url,
            Match.target_platform == target_platform,
            Match.target_url == target_url,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_submissions(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Match]:
        """Get all matches submitted by a user."""
        query = (
            select(Match)
            .where(Match.submitted_by == user_id)
            .order_by(Match.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_pending_verification(
        self, *, limit: int = 50
    ) -> list[Match]:
        """Get user-submitted matches pending verification."""
        query = (
            select(Match)
            .where(
                Match.match_type == MatchType.USER,
                Match.verified_by.is_(None),
            )
            .order_by(
                (Match.upvotes - Match.downvotes).desc(),
                Match.created_at.asc(),
            )
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_vote_counts(
        self, match_id: uuid.UUID
    ) -> Match | None:
        """Recalculate vote counts from votes table."""
        from spotdl.db.models.vote import Vote, VoteType

        match = await self.get_by_id(match_id)
        if match is None:
            return None

        # Count upvotes
        up_query = select(func.count()).select_from(Vote).where(
            Vote.match_id == match_id,
            Vote.vote_type == VoteType.UP,
        )
        up_result = await self.session.execute(up_query)
        upvotes = up_result.scalar() or 0

        # Count downvotes
        down_query = select(func.count()).select_from(Vote).where(
            Vote.match_id == match_id,
            Vote.vote_type == VoteType.DOWN,
        )
        down_result = await self.session.execute(down_query)
        downvotes = down_result.scalar() or 0

        match.upvotes = upvotes
        match.downvotes = downvotes
        await self.session.flush()

        return match
