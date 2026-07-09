"""Offline (in-memory SQLite) tests for :class:`StatsRepository`.

The repository is the sole holder of the admin ``SELECT count(*)`` aggregate SQL
that backs ``GET /admin/stats``. These tests pin each count (users, matches total
+ per-status, votes, reports total + per-status) against a real schema.
"""

from __future__ import annotations

import uuid

from spotdl_core.model import EntityType, MatchStatus, ProviderId
from spotdl_server.db.enums import ReportStatus, VotableType
from spotdl_server.db.models import Match, Track
from spotdl_server.repositories.reports import ReportRepository
from spotdl_server.repositories.stats import StatsRepository
from spotdl_server.repositories.users import UserRepository
from spotdl_server.repositories.votes import VoteRepository
from sqlalchemy.ext.asyncio import AsyncSession


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


async def test_counts_on_empty_db_are_zero(session: AsyncSession) -> None:
    repo = StatsRepository(session)
    assert await repo.count_users() == 0
    assert await repo.count_matches() == 0
    assert await repo.count_matches_in_status(MatchStatus.COMMUNITY_VERIFIED) == 0
    assert await repo.count_votes() == 0
    assert await repo.count_reports() == 0
    assert await repo.count_reports_in_status(ReportStatus.PENDING) == 0


async def test_counts_reflect_seeded_rows(session: AsyncSession) -> None:
    users = UserRepository(session)
    u1 = await users.create(email="a@example.com", password_hash="h")
    await users.create(email="b@example.com", password_hash="h")

    track = Track(name="Song", duration_ms=1000)
    session.add(track)
    await session.flush()
    verified = await _make_match(session, track.id, MatchStatus.COMMUNITY_VERIFIED)
    await _make_match(session, track.id, MatchStatus.REJECTED)
    await _make_match(session, track.id, MatchStatus.AUTO)

    await VoteRepository(session).upsert_value(
        user_id=u1.id, votable_type=VotableType.MATCH, votable_id=verified, value=1
    )

    reports = ReportRepository(session)
    await reports.create(
        reporter_id=u1.id,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        field=None,
        proposed_value=None,
        reason="a",
    )
    await reports.create(
        reporter_id=u1.id,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        field=None,
        proposed_value=None,
        reason="b",
    )

    repo = StatsRepository(session)
    assert await repo.count_users() == 2
    assert await repo.count_matches() == 3
    assert await repo.count_matches_in_status(MatchStatus.COMMUNITY_VERIFIED) == 1
    assert await repo.count_matches_in_status(MatchStatus.REJECTED) == 1
    assert await repo.count_votes() == 1
    assert await repo.count_reports() == 2
    assert await repo.count_reports_in_status(ReportStatus.PENDING) == 2
    assert await repo.count_reports_in_status(ReportStatus.APPROVED) == 0
