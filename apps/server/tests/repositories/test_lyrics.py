"""Offline (in-memory SQLite) tests for :class:`LyricsRepository`."""

from __future__ import annotations

import uuid

from spotdl_core.model import LyricsKind, ProviderId
from spotdl_server.db.models import Track
from spotdl_server.repositories.lyrics import LyricsRepository
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_track(session: AsyncSession) -> Track:
    track = Track(name="Test Track", duration_ms=211000)
    session.add(track)
    await session.flush()
    return track


async def test_upsert_idempotent_by_triple_updates_text(session: AsyncSession) -> None:
    track = await _make_track(session)
    repo = LyricsRepository(session)

    first = await repo.upsert(track.id, ProviderId.LRCLIB, LyricsKind.SYNCED, "old text")
    second = await repo.upsert(track.id, ProviderId.LRCLIB, LyricsKind.SYNCED, "new text")

    assert first.id == second.id
    assert second.text == "new text"


async def test_upsert_distinct_triples_are_distinct_rows(session: AsyncSession) -> None:
    track = await _make_track(session)
    repo = LyricsRepository(session)

    a = await repo.upsert(track.id, ProviderId.LRCLIB, LyricsKind.SYNCED, "synced")
    b = await repo.upsert(track.id, ProviderId.LRCLIB, LyricsKind.PLAIN, "plain")
    c = await repo.upsert(track.id, ProviderId.GENIUS, LyricsKind.PLAIN, "genius")

    assert len({a.id, b.id, c.id}) == 3


async def test_upsert_preserves_tallies(session: AsyncSession) -> None:
    track = await _make_track(session)
    repo = LyricsRepository(session)

    row = await repo.upsert(track.id, ProviderId.LRCLIB, LyricsKind.SYNCED, "old")
    row.upvotes = 7
    row.downvotes = 2
    row.net_score = 5
    await session.flush()

    updated = await repo.upsert(track.id, ProviderId.LRCLIB, LyricsKind.SYNCED, "new")
    assert updated.id == row.id
    assert updated.text == "new"
    assert updated.upvotes == 7
    assert updated.downvotes == 2
    assert updated.net_score == 5


async def test_list_for_track_synced_before_plain_then_net_score(session: AsyncSession) -> None:
    track = await _make_track(session)
    repo = LyricsRepository(session)

    plain_low = await repo.upsert(track.id, ProviderId.GENIUS, LyricsKind.PLAIN, "p1")
    plain_high = await repo.upsert(track.id, ProviderId.MUSIXMATCH, LyricsKind.PLAIN, "p2")
    synced_low = await repo.upsert(track.id, ProviderId.AZLYRICS, LyricsKind.SYNCED, "s1")
    synced_high = await repo.upsert(track.id, ProviderId.LRCLIB, LyricsKind.SYNCED, "s2")

    synced_high.net_score = 10
    synced_low.net_score = 1
    plain_high.net_score = 8
    plain_low.net_score = 2
    await session.flush()

    listed = await repo.list_for_track(track.id)
    assert [row.id for row in listed] == [
        synced_high.id,
        synced_low.id,
        plain_high.id,
        plain_low.id,
    ]


async def test_get_returns_none_when_absent(session: AsyncSession) -> None:
    repo = LyricsRepository(session)
    assert await repo.get(uuid.uuid4()) is None
