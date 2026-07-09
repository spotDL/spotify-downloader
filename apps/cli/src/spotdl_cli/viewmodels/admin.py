"""``AdminViewModel`` — the admin-lite reports queue + stats (CONTRACT A/F).

Gated by ``session.is_admin``: the section is hidden when the user is not an admin,
and these methods additionally refuse defensively (no client call) so a stray call
can never hit an admin endpoint as a non-admin.
"""

from __future__ import annotations

from uuid import UUID

from spotdl_cli.viewmodels.app_state import SessionSnapshot
from spotdl_cli.viewmodels.base import ErrorDisplay, Loadable, guard
from spotdl_cli.viewmodels.mappers import report_row
from spotdl_cli.viewmodels.protocol import SpotdlClientProtocol
from spotdl_cli.viewmodels.types import ReportRow, StatsRow
from spotdl_cli.views import StatsView

_NOT_ADMIN = ErrorDisplay("admin access required", code=None, severity="error")


class AdminViewModel:
    def __init__(self, client: SpotdlClientProtocol, session: SessionSnapshot) -> None:
        self._client = client
        self._session = session

    async def load_reports(self, *, status: str = "pending") -> Loadable[tuple[ReportRow, ...]]:
        if not self._session.is_admin:
            return Loadable.failed(_NOT_ADMIN)

        async def _run() -> tuple[ReportRow, ...]:
            reports = await self._client.admin_reports(status=status)
            return tuple(report_row(report) for report in reports)

        return await guard(_run())

    async def approve(self, report_id: UUID, note: str | None) -> Loadable[ReportRow]:
        if not self._session.is_admin:
            return Loadable.failed(_NOT_ADMIN)

        async def _run() -> ReportRow:
            return report_row(await self._client.approve_report(report_id, note=note))

        return await guard(_run())

    async def reject(self, report_id: UUID, note: str | None) -> Loadable[ReportRow]:
        if not self._session.is_admin:
            return Loadable.failed(_NOT_ADMIN)

        async def _run() -> ReportRow:
            return report_row(await self._client.reject_report(report_id, note=note))

        return await guard(_run())

    async def stats(self) -> Loadable[StatsRow]:
        if not self._session.is_admin:
            return Loadable.failed(_NOT_ADMIN)

        async def _run() -> StatsRow:
            return _stats_row(await self._client.admin_stats(), self._session.matcher_version)

        return await guard(_run())


def _stats_row(stats: StatsView, matcher_version: str) -> StatsRow:
    # AdminStats carries no canonical-track total, so ``tracks`` reports 0 (the
    # server aggregate exposes users/matches/reports/votes only).
    return StatsRow(
        users=stats.users_total,
        tracks=0,
        matches=stats.matches_total,
        pending_reports=stats.reports_pending,
        matcher_version=matcher_version,
    )
