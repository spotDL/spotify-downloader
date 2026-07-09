"""Stats repository: the admin dashboard's ``SELECT count(*)`` aggregates (§6.2).

The sole holder of the aggregate-count SQL that backs ``GET /admin/stats``. Every
method is a single ``SELECT count(*)`` over one table (optionally filtered by a
status enum); none loads rows into the identity map. The repository never commits
— the caller owns the unit of work.

Kept deliberately granular (one count per method) so :class:`AdminService` can
assemble the ``AdminStats`` view while this module stays the only place the ORM /
SQLAlchemy count queries live (the layering contract, spec §6).
"""

from __future__ import annotations

from spotdl_core.model import MatchStatus
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.enums import ReportStatus
from spotdl_server.db.models import Match, Report, User, Vote


class StatsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_users(self) -> int:
        """Total number of registered users."""
        return int(await self.session.scalar(select(func.count()).select_from(User)) or 0)

    async def count_matches(self) -> int:
        """Total number of match rows (all statuses)."""
        return int(await self.session.scalar(select(func.count()).select_from(Match)) or 0)

    async def count_matches_in_status(self, status: MatchStatus) -> int:
        """Number of matches currently in ``status`` (e.g. community-verified)."""
        return int(
            await self.session.scalar(
                select(func.count()).select_from(Match).where(Match.status == status)
            )
            or 0
        )

    async def count_votes(self) -> int:
        """Total number of vote-ledger rows."""
        return int(await self.session.scalar(select(func.count()).select_from(Vote)) or 0)

    async def count_reports(self) -> int:
        """Total number of correction reports (all statuses)."""
        return int(await self.session.scalar(select(func.count()).select_from(Report)) or 0)

    async def count_reports_in_status(self, status: ReportStatus) -> int:
        """Number of reports currently in ``status`` (e.g. pending review)."""
        return int(
            await self.session.scalar(
                select(func.count()).select_from(Report).where(Report.status == status)
            )
            or 0
        )
