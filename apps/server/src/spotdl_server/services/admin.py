"""AdminService — the minimal admin surface (spec §6.2 "Admin (minimal)").

Backs four operator actions over the community data: a paged user list, a
status-filtered report queue, an audited approve/reject **decision**, and a
dashboard of aggregate counts.

**v1 records a review state only — it does NOT auto-apply an approved correction
to canonical data.** ``decide_report`` stamps the report's ``status`` /
``reviewed_by`` / ``reviewed_at`` / ``review_note`` and returns it; wiring an
approved correction into an entity mutation is explicitly out of scope (spec §1
non-goal "Full moderation suite"; §6.2 "Admin (minimal)"). No implementer should
add an entity write here.

Nothing here imports FastAPI; the only ORM types returned are the ``User`` /
``Report`` rows named in the CONTRACT, which the router maps to schemas. Time flows
through the injected :class:`~spotdl_server.auth.clock.Clock` so ``reviewed_at`` is
deterministic; the service flushes (through the repositories) but never commits —
the caller owns the unit of work. The ``session`` is held so :meth:`stats` can
build the aggregate-count :class:`StatsRepository` (keeping that SQL in the
repository layer) without widening the CONTRACT constructor.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from spotdl_core.model import MatchStatus
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.auth.clock import Clock
from spotdl_server.db.enums import ReportStatus
from spotdl_server.db.models import Report, User
from spotdl_server.repositories.reports import ReportRepository
from spotdl_server.repositories.stats import StatsRepository
from spotdl_server.repositories.users import UserRepository
from spotdl_server.services.errors import NotFoundError


@dataclass(frozen=True, slots=True)
class AdminStats:
    """Aggregate community-health counts for the admin dashboard (``GET /admin/stats``)."""

    users_total: int
    matches_total: int
    community_verified_matches: int
    rejected_matches: int
    votes_total: int
    reports_pending: int
    reports_total: int


class AdminService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        clock: Clock,
        users: UserRepository,
        reports: ReportRepository,
    ) -> None:
        self._session = session
        self._clock = clock
        self._users = users
        self._reports = reports

    async def list_users(self, *, limit: int, offset: int) -> tuple[list[User], int]:
        """A ``(page, total)`` slice of the user list (newest first) for the admin UI."""
        return await self._users.list_users(limit=limit, offset=offset)

    async def reports_queue(
        self, *, status: ReportStatus = ReportStatus.PENDING, limit: int, offset: int
    ) -> tuple[list[Report], int]:
        """A ``(page, total)`` slice of the report queue filtered by ``status``.

        Defaults to the ``pending`` queue (the FIFO review backlog); the ``total``
        is the count in that status before paging so the UI can render controls.
        """
        return await self._reports.list_by_status(status, limit=limit, offset=offset)

    async def decide_report(
        self, *, report_id: UUID, reviewer_id: UUID, approve: bool, note: str | None
    ) -> Report:
        """Record an admin decision on a report and return the stamped row.

        Loads the report (``NotFoundError`` if it does not exist), then stamps
        ``status`` (``approved``/``rejected``), the reviewer, the note, and the
        review time from the shared clock. **Records the review state only — v1
        does not auto-apply an approved correction to canonical data.**
        """
        report = await self._reports.get(report_id)
        if report is None:
            raise NotFoundError(entity_type="report", entity_id=report_id)
        await self._reports.set_decision(
            report,
            status=ReportStatus.APPROVED if approve else ReportStatus.REJECTED,
            reviewed_by=reviewer_id,
            note=note,
            now=self._clock.now(),
        )
        return report

    async def stats(self) -> AdminStats:
        """Compute the aggregate community-health counts for the dashboard."""
        stats = StatsRepository(self._session)
        return AdminStats(
            users_total=await stats.count_users(),
            matches_total=await stats.count_matches(),
            community_verified_matches=await stats.count_matches_in_status(
                MatchStatus.COMMUNITY_VERIFIED
            ),
            rejected_matches=await stats.count_matches_in_status(MatchStatus.REJECTED),
            votes_total=await stats.count_votes(),
            reports_pending=await stats.count_reports_in_status(ReportStatus.PENDING),
            reports_total=await stats.count_reports(),
        )
