"""Offline unit tests for :class:`AdminService` (spec §6.2 minimal admin).

The service backs the minimal admin surface: a paged user list, a status-filtered
report queue, an audited approve/reject decision, and aggregate stats. It records
a review state only — v1 does **not** auto-apply an approved correction to
canonical data (spec §1 non-goal). Time flows through the ``FakeClock`` so the
``reviewed_at`` stamp is deterministic; the service flushes (never commits) and the
in-memory ``session`` fixture owns the unit of work.
"""

from __future__ import annotations

import uuid

import pytest
from spotdl_core.model import EntityType, MatchStatus, ProviderId
from spotdl_server.db.enums import ReportStatus, VotableType
from spotdl_server.db.models import Match, Track
from spotdl_server.repositories.reports import ReportRepository
from spotdl_server.repositories.users import UserRepository
from spotdl_server.repositories.votes import VoteRepository
from spotdl_server.services.admin import AdminService, AdminStats
from spotdl_server.services.errors import NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.server.tests.conftest import FakeClock


def _service(session: AsyncSession, clock: FakeClock) -> AdminService:
    return AdminService(
        session=session,
        clock=clock,
        users=UserRepository(session),
        reports=ReportRepository(session),
    )


async def _make_user(session: AsyncSession, *, is_admin: bool = False) -> uuid.UUID:
    user = await UserRepository(session).create(
        email=f"{uuid.uuid4().hex}@example.com", password_hash="h", is_admin=is_admin
    )
    return user.id


async def _make_track(session: AsyncSession) -> uuid.UUID:
    track = Track(name="A Song", duration_ms=180_000)
    session.add(track)
    await session.flush()
    return track.id


async def _make_match(session: AsyncSession, track_id: uuid.UUID, status: MatchStatus) -> uuid.UUID:
    match = Match(
        track_id=track_id,
        target_provider=ProviderId.YOUTUBE,
        target_id=uuid.uuid4().hex,
        target_url=f"https://youtube.com/watch?v={uuid.uuid4().hex}",
        score=0.9,
        matcher_version="v5",
        status=status,
    )
    session.add(match)
    await session.flush()
    return match.id


async def _make_report(
    session: AsyncSession, reporter_id: uuid.UUID, *, reason: str = "typo"
) -> uuid.UUID:
    report = await ReportRepository(session).create(
        reporter_id=reporter_id,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        field=None,
        proposed_value=None,
        reason=reason,
    )
    return report.id


async def test_list_users_pages_and_counts(session: AsyncSession, clock: FakeClock) -> None:
    for _ in range(5):
        await _make_user(session)
    svc = _service(session, clock)

    page, total = await svc.list_users(limit=2, offset=0)
    assert total == 5
    assert len(page) == 2

    page2, total2 = await svc.list_users(limit=2, offset=4)
    assert total2 == 5
    assert len(page2) == 1


async def test_reports_queue_filters_by_status(session: AsyncSession, clock: FakeClock) -> None:
    reporter = await _make_user(session)
    admin = await _make_user(session, is_admin=True)
    svc = _service(session, clock)
    r1 = await _make_report(session, reporter, reason="a")
    await _make_report(session, reporter, reason="b")

    pending, pending_total = await svc.reports_queue(limit=10, offset=0)
    assert pending_total == 2
    assert len(pending) == 2

    # Approve one → it leaves the pending queue and appears under APPROVED.
    await svc.decide_report(report_id=r1, reviewer_id=admin, approve=True, note=None)

    pending2, pending_total2 = await svc.reports_queue(limit=10, offset=0)
    assert pending_total2 == 1

    approved, approved_total = await svc.reports_queue(
        status=ReportStatus.APPROVED, limit=10, offset=0
    )
    assert approved_total == 1
    assert approved[0].id == r1


async def test_decide_report_approve_stamps_decision(
    session: AsyncSession, clock: FakeClock
) -> None:
    reporter = await _make_user(session)
    admin = await _make_user(session, is_admin=True)
    svc = _service(session, clock)
    report_id = await _make_report(session, reporter)

    report = await svc.decide_report(
        report_id=report_id, reviewer_id=admin, approve=True, note="looks right"
    )

    assert report.status is ReportStatus.APPROVED
    assert report.reviewed_by == admin
    assert report.review_note == "looks right"
    assert report.reviewed_at == clock.now()


async def test_decide_report_reject_stamps_decision(
    session: AsyncSession, clock: FakeClock
) -> None:
    reporter = await _make_user(session)
    admin = await _make_user(session, is_admin=True)
    svc = _service(session, clock)
    report_id = await _make_report(session, reporter)

    report = await svc.decide_report(
        report_id=report_id, reviewer_id=admin, approve=False, note="bogus"
    )

    assert report.status is ReportStatus.REJECTED
    assert report.reviewed_by == admin
    assert report.review_note == "bogus"


async def test_decide_report_missing_raises_not_found(
    session: AsyncSession, clock: FakeClock
) -> None:
    admin = await _make_user(session, is_admin=True)
    svc = _service(session, clock)
    with pytest.raises(NotFoundError):
        await svc.decide_report(report_id=uuid.uuid4(), reviewer_id=admin, approve=True, note=None)


async def test_stats_counts_are_correct(session: AsyncSession, clock: FakeClock) -> None:
    # Two users; three matches (1 verified, 1 rejected, 1 auto); one vote; two
    # reports (one later approved so reports_pending < reports_total).
    u1 = await _make_user(session)
    admin = await _make_user(session, is_admin=True)
    track = await _make_track(session)
    verified = await _make_match(session, track, MatchStatus.COMMUNITY_VERIFIED)
    await _make_match(session, track, MatchStatus.REJECTED)
    await _make_match(session, track, MatchStatus.AUTO)
    await VoteRepository(session).upsert_value(
        user_id=u1, votable_type=VotableType.MATCH, votable_id=verified, value=1
    )
    r1 = await _make_report(session, u1)
    await _make_report(session, u1)

    svc = _service(session, clock)
    await svc.decide_report(report_id=r1, reviewer_id=admin, approve=True, note=None)

    stats = await svc.stats()
    assert isinstance(stats, AdminStats)
    assert stats.users_total == 2
    assert stats.matches_total == 3
    assert stats.community_verified_matches == 1
    assert stats.rejected_matches == 1
    assert stats.votes_total == 1
    assert stats.reports_total == 2
    assert stats.reports_pending == 1
