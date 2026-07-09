"""Offline (in-memory SQLite) tests for :class:`EntityLinkRepository`."""

from __future__ import annotations

import uuid

from spotdl_core.model import EntityType, ProviderId
from spotdl_server.db.enums import LinkStatus
from spotdl_server.db.models import ProviderSnapshot
from spotdl_server.repositories.links import EntityLinkRepository
from spotdl_server.repositories.snapshots import SnapshotRepository
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_snapshot(
    session: AsyncSession, provider: ProviderId, provider_entity_id: str
) -> ProviderSnapshot:
    return await SnapshotRepository(session).upsert(
        provider=provider,
        provider_entity_id=provider_entity_id,
        entity_type=EntityType.TRACK,
        raw_payload={},
    )


async def _count(session: AsyncSession) -> int:
    from spotdl_server.db.models import EntityLink

    result = await session.execute(select(func.count()).select_from(EntityLink))
    return int(result.scalar_one())


async def test_upsert_idempotent_by_triple(session: AsyncSession) -> None:
    repo = EntityLinkRepository(session)
    snapshot = await _make_snapshot(session, ProviderId.SPOTIFY, "s1")
    entity_id = uuid.uuid4()

    first = await repo.upsert(EntityType.TRACK, entity_id, snapshot.id)
    second = await repo.upsert(EntityType.TRACK, entity_id, snapshot.id)

    assert first.id == second.id
    assert await _count(session) == 1
    assert first.status == LinkStatus.AUTO


async def test_upsert_distinct_snapshots_are_distinct_rows(session: AsyncSession) -> None:
    repo = EntityLinkRepository(session)
    s1 = await _make_snapshot(session, ProviderId.SPOTIFY, "s1")
    s2 = await _make_snapshot(session, ProviderId.DEEZER, "d1")
    entity_id = uuid.uuid4()

    link1 = await repo.upsert(EntityType.TRACK, entity_id, s1.id)
    link2 = await repo.upsert(EntityType.TRACK, entity_id, s2.id)

    assert link1.id != link2.id
    assert await _count(session) == 2


async def test_for_entity_returns_all_links(session: AsyncSession) -> None:
    repo = EntityLinkRepository(session)
    s1 = await _make_snapshot(session, ProviderId.SPOTIFY, "s1")
    s2 = await _make_snapshot(session, ProviderId.DEEZER, "d1")
    entity_id = uuid.uuid4()
    other_entity = uuid.uuid4()

    await repo.upsert(EntityType.TRACK, entity_id, s1.id)
    await repo.upsert(EntityType.TRACK, entity_id, s2.id)
    await repo.upsert(EntityType.TRACK, other_entity, s1.id)

    links = await repo.for_entity(EntityType.TRACK, entity_id)
    assert {link.snapshot_id for link in links} == {s1.id, s2.id}


async def test_set_status_changes_status(session: AsyncSession) -> None:
    repo = EntityLinkRepository(session)
    snapshot = await _make_snapshot(session, ProviderId.SPOTIFY, "s1")
    entity_id = uuid.uuid4()

    link = await repo.upsert(EntityType.TRACK, entity_id, snapshot.id)
    assert link.status == LinkStatus.AUTO

    await repo.set_status(link, LinkStatus.VERIFIED)
    assert link.status == LinkStatus.VERIFIED

    # Re-upsert must not clobber a human-set status back to AUTO.
    reupserted = await repo.upsert(EntityType.TRACK, entity_id, snapshot.id)
    assert reupserted.id == link.id
    assert reupserted.status == LinkStatus.VERIFIED


async def test_upsert_honors_explicit_status_on_insert(session: AsyncSession) -> None:
    repo = EntityLinkRepository(session)
    snapshot = await _make_snapshot(session, ProviderId.SPOTIFY, "s1")
    entity_id = uuid.uuid4()

    link = await repo.upsert(EntityType.TRACK, entity_id, snapshot.id, status=LinkStatus.VERIFIED)
    assert link.status == LinkStatus.VERIFIED
