"""Offline (in-memory SQLite) tests for :class:`ReportRepository`.

The repository is the sole holder of the ``reports`` table's query code: it
creates a ``pending`` correction report, fetches it by id, lists a reporter's own
reports and the admin review queue by status (with paging), and stamps an
admin decision (status + ``reviewed_by`` / ``reviewed_at`` / ``review_note``).
These tests pin each of those behaviours against a real schema so the atomic
decision write and the paged status query are exercised end to end.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from spotdl_core.model import EntityType
from spotdl_server.db.enums import ReportStatus
from spotdl_server.repositories.reports import ReportRepository
from spotdl_server.repositories.users import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_user(session: AsyncSession) -> uuid.UUID:
    user = await UserRepository(session).create(
        email=f"{uuid.uuid4().hex}@example.com", password_hash="h"
    )
    return user.id


async def test_create_makes_a_pending_report(session: AsyncSession) -> None:
    reporter_id = await _make_user(session)
    repo = ReportRepository(session)

    report = await repo.create(
        reporter_id=reporter_id,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        field="name",
        proposed_value="Corrected Title",
        reason="the title has a typo",
    )

    assert report.id is not None
    assert report.reporter_id == reporter_id
    assert report.subject_type is EntityType.TRACK
    assert report.status is ReportStatus.PENDING
    assert report.reviewed_by is None
    assert report.reviewed_at is None
    assert report.review_note is None


async def test_get_returns_the_report_or_none(session: AsyncSession) -> None:
    reporter_id = await _make_user(session)
    repo = ReportRepository(session)
    created = await repo.create(
        reporter_id=reporter_id,
        subject_type=EntityType.ALBUM,
        subject_id=uuid.uuid4(),
        field=None,
        proposed_value=None,
        reason="wrong cover",
    )

    assert (await repo.get(created.id)).id == created.id
    assert await repo.get(uuid.uuid4()) is None


async def test_list_by_reporter_returns_only_that_reporter(session: AsyncSession) -> None:
    alice = await _make_user(session)
    bob = await _make_user(session)
    repo = ReportRepository(session)
    await repo.create(
        reporter_id=alice,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        field=None,
        proposed_value=None,
        reason="a",
    )
    await repo.create(
        reporter_id=bob,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        field=None,
        proposed_value=None,
        reason="b",
    )

    alice_reports = await repo.list_by_reporter(alice)
    assert len(alice_reports) == 1
    assert alice_reports[0].reporter_id == alice


async def test_list_by_status_pages_and_counts(session: AsyncSession) -> None:
    reporter_id = await _make_user(session)
    repo = ReportRepository(session)
    for i in range(3):
        await repo.create(
            reporter_id=reporter_id,
            subject_type=EntityType.TRACK,
            subject_id=uuid.uuid4(),
            field=None,
            proposed_value=None,
            reason=f"r{i}",
        )

    rows, total = await repo.list_by_status(ReportStatus.PENDING, limit=2, offset=0)
    assert total == 3
    assert len(rows) == 2

    rows2, total2 = await repo.list_by_status(ReportStatus.PENDING, limit=2, offset=2)
    assert total2 == 3
    assert len(rows2) == 1

    approved, approved_total = await repo.list_by_status(ReportStatus.APPROVED, limit=10, offset=0)
    assert approved_total == 0
    assert approved == []


async def test_set_decision_stamps_status_reviewer_and_note(session: AsyncSession) -> None:
    reporter_id = await _make_user(session)
    admin_id = await _make_user(session)
    repo = ReportRepository(session)
    report = await repo.create(
        reporter_id=reporter_id,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        field="isrc",
        proposed_value="USABC1234567",
        reason="wrong isrc",
    )
    now = datetime(2026, 3, 1, tzinfo=UTC)

    await repo.set_decision(
        report,
        status=ReportStatus.APPROVED,
        reviewed_by=admin_id,
        note="applied",
        now=now,
    )

    assert report.status is ReportStatus.APPROVED
    assert report.reviewed_by == admin_id
    assert report.reviewed_at == now
    assert report.review_note == "applied"

    # It now leaves the pending queue and shows up under its new status.
    pending, pending_total = await repo.list_by_status(ReportStatus.PENDING, limit=10, offset=0)
    assert pending_total == 0
    approved, approved_total = await repo.list_by_status(ReportStatus.APPROVED, limit=10, offset=0)
    assert approved_total == 1
    assert approved[0].id == report.id
