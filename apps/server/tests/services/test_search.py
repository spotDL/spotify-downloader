"""Offline (in-memory SQLite + fake registry) tests for SearchService.

SearchService is a thin orchestration seam: it delegates the fan-out / merge /
de-dup to the shared ``provider_search`` helper (Task 8), snapshots every result
track so a subsequent resolve is a cache hit, and returns a ``SearchResult`` DTO.
Provider failures are non-fatal and surface in ``degraded_sources``. No provider
I/O is real — everything is faked at the registry seam.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from spotdl_core.model import ProviderId, Track
from spotdl_core.providers import ProviderUnavailable
from spotdl_server.db.models import ProviderSnapshot
from spotdl_server.repositories.snapshots import SnapshotRepository
from spotdl_server.services.dto import SearchResult, TrackView
from spotdl_server.services.search import SearchService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.server.tests.fakes import FakeSearcher, build_fake_registry


def _track(
    name: str,
    artist: str = "Artist",
    *,
    isrc: str | None = None,
    provider: ProviderId | None = ProviderId.SPOTIFY,
    provider_id: str | None = "sp1",
) -> Track:
    return Track(
        name=name,
        artists=(artist,),
        duration_ms=200_000,
        isrc=isrc,
        provider=provider,
        provider_id=provider_id,
    )


async def _count(session: AsyncSession, model: type[Any]) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


async def test_search_delegates_and_returns_track_views(session: AsyncSession) -> None:
    searcher = FakeSearcher(
        id=ProviderId.SPOTIFY,
        tracks=[
            _track("One", provider_id="sp1", isrc="USONE0000001"),
            _track("Two", provider_id="sp2", isrc="USTWO0000002"),
        ],
    )
    registry = build_fake_registry(searcher)
    service = SearchService(session=session, registry=registry)

    result = await service.search("adele")

    assert isinstance(result, SearchResult)
    assert searcher.calls == ["adele"]  # delegated to provider_search
    assert all(isinstance(t, TrackView) for t in result.tracks)
    assert {t.name for t in result.tracks} == {"One", "Two"}
    assert result.degraded_sources == ()


async def test_search_snapshots_each_result(session: AsyncSession) -> None:
    searcher = FakeSearcher(
        id=ProviderId.SPOTIFY,
        tracks=[
            _track("One", provider_id="sp1", isrc="USONE0000001"),
            _track("Two", provider_id="sp2", isrc="USTWO0000002"),
        ],
    )
    service = SearchService(session=session, registry=build_fake_registry(searcher))

    await service.search("adele")

    # Every result track was persisted as a provider snapshot (durable cache).
    assert await _count(session, ProviderSnapshot) == 2


async def test_search_snapshot_enables_cache_hit(session: AsyncSession) -> None:
    searcher = FakeSearcher(
        id=ProviderId.SPOTIFY, tracks=[_track("One", provider_id="sp1", isrc="USONE0000001")]
    )
    service = SearchService(session=session, registry=build_fake_registry(searcher))

    await service.search("adele")

    # A subsequent resolve of the same provider ref finds a fresh snapshot.
    fresh = await SnapshotRepository(session).get_fresh(
        ProviderId.SPOTIFY, "sp1", datetime.now(UTC)
    )
    assert fresh is not None
    assert fresh.name == "One"


async def test_search_respects_limit(session: AsyncSession) -> None:
    searcher = FakeSearcher(
        id=ProviderId.SPOTIFY,
        tracks=[
            _track("One", provider_id="sp1", isrc="USONE0000001"),
            _track("Two", provider_id="sp2", isrc="USTWO0000002"),
            _track("Three", provider_id="sp3", isrc="USTHR0000003"),
        ],
    )
    service = SearchService(session=session, registry=build_fake_registry(searcher))

    result = await service.search("adele", limit=2)

    assert len(result.tracks) == 2
    assert await _count(session, ProviderSnapshot) == 2


async def test_search_failing_searcher_is_degraded_not_fatal(session: AsyncSession) -> None:
    good = FakeSearcher(id=ProviderId.SPOTIFY, tracks=[_track("Good", provider_id="sp1")])
    bad = FakeSearcher(
        id=ProviderId.DEEZER,
        error=ProviderUnavailable("deezer down", provider=ProviderId.DEEZER),
    )
    service = SearchService(session=session, registry=build_fake_registry(good, bad))

    result = await service.search("adele")

    assert {t.name for t in result.tracks} == {"Good"}  # still returns good results
    assert ProviderId.DEEZER.value in result.degraded_sources


async def test_search_degraded_includes_registry_unavailable(session: AsyncSession) -> None:
    good = FakeSearcher(id=ProviderId.SPOTIFY, tracks=[_track("Good", provider_id="sp1")])
    # DEEZER's factory raises → recorded in registry.unavailable → degraded_sources.
    registry = build_fake_registry(good, failing=[ProviderId.DEEZER])
    service = SearchService(session=session, registry=registry)

    result = await service.search("adele")

    assert {t.name for t in result.tracks} == {"Good"}
    assert ProviderId.DEEZER.value in result.degraded_sources
    assert result.degraded_sources == tuple(sorted(result.degraded_sources))


async def test_search_empty_returns_empty_tuple(session: AsyncSession) -> None:
    searcher = FakeSearcher(id=ProviderId.SPOTIFY, tracks=[])
    service = SearchService(session=session, registry=build_fake_registry(searcher))

    result = await service.search("no such song")

    assert result.tracks == ()
    assert result.degraded_sources == ()
    assert await _count(session, ProviderSnapshot) == 0
