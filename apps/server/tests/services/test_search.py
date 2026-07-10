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

from spotdl_core.model import EntityType, ProviderId, SearchHit, Track
from spotdl_core.providers import ProviderUnavailable
from spotdl_server.db.models import ProviderSnapshot
from spotdl_server.repositories.snapshots import SnapshotRepository
from spotdl_server.services.dto import SearchResult, TrackView
from spotdl_server.services.search import SearchService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.server.tests.fakes import FakeEntitySearcher, FakeSearcher, build_fake_registry


def _hit(
    entity_type: EntityType,
    name: str,
    *,
    subtitle: str | None = None,
    provider: ProviderId = ProviderId.SPOTIFY,
    provider_id: str = "x1",
    isrc: str | None = None,
) -> SearchHit:
    return SearchHit(
        entity_type=entity_type,
        provider=provider,
        provider_id=provider_id,
        name=name,
        subtitle=subtitle,
        isrc=isrc,
    )


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


async def test_search_hit_carries_album_cover(session: AsyncSession) -> None:
    """A search preview surfaces the provider hit's album cover for the result card.

    Regression: the preview view dropped ``album`` entirely, so every result card
    rendered a blank thumbnail. The hit's album (metadata only) now flows through.
    """
    from spotdl_core.model import AlbumRef

    hit = Track(
        name="One",
        artists=("Artist",),
        duration_ms=200_000,
        provider=ProviderId.SPOTIFY,
        provider_id="sp1",
        album=AlbumRef(name="An Album", year=2020, cover_url="https://img/cover.jpg"),
    )
    searcher = FakeSearcher(id=ProviderId.SPOTIFY, tracks=[hit])
    service = SearchService(session=session, registry=build_fake_registry(searcher))

    result = await service.search("adele")

    (view,) = result.tracks
    assert view.album is not None
    assert view.album.name == "An Album"
    assert view.album.cover_url == "https://img/cover.jpg"


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
    assert result.albums == ()
    assert result.artists == ()
    assert result.playlists == ()
    assert result.degraded_sources == ()
    assert await _count(session, ProviderSnapshot) == 0


# --- universal (multi-entity) search --------------------------------------


async def test_search_returns_all_entity_groups(session: AsyncSession) -> None:
    # Distinct provider ids: the registry keys specs by id, so a track-only
    # searcher and an entity searcher must be different providers to coexist.
    tracks = FakeSearcher(id=ProviderId.SPOTIFY, tracks=[_track("Song", provider_id="t1")])
    dz = ProviderId.DEEZER
    entities = FakeEntitySearcher(
        id=dz,
        hits=[
            _hit(EntityType.ALBUM, "An Album", subtitle="Band", provider=dz, provider_id="al1"),
            _hit(EntityType.ARTIST, "An Artist", provider=dz, provider_id="ar1"),
            _hit(
                EntityType.PLAYLIST, "A Playlist", subtitle="Owner", provider=dz, provider_id="pl1"
            ),
        ],
    )
    service = SearchService(session=session, registry=build_fake_registry(tracks, entities))

    result = await service.search("query")

    assert {t.name for t in result.tracks} == {"Song"}
    assert [(a.name, a.album_artist) for a in result.albums] == [("An Album", "Band")]
    assert [a.name for a in result.artists] == ["An Artist"]
    assert [(p.name, p.owner) for p in result.playlists] == [("A Playlist", "Owner")]
    # The playlist preview id is the resolvable provider ref (not snapshotted).
    assert result.playlists[0].id == "deezer:playlist:pl1"


async def test_search_snapshots_album_and_artist_hits(session: AsyncSession) -> None:
    entities = FakeEntitySearcher(
        id=ProviderId.SPOTIFY,
        hits=[
            _hit(EntityType.ALBUM, "An Album", provider_id="al1"),
            _hit(EntityType.ARTIST, "An Artist", provider_id="ar1"),
            _hit(EntityType.PLAYLIST, "A Playlist", provider_id="pl1"),
        ],
    )
    service = SearchService(session=session, registry=build_fake_registry(entities))

    result = await service.search("query")

    # Album + artist hits are snapshotted (resolve-on-open cache hit); playlist is not.
    assert await _count(session, ProviderSnapshot) == 2
    album_snap = await SnapshotRepository(session).get_fresh(
        ProviderId.SPOTIFY, "al1", datetime.now(UTC)
    )
    assert album_snap is not None
    assert album_snap.entity_type is EntityType.ALBUM
    # The preview view's id is its snapshot id (a resolvable durable ref).
    assert result.albums[0].id == str(album_snap.id)


async def test_search_dedupes_entity_hits_across_providers(session: AsyncSession) -> None:
    spotify = FakeEntitySearcher(
        id=ProviderId.SPOTIFY,
        hits=[_hit(EntityType.ALBUM, "Discovery", subtitle="Daft Punk", provider_id="sp_al")],
    )
    deezer = FakeEntitySearcher(
        id=ProviderId.DEEZER,
        hits=[_hit(EntityType.ALBUM, "discovery", subtitle="daft punk", provider_id="dz_al")],
    )
    service = SearchService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.search("discovery")

    # Same (name, subtitle) casefolded → Spotify (higher priority) wins the dedup.
    assert len(result.albums) == 1
    assert result.albums[0].album_artist == "Daft Punk"


async def test_search_failing_entity_searcher_is_degraded(session: AsyncSession) -> None:
    good = FakeSearcher(id=ProviderId.SPOTIFY, tracks=[_track("Good", provider_id="t1")])
    bad = FakeEntitySearcher(
        id=ProviderId.DEEZER,
        error=ProviderUnavailable("deezer down", provider=ProviderId.DEEZER),
    )
    service = SearchService(session=session, registry=build_fake_registry(good, bad))

    result = await service.search("query")

    assert {t.name for t in result.tracks} == {"Good"}  # still returns good results
    assert ProviderId.DEEZER.value in result.degraded_sources


async def test_search_hit_never_clobbers_a_rich_snapshot(session: AsyncSession) -> None:
    """Searching AFTER a full resolve must not wipe the rich snapshot.

    Regression (E2E sweep): the artist/album search-hit writers used the default
    clobbering upsert, so a search for an already-resolved artist replaced its
    payload (followers/popularity) with the sparse hit shape — degrading /sources
    and every future re-merge.
    """
    # A rich snapshot, as a full artist resolve persists it.
    await SnapshotRepository(session).upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="ar1",
        entity_type=EntityType.ARTIST,
        raw_payload={"name": "Mata", "followers": 2_700_000, "popularity": 73, "genres": ["rap"]},
        name="Mata",
        art_url="https://img/full",
    )
    searcher = FakeEntitySearcher(
        id=ProviderId.SPOTIFY,
        hits=[_hit(EntityType.ARTIST, "Mata", provider_id="ar1")],
    )
    service = SearchService(session=session, registry=build_fake_registry(searcher))

    await service.search("mata")

    snapshot = await SnapshotRepository(session).get(ProviderId.SPOTIFY, "ar1")
    assert snapshot is not None
    assert snapshot.raw_payload["followers"] == 2_700_000  # not clobbered
    assert snapshot.raw_payload["popularity"] == 73
    assert snapshot.art_url == "https://img/full"


async def test_isrc_less_track_hit_is_marked_partial(session: AsyncSession) -> None:
    """A searcher that returns tracks without ISRC (Deezer/iTunes) must mark the
    snapshot partial so a direct open fetches the full track instead of
    cache-hitting the sparse listing."""
    searcher = FakeSearcher(
        id=ProviderId.DEEZER,
        tracks=[_track("NoIsrc", isrc=None, provider=ProviderId.DEEZER, provider_id="d1")],
    )
    service = SearchService(session=session, registry=build_fake_registry(searcher))

    await service.search("noisrc")

    snapshot = await SnapshotRepository(session).get(ProviderId.DEEZER, "d1")
    assert snapshot is not None
    assert snapshot.raw_payload.get("partial") is True
