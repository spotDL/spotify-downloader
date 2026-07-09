"""Offline (in-memory SQLite) tests for :class:`MatchRepository`."""

from __future__ import annotations

import uuid

from spotdl_core.model import AudioCandidate, FeatureVector, Match, MatchStatus, ProviderId
from spotdl_server.db.models import Track
from spotdl_server.repositories.matches import MatchRepository
from sqlalchemy.ext.asyncio import AsyncSession


def _candidate(provider_id: str, *, provider: ProviderId = ProviderId.YTMUSIC) -> AudioCandidate:
    return AudioCandidate(
        provider=provider,
        provider_id=provider_id,
        url=f"https://example.test/{provider_id}",
        name=f"Song {provider_id}",
        artists=("Artist A", "Artist B"),
        duration_ms=211000,
    )


def _features() -> FeatureVector:
    return FeatureVector(
        title_similarity=99.0,
        main_artist_similarity=98.0,
        other_artist_similarity=95.0,
        artist_similarity=97.0,
        album_similarity=90.0,
        duration_delta_s=0.5,
        duration_similarity=99.0,
        isrc_equal=True,
        verified_source=True,
        common_word_overlap=True,
        forbidden_words=(),
        explicit_mismatch=False,
        popularity_prior=0.7,
    )


def _match(provider_id: str, score: float, *, features: bool = True) -> Match:
    return Match(
        candidate=_candidate(provider_id),
        score=score,
        matcher_version="v5.0",
        status=MatchStatus.AUTO,
        features=_features() if features else None,
    )


async def _make_track(session: AsyncSession) -> Track:
    track = Track(name="Test Track", duration_ms=211000)
    session.add(track)
    await session.flush()
    return track


async def test_replace_for_track_inserts_rows(session: AsyncSession) -> None:
    track = await _make_track(session)
    repo = MatchRepository(session)

    rows = await repo.replace_for_track(track.id, [_match("a", 90.0), _match("b", 80.0)], "v5.0")
    assert len(rows) == 2
    by_target = {r.target_id: r for r in rows}
    row = by_target["a"]
    assert row.target_provider == ProviderId.YTMUSIC
    assert row.target_url == "https://example.test/a"
    assert row.score == 90.0
    assert row.matcher_version == "v5.0"
    assert row.status == MatchStatus.AUTO
    assert row.candidate_name == "Song a"
    assert row.candidate_artists == ["Artist A", "Artist B"]
    assert row.candidate_duration_ms == 211000
    assert isinstance(row.features, dict)
    assert row.features["isrc_equal"] is True


async def test_replace_for_track_dedupes_by_target(session: AsyncSession) -> None:
    track = await _make_track(session)
    repo = MatchRepository(session)

    await repo.replace_for_track(track.id, [_match("a", 90.0), _match("b", 80.0)], "v5.0")
    # Re-run: "a" survives with a new score, "b" disappears, "c" is new.
    rows = await repo.replace_for_track(track.id, [_match("a", 70.0), _match("c", 60.0)], "v5.1")

    targets = {r.target_id for r in await repo.list_for_track(track.id)}
    assert targets == {"a", "c"}
    a_row = next(r for r in rows if r.target_id == "a")
    assert a_row.score == 70.0
    assert a_row.matcher_version == "v5.1"


async def test_replace_preserves_community_verified_status_and_tallies(
    session: AsyncSession,
) -> None:
    track = await _make_track(session)
    repo = MatchRepository(session)

    [row_a, _] = await repo.replace_for_track(
        track.id, [_match("a", 90.0), _match("b", 80.0)], "v5.0"
    )
    # Simulate a Plan 6 community vote promoting "a".
    row_a.status = MatchStatus.COMMUNITY_VERIFIED
    row_a.upvotes = 12
    row_a.downvotes = 3
    row_a.net_score = 9
    await session.flush()

    # Re-match with a fresh AUTO list that still contains "a" (lower score) but
    # no longer contains "b".
    await repo.replace_for_track(track.id, [_match("a", 10.0), _match("d", 5.0)], "v5.1")

    preserved = await repo.get(row_a.id)
    assert preserved is not None
    assert preserved.status == MatchStatus.COMMUNITY_VERIFIED
    assert preserved.upvotes == 12
    assert preserved.downvotes == 3
    assert preserved.net_score == 9
    # Non-status fields still refresh from the new match.
    assert preserved.score == 10.0
    assert preserved.matcher_version == "v5.1"


async def test_replace_keeps_community_row_absent_from_new_set(session: AsyncSession) -> None:
    track = await _make_track(session)
    repo = MatchRepository(session)

    [row_a, _] = await repo.replace_for_track(
        track.id, [_match("a", 90.0), _match("b", 80.0)], "v5.0"
    )
    row_a.status = MatchStatus.COMMUNITY_VERIFIED
    row_a.upvotes = 5
    row_a.net_score = 5
    await session.flush()

    # New auto set omits "a" entirely — a community row must survive.
    await repo.replace_for_track(track.id, [_match("z", 50.0)], "v5.1")

    survivor = await repo.get(row_a.id)
    assert survivor is not None
    assert survivor.status == MatchStatus.COMMUNITY_VERIFIED
    targets = {r.target_id for r in await repo.list_for_track(track.id)}
    assert targets == {"a", "z"}


async def test_list_for_track_orders_community_first_then_score(session: AsyncSession) -> None:
    track = await _make_track(session)
    repo = MatchRepository(session)

    rows = await repo.replace_for_track(
        track.id,
        [_match("high", 95.0), _match("mid", 70.0), _match("low", 40.0)],
        "v5.0",
    )
    # Promote the lowest-scoring row to community_verified.
    low = next(r for r in rows if r.target_id == "low")
    low.status = MatchStatus.COMMUNITY_VERIFIED
    await session.flush()

    listed = await repo.list_for_track(track.id)
    assert [r.target_id for r in listed] == ["low", "high", "mid"]


async def test_list_for_track_excludes_rejected(session: AsyncSession) -> None:
    track = await _make_track(session)
    repo = MatchRepository(session)

    rows = await repo.replace_for_track(track.id, [_match("a", 90.0), _match("b", 80.0)], "v5.0")
    rejected = next(r for r in rows if r.target_id == "b")
    rejected.status = MatchStatus.REJECTED
    await session.flush()

    listed = await repo.list_for_track(track.id)
    assert [r.target_id for r in listed] == ["a"]


async def test_replace_for_track_handles_none_features(session: AsyncSession) -> None:
    track = await _make_track(session)
    repo = MatchRepository(session)

    [row] = await repo.replace_for_track(track.id, [_match("a", 90.0, features=False)], "v5.0")
    assert row.features is None


async def test_get_returns_none_when_absent(session: AsyncSession) -> None:
    repo = MatchRepository(session)
    assert await repo.get(uuid.uuid4()) is None
