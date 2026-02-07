"""Metadata reports API endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from spotdl.api.v1.auth import get_current_user
from spotdl.api.v1.validation import validate_uuid
from spotdl.core.reputation import ReputationReward
from spotdl.db.database import get_db_session
from spotdl.db.models.metadata_report import (
    MetadataReport,
    MetadataReportEntityType,
    ReportStatus,
)
from spotdl.db.models.user import User
from spotdl.db.repositories.user import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports")


# Request/Response models
class CreateReportRequest(BaseModel):
    """Request to create a metadata report."""

    entity_type: MetadataReportEntityType
    entity_id: str
    field_name: str = Field(..., max_length=100)
    current_value: str
    suggested_value: str
    description: str | None = None


class ReportResponse(BaseModel):
    """Response model for a metadata report."""

    id: str
    entity_type: str
    entity_id: str
    field_name: str
    current_value: str
    suggested_value: str
    description: str | None
    status: str
    reporter_id: str
    reporter_username: str | None
    reviewer_id: str | None
    reviewed_by_username: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    """Response model for a list of reports."""

    reports: list[ReportResponse]
    total: int
    page: int
    page_size: int


class UpdateReportRequest(BaseModel):
    """Request to update a report status (admin only)."""

    status: ReportStatus


# User endpoints
@router.post("", response_model=ReportResponse)
async def create_report(
    request: CreateReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    """
    Submit a metadata correction report.

    Requires authentication.
    """
    # Validate entity ID
    entity_uuid = validate_uuid(request.entity_id, "entity ID")

    # Create report
    report = MetadataReport(
        entity_type=request.entity_type.value,
        entity_id=entity_uuid,
        reporter_id=current_user.id,
        field_name=request.field_name,
        current_value=request.current_value,
        suggested_value=request.suggested_value,
        description=request.description,
        status=ReportStatus.PENDING,
    )

    db.add(report)

    # Award reputation for submitting a report
    user_repo = UserRepository(db)
    await user_repo.update_reputation(current_user.id, ReputationReward.REPORT_SUBMITTED)

    await db.commit()
    await db.refresh(report)

    logger.info(
        "User %s submitted report for %s:%s field %s",
        current_user.username,
        request.entity_type.value,
        request.entity_id,
        request.field_name,
    )

    return _report_to_response(report)


@router.get("/me", response_model=ReportListResponse)
async def get_my_reports(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[ReportStatus | None, Query()] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReportListResponse:
    """
    Get reports submitted by the current user.
    """
    # Build query
    query = select(MetadataReport).where(MetadataReport.reporter_id == current_user.id)

    if status:
        query = query.where(MetadataReport.status == status.value)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get page
    query = query.order_by(MetadataReport.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    reports = result.scalars().all()

    return ReportListResponse(
        reports=[_report_to_response(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
    )


# Admin endpoints
@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[ReportStatus | None, Query()] = None,
    entity_type: Annotated[MetadataReportEntityType | None, Query()] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReportListResponse:
    """
    List all metadata reports (admin only).
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Build query with eager loading for usernames
    query = select(MetadataReport).options(
        selectinload(MetadataReport.reporter),
        selectinload(MetadataReport.reviewer),
    )

    if status:
        query = query.where(MetadataReport.status == status.value)
    if entity_type:
        query = query.where(MetadataReport.entity_type == entity_type.value)

    # Count total
    count_subquery = select(MetadataReport)
    if status:
        count_subquery = count_subquery.where(MetadataReport.status == status.value)
    if entity_type:
        count_subquery = count_subquery.where(MetadataReport.entity_type == entity_type.value)

    count_query = select(func.count()).select_from(count_subquery.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get page
    query = query.order_by(MetadataReport.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    reports = result.scalars().all()

    return ReportListResponse(
        reports=[_report_to_response(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    """
    Get a specific report.

    Users can view their own reports; admins can view all.
    """
    report_uuid = validate_uuid(report_id, "report ID")

    result = await db.execute(
        select(MetadataReport).where(MetadataReport.id == report_uuid)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Check access
    if not current_user.is_admin and report.reporter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _report_to_response(report)


@router.patch("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: str,
    request: UpdateReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    """
    Update report status (admin only).

    Use this to mark reports as fixed, dismissed, or reviewed.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    report_uuid = validate_uuid(report_id, "report ID")

    result = await db.execute(
        select(MetadataReport).where(MetadataReport.id == report_uuid)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Track previous status for reputation calculation
    previous_status = report.status

    # Update status
    report.status = request.status.value
    report.reviewed_by = current_user.id
    report.reviewed_at = datetime.now(timezone.utc)

    # Award/deduct reputation to the reporter (only if transitioning from pending)
    if previous_status == ReportStatus.PENDING.value:
        user_repo = UserRepository(db)
        if request.status == ReportStatus.FIXED:
            await user_repo.update_reputation(
                report.reporter_id, ReputationReward.REPORT_FIXED
            )
        elif request.status == ReportStatus.REVIEWED:
            await user_repo.update_reputation(
                report.reporter_id, ReputationReward.REPORT_REVIEWED
            )
        elif request.status == ReportStatus.DISMISSED:
            await user_repo.update_reputation(
                report.reporter_id, ReputationReward.REPORT_DISMISSED
            )

    await db.commit()
    await db.refresh(report)

    logger.info(
        "Admin %s updated report %s to status %s",
        current_user.username,
        report_id,
        request.status.value,
    )

    return _report_to_response(report)


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Delete a report (admin only).
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    report_uuid = validate_uuid(report_id, "report ID")

    result = await db.execute(
        select(MetadataReport).where(MetadataReport.id == report_uuid)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    await db.delete(report)
    await db.commit()

    logger.info("Admin %s deleted report %s", current_user.username, report_id)

    return {"message": "Report deleted", "id": report_id}


def _report_to_response(report: MetadataReport) -> ReportResponse:
    """Convert a MetadataReport model to ReportResponse."""
    # Get usernames from relationships if loaded
    reporter_username = None
    reviewed_by_username = None

    if hasattr(report, "reporter") and report.reporter:
        reporter_username = report.reporter.username
    if hasattr(report, "reviewer") and report.reviewer:
        reviewed_by_username = report.reviewer.username

    return ReportResponse(
        id=str(report.id),
        entity_type=report.entity_type,
        entity_id=str(report.entity_id),
        field_name=report.field_name,
        current_value=report.current_value,
        suggested_value=report.suggested_value,
        description=report.description,
        status=report.status,
        reporter_id=str(report.reporter_id),
        reporter_username=reporter_username,
        reviewer_id=str(report.reviewed_by) if report.reviewed_by else None,
        reviewed_by_username=reviewed_by_username,
        reviewed_at=report.reviewed_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )
