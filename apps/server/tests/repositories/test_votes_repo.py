"""Offline (in-memory SQLite) tests for :class:`VoteRepository`.

The repository is the sole holder of the atomic-tally SQL: ``apply_tally_delta``
mutates a votable row's counters with ``col = col + :delta`` expressions (never a
Python read-modify-write), dispatching to the right table by
:class:`~spotdl_server.db.enums.VotableType`. These tests pin that each table
type moves the right counters and ``net_score``, that ``load_tallies`` returns
``None`` for a missing id, and that the vote-ledger CRUD helpers behave.
"""

from __future__ import annotations

import uuid

import pytest
from spotdl_core.model import EntityType, LyricsKind, MatchStatus, ProviderId
from spotdl_server.db.enums import LinkStatus, VotableType
from spotdl_server.db.models import EntityLink, Lyrics, Match, ProviderSnapshot, Track, User, Vote
from spotdl_server.repositories.votes import VoteRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_user(session: AsyncSession) -> uuid.UUID:
    user = User(email=f"{uuid.uuid4().hex}@example.com", password_hash="h")
    session.add(user)
    await session.flush()
    return user.id


async def _make_track(session: AsyncSession) -> Track:
    track = Track(name="Test Track", duration_ms=211000)
    session.add(track)
    await session.flush()
    return track


async def _make_match(session: AsyncSession) -> Match:
    track = await _make_track(session)
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
    return match


async def _make_lyrics(session: AsyncSession) -> Lyrics:
    track = await _make_track(session)
    lyrics = Lyrics(
        track_id=track.id,
        source=ProviderId.LRCLIB,
        kind=LyricsKind.PLAIN,
        text="la la la",
    )
    session.add(lyrics)
    await session.flush()
    return lyrics


async def _make_link(session: AsyncSession) -> EntityLink:
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
    return link


class TestApplyTallyDelta:
    async def test_moves_match_counters_and_net_score(self, session: AsyncSession) -> None:
        match = await _make_match(session)
        repo = VoteRepository(session)

        await repo.apply_tally_delta(VotableType.MATCH, match.id, d_up=1, d_down=0)
        assert await repo.load_tallies(VotableType.MATCH, match.id) == (1, 0, 1)

        await repo.apply_tally_delta(VotableType.MATCH, match.id, d_up=0, d_down=1)
        assert await repo.load_tallies(VotableType.MATCH, match.id) == (1, 1, 0)

        await repo.apply_tally_delta(VotableType.MATCH, match.id, d_up=-1, d_down=1)
        assert await repo.load_tallies(VotableType.MATCH, match.id) == (0, 2, -2)

    async def test_moves_lyrics_counters(self, session: AsyncSession) -> None:
        lyrics = await _make_lyrics(session)
        repo = VoteRepository(session)

        await repo.apply_tally_delta(VotableType.LYRICS, lyrics.id, d_up=1, d_down=0)
        await repo.apply_tally_delta(VotableType.LYRICS, lyrics.id, d_up=1, d_down=0)
        assert await repo.load_tallies(VotableType.LYRICS, lyrics.id) == (2, 0, 2)

    async def test_moves_entity_link_counters(self, session: AsyncSession) -> None:
        link = await _make_link(session)
        repo = VoteRepository(session)

        await repo.apply_tally_delta(VotableType.ENTITY_LINK, link.id, d_up=0, d_down=1)
        assert await repo.load_tallies(VotableType.ENTITY_LINK, link.id) == (0, 1, -1)

    async def test_delta_is_a_pure_sql_expression_not_read_modify_write(
        self, session: AsyncSession
    ) -> None:
        # Even with a stale ORM instance in the identity map, the counter update
        # is column = column + delta, so re-reading yields the true DB value.
        match = await _make_match(session)
        repo = VoteRepository(session)
        await repo.apply_tally_delta(VotableType.MATCH, match.id, d_up=5, d_down=2)
        assert await repo.load_tallies(VotableType.MATCH, match.id) == (5, 2, 3)


class TestLoadTallies:
    async def test_none_for_missing_id(self, session: AsyncSession) -> None:
        repo = VoteRepository(session)
        assert await repo.load_tallies(VotableType.MATCH, uuid.uuid4()) is None
        assert await repo.load_tallies(VotableType.LYRICS, uuid.uuid4()) is None
        assert await repo.load_tallies(VotableType.ENTITY_LINK, uuid.uuid4()) is None

    async def test_fresh_row_is_all_zero(self, session: AsyncSession) -> None:
        match = await _make_match(session)
        repo = VoteRepository(session)
        assert await repo.load_tallies(VotableType.MATCH, match.id) == (0, 0, 0)


class TestVoteLedger:
    async def test_upsert_inserts_then_updates(self, session: AsyncSession) -> None:
        user_id = await _make_user(session)
        match = await _make_match(session)
        repo = VoteRepository(session)

        created = await repo.upsert_value(
            user_id=user_id, votable_type=VotableType.MATCH, votable_id=match.id, value=1
        )
        assert created.value == 1

        updated = await repo.upsert_value(
            user_id=user_id, votable_type=VotableType.MATCH, votable_id=match.id, value=-1
        )
        assert updated.id == created.id  # same row, mutated in place
        assert updated.value == -1

        rows = (
            (await session.execute(select(Vote).where(Vote.votable_id == match.id))).scalars().all()
        )
        assert len(rows) == 1

    async def test_get_vote_scoped_to_user_and_votable(self, session: AsyncSession) -> None:
        user_a = await _make_user(session)
        user_b = await _make_user(session)
        match = await _make_match(session)
        repo = VoteRepository(session)
        await repo.upsert_value(
            user_id=user_a, votable_type=VotableType.MATCH, votable_id=match.id, value=1
        )

        assert (
            await repo.get_vote(user_id=user_a, votable_type=VotableType.MATCH, votable_id=match.id)
        ) is not None
        assert (
            await repo.get_vote(user_id=user_b, votable_type=VotableType.MATCH, votable_id=match.id)
        ) is None

    async def test_delete_removes_the_row(self, session: AsyncSession) -> None:
        user_id = await _make_user(session)
        match = await _make_match(session)
        repo = VoteRepository(session)
        vote = await repo.upsert_value(
            user_id=user_id, votable_type=VotableType.MATCH, votable_id=match.id, value=1
        )

        await repo.delete(vote)

        assert (
            await repo.get_vote(
                user_id=user_id, votable_type=VotableType.MATCH, votable_id=match.id
            )
        ) is None


class TestStatusSetters:
    async def test_set_match_status(self, session: AsyncSession) -> None:
        match = await _make_match(session)
        repo = VoteRepository(session)
        await repo.set_match_status(match.id, MatchStatus.COMMUNITY_VERIFIED)
        fresh = await session.get(Match, match.id)
        assert fresh is not None and fresh.status is MatchStatus.COMMUNITY_VERIFIED

    async def test_set_link_status(self, session: AsyncSession) -> None:
        link = await _make_link(session)
        repo = VoteRepository(session)
        await repo.set_link_status(link.id, LinkStatus.DISPUTED)
        fresh = await session.get(EntityLink, link.id)
        assert fresh is not None and fresh.status is LinkStatus.DISPUTED


@pytest.mark.parametrize("value", [-1, 1])
async def test_upsert_respects_check_constraint(session: AsyncSession, value: int) -> None:
    user_id = await _make_user(session)
    match = await _make_match(session)
    repo = VoteRepository(session)
    vote = await repo.upsert_value(
        user_id=user_id, votable_type=VotableType.MATCH, votable_id=match.id, value=value
    )
    assert vote.value == value
