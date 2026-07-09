"""``/api/v1/admin`` — the minimal admin surface (spec §6.2 "Admin (minimal)").

A thin HTTP shell over :class:`~spotdl_server.services.admin.AdminService`. **Every**
route depends on ``require_admin``, which re-loads the caller's row so a demoted or
disabled admin holding a still-valid ≤15-min access token is rejected (403). No
business logic and no ORM import (the ``User`` / ``Report`` rows are serialized by
``model_validate`` without naming the ORM type).

Approve and reject are two explicit verbs (not a mutable ``PATCH``) so the review
queue reads as an append-only audit log. The decision **records a review state
only** — v1 does not auto-apply an approved correction to canonical data (the
service documents this non-goal). This router is mounted only when
``settings.auth_active()`` (never in EMBEDDED mode).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from spotdl_server.api.deps import get_admin_service, require_admin
from spotdl_server.api.routers import ERROR_RESPONSES
from spotdl_server.api.schemas import (
    AdminReviewRequest,
    AdminStatsResponse,
    AdminUserResponse,
    PagedReports,
    PagedUsers,
    ReportResponse,
)
from spotdl_server.auth.context import AuthContext
from spotdl_server.db.enums import ReportStatus
from spotdl_server.services.admin import AdminService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], responses=ERROR_RESPONSES)


@router.get("/users", response_model=PagedUsers)
async def list_users(
    limit: int = Query(50, ge=1, le=200, description="Maximum users to return."),
    offset: int = Query(0, ge=0, description="Rows to skip (pagination)."),
    _ctx: AuthContext = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> PagedUsers:
    """List users, newest first, with the full ``total`` count for pagination."""
    users, total = await service.list_users(limit=limit, offset=offset)
    return PagedUsers(items=[AdminUserResponse.model_validate(u) for u in users], total=total)


@router.get("/reports", response_model=PagedReports)
async def reports_queue(
    status: ReportStatus = Query(
        ReportStatus.PENDING, description="Review state to filter the queue by."
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum reports to return."),
    offset: int = Query(0, ge=0, description="Rows to skip (pagination)."),
    _ctx: AuthContext = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> PagedReports:
    """The report queue filtered by ``status`` (default ``pending``, oldest first)."""
    reports, total = await service.reports_queue(status=status, limit=limit, offset=offset)
    return PagedReports(items=[ReportResponse.model_validate(r) for r in reports], total=total)


@router.post("/reports/{report_id}/approve", response_model=ReportResponse)
async def approve_report(
    report_id: UUID,
    body: AdminReviewRequest,
    ctx: AuthContext = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> ReportResponse:
    """Approve a report (records the review state; 404 if the report is unknown)."""
    assert ctx.user_id is not None  # require_admin guarantees an identity
    row = await service.decide_report(
        report_id=report_id, reviewer_id=ctx.user_id, approve=True, note=body.note
    )
    return ReportResponse.model_validate(row)


@router.post("/reports/{report_id}/reject", response_model=ReportResponse)
async def reject_report(
    report_id: UUID,
    body: AdminReviewRequest,
    ctx: AuthContext = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> ReportResponse:
    """Reject a report (records the review state; 404 if the report is unknown)."""
    assert ctx.user_id is not None  # require_admin guarantees an identity
    row = await service.decide_report(
        report_id=report_id, reviewer_id=ctx.user_id, approve=False, note=body.note
    )
    return ReportResponse.model_validate(row)


@router.get("/stats", response_model=AdminStatsResponse)
async def stats(
    _ctx: AuthContext = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminStatsResponse:
    """Aggregate community-health counts for the admin dashboard."""
    return AdminStatsResponse.model_validate(await service.stats())
