"""Report repository: metadata-correction reports + their review state (§6.1).

The sole holder of the ``reports`` table's query code. A report targets a
canonical entity by a polymorphic ``(subject_type, subject_id)`` pair (no
cross-table FK, per the Plan 6 contract) and carries a minimal review state
(``pending | approved | rejected``). This repository creates a ``pending`` report,
fetches one by id, lists a reporter's own reports and the admin review queue by
status (paged, with a total count for the admin UI), and stamps an admin decision.

Every time-dependent mutation takes an explicit ``now`` (from the injected
:class:`~spotdl_server.auth.clock.Clock`) so ``reviewed_at`` is deterministic in
tests. The repository never commits; the caller owns the unit of work.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from spotdl_core.model import EntityType
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.enums import ReportStatus
from spotdl_server.db.models import Report


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        reporter_id: uuid.UUID | None,
        subject_type: EntityType,
        subject_id: uuid.UUID,
        field: str | None,
        proposed_value: str | None,
        reason: str | None,
    ) -> Report:
        """Insert a ``pending`` correction report and return it (with its id)."""
        report = Report(
            reporter_id=reporter_id,
            subject_type=subject_type,
            subject_id=subject_id,
            field=field,
            proposed_value=proposed_value,
            reason=reason,
            status=ReportStatus.PENDING,
        )
        self.session.add(report)
        await self.session.flush()
        return report

    async def get(self, report_id: uuid.UUID) -> Report | None:
        return await self.session.get(Report, report_id)

    async def list_by_reporter(self, reporter_id: uuid.UUID) -> list[Report]:
        """Every report a given reporter filed, newest first."""
        result = await self.session.execute(
            select(Report)
            .where(Report.reporter_id == reporter_id)
            .order_by(Report.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_status(
        self, status: ReportStatus, *, limit: int, offset: int
    ) -> tuple[list[Report], int]:
        """A paged slice of reports in ``status`` plus the total in that status.

        The total is the count *before* paging so the admin queue can render page
        controls; the slice is ordered oldest-first (a FIFO review queue).
        """
        total = await self.session.scalar(
            select(func.count()).select_from(Report).where(Report.status == status)
        )
        result = await self.session.execute(
            select(Report)
            .where(Report.status == status)
            .order_by(Report.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    async def set_decision(
        self,
        report: Report,
        *,
        status: ReportStatus,
        reviewed_by: uuid.UUID,
        note: str | None,
        now: datetime,
    ) -> None:
        """Stamp an admin decision on ``report`` (status + reviewer + note + time)."""
        report.status = status
        report.reviewed_by = reviewed_by
        report.review_note = note
        report.reviewed_at = now
        await self.session.flush()
