"""ReportService — metadata-correction reports (spec §6.2, CONTRACT).

A logged-in user files a correction against a canonical entity (``POST /reports``)
and can review the state of their own submissions (``GET /reports/me``). The
service creates a ``pending`` report and lists a reporter's own reports.

**Subject existence is not hard-verified in v1** (documented): a report may target
any well-formed ``(subject_type, subject_id)`` the reporter saw — admin triage
judges validity. ``subject_type`` is normalized through :class:`EntityType` so a
non-canonical type is rejected at the service boundary too (the router already
rejects it at the schema, so this is defence in depth).

Nothing here imports FastAPI; the only ORM type returned is the ``Report`` row
named in the CONTRACT, which the router maps to a schema. Time flows through the
injected :class:`~spotdl_server.auth.clock.Clock`; the service flushes (through
the repository) but never commits — the caller owns the unit of work.
"""

from __future__ import annotations

from uuid import UUID

from spotdl_core.model import EntityType
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.auth.clock import Clock
from spotdl_server.db.models import Report
from spotdl_server.repositories.reports import ReportRepository


class ReportService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        clock: Clock,
        reports: ReportRepository,
    ) -> None:
        self._session = session
        self._clock = clock
        self._reports = reports

    async def submit(
        self,
        *,
        reporter_id: UUID,
        subject_type: EntityType,
        subject_id: UUID,
        field: str | None,
        proposed_value: str | None,
        reason: str | None,
    ) -> Report:
        """Create a ``pending`` correction report and return it.

        ``subject_type`` is normalized through :class:`EntityType` (a bad value
        raises ``ValueError``); the subject entity itself is **not** verified to
        exist — admin triage judges the report's validity.
        """
        subject_type = EntityType(subject_type)
        return await self._reports.create(
            reporter_id=reporter_id,
            subject_type=subject_type,
            subject_id=subject_id,
            field=field,
            proposed_value=proposed_value,
            reason=reason,
        )

    async def list_own(self, reporter_id: UUID) -> list[Report]:
        """Every report the caller filed (newest first)."""
        return await self._reports.list_by_reporter(reporter_id)
