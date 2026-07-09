"""Offline unit tests for :class:`ReportService` (spec §6.2 reports).

The service creates a ``pending`` metadata-correction report and lists a
reporter's own reports; it does **not** hard-verify the subject entity exists in
v1 (admin triage judges validity), so a report may target any well-formed
``(subject_type, subject_id)``. Time flows through the ``FakeClock`` so any
timestamps are deterministic; the service flushes (never commits) and the
in-memory ``session`` fixture owns the unit of work.
"""

from __future__ import annotations

import uuid

from spotdl_core.model import EntityType
from spotdl_server.db.enums import ReportStatus
from spotdl_server.repositories.reports import ReportRepository
from spotdl_server.repositories.users import UserRepository
from spotdl_server.services.reports import ReportService
from sqlalchemy.ext.asyncio import AsyncSession

from apps.server.tests.conftest import FakeClock


async def _make_user(session: AsyncSession) -> uuid.UUID:
    user = await UserRepository(session).create(
        email=f"{uuid.uuid4().hex}@example.com", password_hash="h"
    )
    return user.id


def _service(session: AsyncSession, clock: FakeClock) -> ReportService:
    return ReportService(session=session, clock=clock, reports=ReportRepository(session))


async def test_submit_creates_a_pending_report(session: AsyncSession, clock: FakeClock) -> None:
    reporter_id = await _make_user(session)
    svc = _service(session, clock)

    report = await svc.submit(
        reporter_id=reporter_id,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        field="name",
        proposed_value="Better Title",
        reason="typo",
    )

    assert report.status is ReportStatus.PENDING
    assert report.reporter_id == reporter_id
    assert report.subject_type is EntityType.TRACK
    assert report.field == "name"
    assert report.proposed_value == "Better Title"


async def test_submit_does_not_verify_subject_exists(
    session: AsyncSession, clock: FakeClock
) -> None:
    # A report may target an id that is not in our DB — admin triage judges it.
    reporter_id = await _make_user(session)
    svc = _service(session, clock)

    report = await svc.submit(
        reporter_id=reporter_id,
        subject_type=EntityType.ARTIST,
        subject_id=uuid.uuid4(),
        field=None,
        proposed_value=None,
        reason=None,
    )

    assert report.status is ReportStatus.PENDING


async def test_list_own_returns_only_the_callers_reports(
    session: AsyncSession, clock: FakeClock
) -> None:
    alice = await _make_user(session)
    bob = await _make_user(session)
    svc = _service(session, clock)
    await svc.submit(
        reporter_id=alice,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        field=None,
        proposed_value=None,
        reason="a",
    )
    await svc.submit(
        reporter_id=bob,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        field=None,
        proposed_value=None,
        reason="b",
    )

    own = await svc.list_own(alice)
    assert len(own) == 1
    assert own[0].reporter_id == alice
