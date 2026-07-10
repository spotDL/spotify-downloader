"""Offline (in-memory SQLite) tests for :class:`SnapshotRepository`."""

from datetime import UTC, datetime, timedelta

from spotdl_core.model import EntityType, ProviderId
from spotdl_server.db.models import ProviderSnapshot
from spotdl_server.repositories.snapshots import SnapshotRepository
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def _count(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(ProviderSnapshot))
    return int(result.scalar_one())


async def test_upsert_creates_then_updates_same_row(session: AsyncSession) -> None:
    repo = SnapshotRepository(session)

    created = await repo.upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="track123",
        entity_type=EntityType.TRACK,
        raw_payload={"v": 1},
        name="Old Name",
        isrc="USABC1234567",
    )
    assert await _count(session) == 1
    first_id = created.id
    first_fetched = created.fetched_at

    updated = await repo.upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="track123",
        entity_type=EntityType.TRACK,
        raw_payload={"v": 2},
        name="New Name",
        isrc="USABC1234567",
    )
    # Same row (unique on provider+provider_entity_id), payload refreshed.
    assert await _count(session) == 1
    assert updated.id == first_id
    assert updated.raw_payload == {"v": 2}
    assert updated.name == "New Name"
    assert updated.fetched_at >= first_fetched


async def test_get_returns_none_when_absent(session: AsyncSession) -> None:
    repo = SnapshotRepository(session)
    assert await repo.get(ProviderId.SPOTIFY, "missing") is None


async def test_get_by_isrc_returns_all_providers(session: AsyncSession) -> None:
    repo = SnapshotRepository(session)
    isrc = "GBAYE0000001"
    await repo.upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="s1",
        entity_type=EntityType.TRACK,
        raw_payload={},
        isrc=isrc,
    )
    await repo.upsert(
        provider=ProviderId.DEEZER,
        provider_entity_id="d1",
        entity_type=EntityType.TRACK,
        raw_payload={},
        isrc=isrc,
    )
    await repo.upsert(
        provider=ProviderId.ITUNES,
        provider_entity_id="i1",
        entity_type=EntityType.TRACK,
        raw_payload={},
        isrc="OTHER0000001",
    )

    rows = await repo.get_by_isrc(isrc)
    assert {r.provider for r in rows} == {ProviderId.SPOTIFY, ProviderId.DEEZER}


async def test_get_fresh_none_past_expires(session: AsyncSession) -> None:
    repo = SnapshotRepository(session)
    now = datetime.now(UTC)

    await repo.upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="expired",
        entity_type=EntityType.TRACK,
        raw_payload={},
        expires_at=now - timedelta(hours=1),
    )
    await repo.upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="fresh",
        entity_type=EntityType.TRACK,
        raw_payload={},
        expires_at=now + timedelta(hours=1),
    )
    await repo.upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="permanent",
        entity_type=EntityType.TRACK,
        raw_payload={},
        expires_at=None,
    )

    assert await repo.get_fresh(ProviderId.SPOTIFY, "expired", now) is None
    assert await repo.get_fresh(ProviderId.SPOTIFY, "fresh", now) is not None
    assert await repo.get_fresh(ProviderId.SPOTIFY, "permanent", now) is not None
    assert await repo.get_fresh(ProviderId.SPOTIFY, "missing", now) is None


async def test_fill_only_upsert_fills_gaps_without_clobbering(session: AsyncSession) -> None:
    """A preview write must fill gaps and never downgrade a richer snapshot.

    Regression (found live via Mata / the E2E sweep): the default upsert clobbers
    everything, so a sparse search hit persisted AFTER a full resolve wiped the
    rich payload (followers/label/album_type) and normalized columns (isrc).
    """
    repo = SnapshotRepository(session)
    rich = await repo.upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="artist1",
        entity_type=EntityType.ARTIST,
        raw_payload={"name": "Mata", "followers": 2_700_000, "genres": [], "bio": None},
        name="Mata",
        art_url="https://img/full",
    )
    rich_fetched = rich.fetched_at

    filled = await repo.upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="artist1",
        entity_type=EntityType.ARTIST,
        raw_payload={"name": "Mata", "genres": ["rap"], "bio": "polish rapper", "partial": True},
        name="Mata (search)",
        art_url="https://img/sparse",
        fill_only=True,
    )
    assert filled.id == rich.id
    # Rich values kept; null/empty gaps healed; lifecycle marker never grafted.
    assert filled.raw_payload["followers"] == 2_700_000
    assert filled.raw_payload["genres"] == ["rap"]
    assert filled.raw_payload["bio"] == "polish rapper"
    assert "partial" not in filled.raw_payload
    # Columns: existing wins; freshness NOT renewed by a preview.
    assert filled.name == "Mata"
    assert filled.art_url == "https://img/full"
    assert filled.fetched_at == rich_fetched


async def test_fill_only_upsert_inserts_normally_when_row_absent(session: AsyncSession) -> None:
    repo = SnapshotRepository(session)
    created = await repo.upsert(
        provider=ProviderId.DEEZER,
        provider_entity_id="t9",
        entity_type=EntityType.TRACK,
        raw_payload={"name": "Song", "partial": True},
        name="Song",
        fill_only=True,
    )
    assert created.raw_payload == {"name": "Song", "partial": True}
    assert await _count(session) == 1  # inserted (no pre-existing row to fill)
