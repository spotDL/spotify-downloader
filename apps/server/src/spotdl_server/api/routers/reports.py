"""``/api/v1/reports`` — metadata-correction reports.

A thin HTTP shell over :class:`~spotdl_server.services.reports.ReportService`: it
requires an authenticated caller (``require_user`` — a JWT *or* a PAT), creates a
``pending`` report, and lists the caller's own reports. No business logic and no
ORM import (the ``Report`` rows are serialized by ``ReportResponse.model_validate``
without naming the ORM type). ``GET /reports/me`` is a deliberate minimal addition
to §6.2's literal endpoint list so a reporter can see the review state of their own
submissions. This router is mounted only when ``settings.auth_active()`` (never in
EMBEDDED mode).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from spotdl_server.api.deps import get_report_service, require_user
from spotdl_server.api.routers import ERROR_RESPONSES
from spotdl_server.api.schemas import CreateReportRequest, ReportResponse
from spotdl_server.auth.context import AuthContext
from spotdl_server.services.reports import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"], responses=ERROR_RESPONSES)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ReportResponse)
async def create_report(
    body: CreateReportRequest,
    ctx: AuthContext = Depends(require_user),
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    """File a metadata-correction report against a canonical entity (201, ``pending``)."""
    assert ctx.user_id is not None  # require_user guarantees an identity
    row = await service.submit(
        reporter_id=ctx.user_id,
        subject_type=body.subject_type,
        subject_id=body.subject_id,
        field=body.field,
        proposed_value=body.proposed_value,
        reason=body.reason,
    )
    return ReportResponse.model_validate(row)


@router.get("/me", response_model=list[ReportResponse])
async def list_my_reports(
    ctx: AuthContext = Depends(require_user),
    service: ReportService = Depends(get_report_service),
) -> list[ReportResponse]:
    """List the caller's own reports and their review state (newest first)."""
    assert ctx.user_id is not None  # require_user guarantees an identity
    rows = await service.list_own(ctx.user_id)
    return [ReportResponse.model_validate(row) for row in rows]
