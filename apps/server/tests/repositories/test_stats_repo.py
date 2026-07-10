"""Offline (in-memory SQLite) tests for :class:`StatsRepository` +
:class:`EntityStatRepository`.

``StatsRepository`` is the sole holder of the admin ``SELECT count(*)`` aggregate
SQL that backs ``GET /admin/stats``; those tests pin each count against a real
schema. ``EntityStatRepository`` owns the append-only ``entity_stat`` engagement
time-series (Phase 4): ``record`` never overwrites, and ``latest_per_metric``
collapses the series to the newest value per (provider, metric).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from spotdl_core.model import EntityType, MatchStatus, ProviderId
from spotdl_server.db.enums import ReportStatus, VotableType
from spotdl_server.db.models import EntityStat, Match, Track
from spotdl_server.repositories.reports import ReportRepository
from spotdl_server.repositories.stats import EntityStatRepository, StatsRepository
from spotdl_server.repositories.users import UserRepository
from spotdl_server.repositories.votes import VoteRepository
from sqlalchemy import func, select
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


# --------------------------------------------------------------------------
# EntityStatRepository — engagement time-series
# --------------------------------------------------------------------------


async def _entity_stat_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(EntityStat)) or 0)


async def test_record_appends_a_capture(session: AsyncSession) -> None:
    repo = EntityStatRepository(session)
    entity_id = uuid.uuid4()

    row = await repo.record(
        entity_type=EntityType.ARTIST,
        entity_id=entity_id,
        provider=ProviderId.SPOTIFY,
        metric="followers",
        value=9_000_000,
    )

    assert await _entity_stat_count(session) == 1
    assert row.value == 9_000_000
    assert row.captured_at is not None


async def test_record_is_append_only(session: AsyncSession) -> None:
    repo = EntityStatRepository(session)
    entity_id = uuid.uuid4()
    for value in (100, 200):
        await repo.record(
            entity_type=EntityType.ARTIST,
            entity_id=entity_id,
            provider=ProviderId.SPOTIFY,
            metric="followers",
            value=value,
        )

    # Re-capturing the same (entity, provider, metric) inserts a new row.
    assert await _entity_stat_count(session) == 2
    rows = await repo.list_for_entity(EntityType.ARTIST, entity_id)
    assert {r.value for r in rows} == {100, 200}


async def test_latest_per_metric_collapses_and_scopes(session: AsyncSession) -> None:
    repo = EntityStatRepository(session)
    entity_id = uuid.uuid4()
    base = datetime(2026, 1, 1, tzinfo=UTC)
    # Explicit, distinct timestamps so "newest capture wins" is deterministic.
    for value, offset in ((100, 0), (150, 60)):  # 150 captured later → wins
        await repo.record(
            entity_type=EntityType.ARTIST,
            entity_id=entity_id,
            provider=ProviderId.SPOTIFY,
            metric="followers",
            value=value,
            captured_at=base + timedelta(seconds=offset),
        )
    await repo.record(
        entity_type=EntityType.ARTIST,
        entity_id=entity_id,
        provider=ProviderId.LASTFM,
        metric="listeners",
        value=42,
    )
    # A different entity's rows must not leak into the query.
    await repo.record(
        entity_type=EntityType.ARTIST,
        entity_id=uuid.uuid4(),
        provider=ProviderId.SPOTIFY,
        metric="followers",
        value=999,
    )

    latest = await repo.latest_per_metric(EntityType.ARTIST, entity_id)
    assert [(r.provider, r.metric, r.value) for r in latest] == [
        (ProviderId.LASTFM, "listeners", 42),
        (ProviderId.SPOTIFY, "followers", 150),
    ]
