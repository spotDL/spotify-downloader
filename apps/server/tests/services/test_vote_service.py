"""Offline unit tests for :class:`VoteService` (spec §6.2 — vote CONTRACT).

The vote state machine, the atomic-tally invariant, and the versioned status
policy are the heart of the community layer, so these tests are exhaustive:

* the full 9-cell ``(old, new)`` transition table, asserting both the counter
  deltas and the resulting tallies;
* the never-drift invariant ``net_score == upvotes - downvotes`` after a
  randomized multi-user sequence, cross-checked by re-summing the ledger;
* status transitions (matches ``community_verified``/``rejected``; entity_links
  ``verified``/``disputed``; lyrics never gets a status) driven across the
  policy thresholds and back;
* the policy as config — a custom threshold changes the verification score, and
  the policy JSON-round-trips.

Everything runs against in-memory SQLite through the ``session`` fixture; the
service flushes and the fixture owns the unit of work.
"""

from __future__ import annotations

import random
import uuid

import pytest
from pydantic import ValidationError
from spotdl_core.model import EntityType, LyricsKind, MatchStatus, ProviderId
from spotdl_server.db.enums import LinkStatus, VotableType
from spotdl_server.db.models import EntityLink, Lyrics, Match, ProviderSnapshot, Track, User, Vote
from spotdl_server.policies.voting import VOTE_POLICY_V1, VotePolicy
from spotdl_server.repositories.votes import VoteRepository
from spotdl_server.services.errors import NotFoundError
from spotdl_server.services.voting import VoteService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_user(session: AsyncSession) -> uuid.UUID:
    user = User(email=f"{uuid.uuid4().hex}@example.com", password_hash="h")
    session.add(user)
    await session.flush()
    return user.id


async def _make_match(session: AsyncSession) -> uuid.UUID:
    track = Track(name="Test Track", duration_ms=211000)
    session.add(track)
    await session.flush()
    match = Match(
        track_id=track.id,
        target_provider=ProviderId.YTMUSIC,
        target_id=uuid.uuid4().hex,
        target_url="https://example.test/a",
        score=90.0,
        matcher_version="v5.0",
        status=MatchStatus.AUTO,
    )
    session.add(match)
    await session.flush()
    return match.id


async def _make_lyrics(session: AsyncSession) -> uuid.UUID:
    track = Track(name="Test Track", duration_ms=211000)
    session.add(track)
    await session.flush()
    lyrics = Lyrics(
        track_id=track.id, source=ProviderId.LRCLIB, kind=LyricsKind.PLAIN, text="la la la"
    )
    session.add(lyrics)
    await session.flush()
    return lyrics.id


async def _make_link(session: AsyncSession) -> uuid.UUID:
    snapshot = ProviderSnapshot(
        provider=ProviderId.SPOTIFY,
        provider_entity_id=uuid.uuid4().hex,
        entity_type=EntityType.TRACK,
        raw_payload={},
    )
    session.add(snapshot)
    await session.flush()
    link = EntityLink(
        entity_type=EntityType.TRACK,
        entity_id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        status=LinkStatus.AUTO,
    )
    session.add(link)
    await session.flush()
    return link.id


def _service(session: AsyncSession, policy: VotePolicy = VOTE_POLICY_V1) -> VoteService:
    return VoteService(session=session, votes=VoteRepository(session), policy=policy)


# --------------------------------------------------------------------------
# State machine: the 9-cell (old, new) transition table
# --------------------------------------------------------------------------

# (initial actions to establish `old`, new action, expected (up, down, net), your_vote)
_TRANSITIONS = [
    # old = none
    ([], "up", (1, 0, 1), 1),
    ([], "down", (0, 1, -1), -1),
    ([], "retract", (0, 0, 0), None),
    # old = +1 (up)
    (["up"], "up", (1, 0, 1), 1),  # no-op
    (["up"], "down", (0, 1, -1), -1),
    (["up"], "retract", (0, 0, 0), None),
    # old = -1 (down)
    (["down"], "up", (1, 0, 1), 1),
    (["down"], "down", (0, 1, -1), -1),  # no-op
    (["down"], "retract", (0, 0, 0), None),
]


@pytest.mark.parametrize("setup,action,expected,your_vote", _TRANSITIONS)
async def test_state_machine_transitions(
    session: AsyncSession,
    setup: list[str],
    action: str,
    expected: tuple[int, int, int],
    your_vote: int | None,
) -> None:
    user_id = await _make_user(session)
    match_id = await _make_match(session)
    svc = _service(session)

    for pre in setup:
        await svc.vote(
            user_id=user_id, votable_type=VotableType.MATCH, votable_id=match_id, action=pre
        )

    outcome = await svc.vote(
        user_id=user_id, votable_type=VotableType.MATCH, votable_id=match_id, action=action
    )

    assert (outcome.upvotes, outcome.downvotes, outcome.net_score) == expected
    assert outcome.your_vote == your_vote
    # Cross-check against the DB row directly.
    row = await session.get(Match, match_id)
    assert row is not None
    assert (row.upvotes, row.downvotes, row.net_score) == expected


async def test_double_up_is_noop(session: AsyncSession) -> None:
    user_id = await _make_user(session)
    match_id = await _make_match(session)
    svc = _service(session)
    await svc.vote(
        user_id=user_id, votable_type=VotableType.MATCH, votable_id=match_id, action="up"
    )
    out = await svc.vote(
        user_id=user_id, votable_type=VotableType.MATCH, votable_id=match_id, action="up"
    )
    assert (out.upvotes, out.downvotes, out.net_score) == (1, 0, 1)
    assert out.your_vote == 1


async def test_change_up_to_down(session: AsyncSession) -> None:
    user_id = await _make_user(session)
    match_id = await _make_match(session)
    svc = _service(session)
    await svc.vote(
        user_id=user_id, votable_type=VotableType.MATCH, votable_id=match_id, action="up"
    )
    out = await svc.vote(
        user_id=user_id, votable_type=VotableType.MATCH, votable_id=match_id, action="down"
    )
    assert (out.upvotes, out.downvotes, out.net_score) == (0, 1, -1)


async def test_retract_removes_row_and_decrements(session: AsyncSession) -> None:
    user_id = await _make_user(session)
    match_id = await _make_match(session)
    svc = _service(session)
    await svc.vote(
        user_id=user_id, votable_type=VotableType.MATCH, votable_id=match_id, action="up"
    )

    out = await svc.vote(
        user_id=user_id, votable_type=VotableType.MATCH, votable_id=match_id, action="retract"
    )

    assert (out.upvotes, out.downvotes, out.net_score) == (0, 0, 0)
    assert out.your_vote is None
    rows = (await session.execute(select(Vote).where(Vote.votable_id == match_id))).scalars().all()
    assert rows == []  # the ledger row is deleted, not kept as zero


async def test_retract_with_no_vote_is_noop(session: AsyncSession) -> None:
    user_id = await _make_user(session)
    match_id = await _make_match(session)
    svc = _service(session)
    out = await svc.vote(
        user_id=user_id, votable_type=VotableType.MATCH, votable_id=match_id, action="retract"
    )
    assert (out.upvotes, out.downvotes, out.net_score) == (0, 0, 0)
    assert out.your_vote is None


async def test_missing_votable_raises_not_found(session: AsyncSession) -> None:
    user_id = await _make_user(session)
    svc = _service(session)
    with pytest.raises(NotFoundError):
        await svc.vote(
            user_id=user_id,
            votable_type=VotableType.MATCH,
            votable_id=uuid.uuid4(),
            action="up",
        )


# --------------------------------------------------------------------------
# Atomicity / never-drift invariant
# --------------------------------------------------------------------------


async def test_net_score_equals_up_minus_down_after_random_sequence(
    session: AsyncSession,
) -> None:
    match_id = await _make_match(session)
    svc = _service(session)
    users = [await _make_user(session) for _ in range(6)]
    rng = random.Random(1234)

    for _ in range(200):
        user = rng.choice(users)
        action = rng.choice(["up", "down", "retract"])
        await svc.vote(
            user_id=user, votable_type=VotableType.MATCH, votable_id=match_id, action=action
        )

    row = await session.get(Match, match_id)
    assert row is not None
    # Invariant 1: net_score is exactly up - down.
    assert row.net_score == row.upvotes - row.downvotes
    # Invariant 2: the counters equal a fresh re-tally of the ledger (no drift).
    ledger_up = await session.scalar(
        select(func.count()).select_from(Vote).where(Vote.votable_id == match_id, Vote.value == 1)
    )
    ledger_down = await session.scalar(
        select(func.count()).select_from(Vote).where(Vote.votable_id == match_id, Vote.value == -1)
    )
    assert (row.upvotes, row.downvotes) == (ledger_up, ledger_down)
    assert row.net_score == (ledger_up or 0) - (ledger_down or 0)


# --------------------------------------------------------------------------
# Status transitions (matches / entity_links); lyrics never gets a status
# --------------------------------------------------------------------------


async def _drive_net(
    session: AsyncSession,
    svc: VoteService,
    votable_type: VotableType,
    votable_id: uuid.UUID,
    users: list[uuid.UUID],
    *,
    up: int = 0,
    down: int = 0,
) -> None:
    """Cast ``up`` upvotes and ``down`` downvotes from distinct fresh users."""
    for _ in range(up):
        users.append(await _make_user(session))
        await svc.vote(
            user_id=users[-1], votable_type=votable_type, votable_id=votable_id, action="up"
        )
    for _ in range(down):
        users.append(await _make_user(session))
        await svc.vote(
            user_id=users[-1], votable_type=votable_type, votable_id=votable_id, action="down"
        )


async def test_match_status_transitions_across_thresholds(session: AsyncSession) -> None:
    match_id = await _make_match(session)
    svc = _service(session)  # default policy: verify>=5, reject<=-5, min_votes=3
    users: list[uuid.UUID] = []

    # 5 upvotes: net=5, total=5 >= 3 -> community_verified.
    await _drive_net(session, svc, VotableType.MATCH, match_id, users, up=5)
    row = await session.get(Match, match_id)
    assert row is not None and row.status is MatchStatus.COMMUNITY_VERIFIED

    # Add 4 downvotes: net=1 (<5, >-5) -> back to auto.
    await _drive_net(session, svc, VotableType.MATCH, match_id, users, down=4)
    row = await session.get(Match, match_id)
    assert row is not None and row.status is MatchStatus.AUTO

    # 8 more downvotes: net = 5 - 12 = -7 <= -5 -> rejected.
    await _drive_net(session, svc, VotableType.MATCH, match_id, users, down=8)
    row = await session.get(Match, match_id)
    assert row is not None and row.status is MatchStatus.REJECTED


async def test_min_votes_gate_blocks_early_transition(session: AsyncSession) -> None:
    match_id = await _make_match(session)
    svc = _service(session)
    users: list[uuid.UUID] = []
    # 2 upvotes only: net=2 but total=2 < min_votes_for_status(3) -> stays auto.
    await _drive_net(session, svc, VotableType.MATCH, match_id, users, up=2)
    row = await session.get(Match, match_id)
    assert row is not None and row.status is MatchStatus.AUTO


async def test_entity_link_status_transitions(session: AsyncSession) -> None:
    link_id = await _make_link(session)
    svc = _service(session)
    users: list[uuid.UUID] = []

    await _drive_net(session, svc, VotableType.ENTITY_LINK, link_id, users, up=5)
    row = await session.get(EntityLink, link_id)
    assert row is not None and row.status is LinkStatus.VERIFIED

    await _drive_net(session, svc, VotableType.ENTITY_LINK, link_id, users, down=11)
    row = await session.get(EntityLink, link_id)
    assert row is not None and row.status is LinkStatus.DISPUTED


async def test_lyrics_never_gets_a_status(session: AsyncSession) -> None:
    lyrics_id = await _make_lyrics(session)
    svc = _service(session)
    users: list[uuid.UUID] = []
    await _drive_net(session, svc, VotableType.LYRICS, lyrics_id, users, up=5)
    out = await svc.vote(
        user_id=await _make_user(session),
        votable_type=VotableType.LYRICS,
        votable_id=lyrics_id,
        action="up",
    )
    assert out.status is None
    row = await session.get(Lyrics, lyrics_id)
    assert row is not None
    assert (row.upvotes, row.net_score) == (6, 6)


# --------------------------------------------------------------------------
# Policy as config
# --------------------------------------------------------------------------


async def test_custom_policy_changes_threshold(session: AsyncSession) -> None:
    match_id = await _make_match(session)
    # Verify at net>=2 with min 3 votes: 3 upvotes -> net=3 -> verified early.
    svc = _service(session, VotePolicy(match_verify_net_score=2))
    users: list[uuid.UUID] = []
    await _drive_net(session, svc, VotableType.MATCH, match_id, users, up=3)
    row = await session.get(Match, match_id)
    assert row is not None and row.status is MatchStatus.COMMUNITY_VERIFIED


def test_policy_json_roundtrip() -> None:
    policy = VotePolicy(match_verify_net_score=7, policy_version="vote-test")
    restored = VotePolicy.model_validate_json(policy.model_dump_json())
    assert restored == policy
    assert restored.match_verify_net_score == 7
    assert restored.policy_version == "vote-test"


def test_policy_is_frozen() -> None:
    with pytest.raises(ValidationError):
        VOTE_POLICY_V1.match_verify_net_score = 99  # type: ignore[misc]
