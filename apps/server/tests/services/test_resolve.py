"""Offline (in-memory SQLite + fake registry) tests for ResolveService.

The service is cache-first: parse the query (URL / ``provider:type:id`` / free
text), fetch+snapshot on a cache miss, deterministically merge snapshots into a
canonical entity, and (tracks only) kick matching over the audio providers. No
provider or matcher I/O is real — everything is faked at the registry seam.
"""

from __future__ import annotations

from typing import Any

import pytest
from spotdl_core.model import AudioCandidate, EntityType, ProviderId, Track
from spotdl_core.providers import ProviderUnavailable, UnsupportedURL
from spotdl_server.repositories.matches import MatchRepository
from spotdl_server.repositories.snapshots import SnapshotRepository
from spotdl_server.services.dto import ResolveResult
from spotdl_server.services.resolve import ResolveService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.server.tests.fakes import (
    FakeAudioProvider,
    FakeResolver,
    FakeSearcher,
    build_fake_registry,
)

SPOTIFY_URL = "https://open.spotify.com/track/track123"


def _track(
    name: str = "Song",
    artist: str = "Artist",
    *,
    isrc: str | None = "USABC1234567",
    provider: ProviderId | None = None,
    provider_id: str | None = None,
) -> Track:
    return Track(
        name=name,
        artists=(artist,),
        duration_ms=200_000,
        isrc=isrc,
        provider=provider,
        provider_id=provider_id,
    )


def _candidate(provider: ProviderId, provider_id: str, name: str = "Song") -> AudioCandidate:
    return AudioCandidate(
        provider=provider,
        provider_id=provider_id,
        url=f"https://audio/{provider_id}",
        name=name,
        artists=("Artist",),
        duration_ms=200_000,
    )


async def _count(session: AsyncSession, model: type[Any]) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


async def test_resolve_url_miss_fetches_snapshots_merges_and_returns_track(
    session: AsyncSession,
) -> None:
    resolver = FakeResolver(id=ProviderId.SPOTIFY, track=_track("Hello", "Adele"))
    registry = build_fake_registry(resolver)
    service = ResolveService(session=session, registry=registry)

    result = await service.resolve(SPOTIFY_URL)

    assert isinstance(result, ResolveResult)
    assert result.entity_type == EntityType.TRACK.value
    assert result.track is not None
    assert result.track.name == "Hello"
    assert result.track.artists == ("Adele",)
    assert result.degraded_sources == ()
    assert len(resolver.calls) == 1
    from spotdl_server.db.models import ProviderSnapshot

    assert await _count(session, ProviderSnapshot) == 1


async def test_resolve_cache_hit_skips_provider_call(session: AsyncSession) -> None:
    # Seed a fresh (permanent) snapshot for the ref so the resolver is never hit.
    await SnapshotRepository(session).upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="track123",
        entity_type=EntityType.TRACK,
        raw_payload={"name": "Cached", "artists": ["Cached Artist"], "duration_ms": 123_000},
        name="Cached",
        isrc="USCACHE00001",
        duration_ms=123_000,
        artist_names=["Cached Artist"],
    )
    resolver = FakeResolver(id=ProviderId.SPOTIFY, track=_track("Should Not Appear", "Nope"))
    registry = build_fake_registry(resolver)
    service = ResolveService(session=session, registry=registry)

    result = await service.resolve(SPOTIFY_URL)

    assert resolver.calls == []  # cache hit: no network fetch
    assert result.track is not None
    assert result.track.name == "Cached"


async def test_resolve_records_degraded_source_on_provider_failure(
    session: AsyncSession,
) -> None:
    resolver = FakeResolver(id=ProviderId.SPOTIFY, track=_track("Song", "Artist"))
    # DEEZER's factory raises → recorded in registry.unavailable → degraded_sources.
    registry = build_fake_registry(resolver, failing=[ProviderId.DEEZER])
    service = ResolveService(session=session, registry=registry)

    result = await service.resolve(SPOTIFY_URL)

    assert result.track is not None  # still succeeds from Spotify
    assert result.track.name == "Song"
    assert ProviderId.DEEZER.value in result.degraded_sources


async def test_resolve_records_degraded_source_on_resolve_time_failure(
    session: AsyncSession,
) -> None:
    # Primary resolver succeeds; an audio provider fails mid-resolve → degraded.
    resolver = FakeResolver(id=ProviderId.SPOTIFY, track=_track("Song", "Artist"))
    audio = FakeAudioProvider(
        id=ProviderId.YOUTUBE,
        error=ProviderUnavailable("audio down", provider=ProviderId.YOUTUBE),
    )
    registry = build_fake_registry(resolver, audio)
    service = ResolveService(session=session, registry=registry)

    result = await service.resolve(SPOTIFY_URL)

    assert result.track is not None
    assert ProviderId.YOUTUBE.value in result.degraded_sources


async def test_resolve_kicks_matching_and_persists_matches(session: AsyncSession) -> None:
    resolver = FakeResolver(id=ProviderId.SPOTIFY, track=_track("Song", "Artist"))
    audio = FakeAudioProvider(
        id=ProviderId.YOUTUBE,
        candidates=[_candidate(ProviderId.YOUTUBE, "yt1")],
    )
    registry = build_fake_registry(resolver, audio)
    service = ResolveService(session=session, registry=registry)

    result = await service.resolve(SPOTIFY_URL)

    assert result.track is not None
    assert len(result.track.matches) >= 1
    matches = await MatchRepository(session).list_for_track(_uuid(result.track.id))
    assert matches
    assert matches[0].target_provider == ProviderId.YOUTUBE


async def test_resolve_free_text_falls_back_to_search(session: AsyncSession) -> None:
    # A searcher (Deezer) points at a Spotify track that a Spotify resolver serves.
    found = _track("Found", "Artist", provider=ProviderId.SPOTIFY, provider_id="sp99")
    searcher = FakeSearcher(id=ProviderId.DEEZER, tracks=[found])
    resolver = FakeResolver(id=ProviderId.SPOTIFY, track=_track("Found", "Artist"))
    registry = build_fake_registry(searcher, resolver)
    service = ResolveService(session=session, registry=registry)

    result = await service.resolve("adele hello free text")

    assert result.track is not None
    assert result.track.name == "Found"
    # The free-text query drives the fallback search (Phase 3 enrichment may add a
    # follow-up ISRC search to the same secondary provider afterwards).
    assert searcher.calls[0] == "adele hello free text"
    # Resolved the searched track's ref via the Spotify resolver.
    assert resolver.calls and resolver.calls[0].entity_id == "sp99"


async def test_resolve_unsupported_and_no_result_raises(session: AsyncSession) -> None:
    searcher = FakeSearcher(id=ProviderId.DEEZER, tracks=[])  # search finds nothing
    registry = build_fake_registry(searcher)
    service = ResolveService(session=session, registry=registry)

    with pytest.raises(UnsupportedURL):
        await service.resolve("not a url and no search hit")


async def test_resolve_unregistered_provider_maps_keyerror_to_provider_unavailable(
    session: AsyncSession,
) -> None:
    # The ref parses to SPOTIFY, but the registry has no Spotify provider at all.
    registry = build_fake_registry(FakeResolver(id=ProviderId.DEEZER, track=_track()))
    service = ResolveService(session=session, registry=registry)

    with pytest.raises(ProviderUnavailable) as excinfo:
        await service.resolve(SPOTIFY_URL)
    assert excinfo.value.provider == ProviderId.SPOTIFY


async def test_resolve_is_rerunnable(session: AsyncSession) -> None:
    from spotdl_server.db.models import Match as MatchModel
    from spotdl_server.db.models import Track as TrackModel

    resolver = FakeResolver(id=ProviderId.SPOTIFY, track=_track("Song", "Artist"))
    audio = FakeAudioProvider(
        id=ProviderId.YOUTUBE,
        candidates=[_candidate(ProviderId.YOUTUBE, "yt1")],
    )
    registry = build_fake_registry(resolver, audio)
    service = ResolveService(session=session, registry=registry)

    first = await service.resolve(SPOTIFY_URL)
    second = await service.resolve(SPOTIFY_URL)

    assert first.track is not None and second.track is not None
    assert first.track.id == second.track.id
    assert await _count(session, TrackModel) == 1
    assert await _count(session, MatchModel) == 1  # replaced, not duplicated


async def test_resolve_album_url_merges_container_and_lists_tracks(
    session: AsyncSession,
) -> None:
    from spotdl_core.model import AlbumRef
    from spotdl_core.providers import ResolvedEntity

    album_entity = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="album123",
        entity_type=EntityType.ALBUM,
        album=AlbumRef(
            name="Greatest Hits",
            year=2020,
            track_count=2,
            cover_url="https://img/gh-cover",
            label="Big Label",
            copyright_text="(C) 2020 Big Label",
            album_type="album",
            popularity=71,
            genres=("rock",),
        ),
        tracks=(
            _track("One", "Adele", isrc="USONE0000001"),
            _track("Two", "Adele", isrc="USTWO0000002"),
        ),
    )
    resolver = FakeResolver(id=ProviderId.SPOTIFY, entity=album_entity)
    registry = build_fake_registry(resolver)
    service = ResolveService(session=session, registry=registry)

    result = await service.resolve("https://open.spotify.com/album/album123")

    assert result.entity_type == EntityType.ALBUM.value
    assert result.album is not None
    assert result.album.name == "Greatest Hits"
    assert {t.name for t in result.album.tracks} == {"One", "Two"}
    # The captured album metadata flows snapshot → merge → view.
    assert result.album.label == "Big Label"
    assert result.album.copyright_text == "(C) 2020 Big Label"
    assert result.album.album_type == "album"
    assert result.album.popularity == 71
    assert tuple(result.album.genres) == ("rock",)
    # Nested listing rows carry the album cover thumbnail (no album sub-object).
    assert all(t.album is None for t in result.album.tracks)
    assert all(t.cover_url == "https://img/gh-cover" for t in result.album.tracks)

    # Re-resolve hits the cache and returns the same canonical album (no dup).
    again = await service.resolve("https://open.spotify.com/album/album123")
    assert again.album is not None
    assert again.album.id == result.album.id


async def test_resolve_artist_lists_top_tracks_across_fresh_sessions(
    download_sessionmaker: Any,
) -> None:
    """Resolving an artist must return its top-track listing and never MissingGreenlet.

    Regression (found live via ``deezer:artist:288166``): ``merge_artist`` returned
    the bare artist row without loading ``artist.tracks``, and ``artist_view``
    iterated that relationship (plus each track's ``artists``) on attribute access
    outside the await context. The container path also dropped the resolved
    top-tracks entirely. A fresh session per resolve (empty identity map) is what
    exposes the lazy-load — a single session keeps the relationships warm.
    """
    from spotdl_core.model import AlbumRef, ArtistRef
    from spotdl_core.providers import ResolvedEntity

    artist_entity = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(
            name="Daft Punk",
            image_url="https://img/dp-avatar",
            genres=("french house", "electronic"),
            followers=9_000_000,
            popularity=88,
        ),
        tracks=(
            _track("One More Time", "Daft Punk", isrc="USONE0000011"),
            _track("Harder Better", "Daft Punk", isrc="USTWO0000022"),
        ),
        albums=(
            AlbumRef(
                name="Discovery",
                year=2001,
                album_type="album",
                cover_url="https://img/discovery",
                provider=ProviderId.SPOTIFY,
                provider_id="disc-album-1",
            ),
            AlbumRef(
                name="Homework",
                year=1997,
                album_type="album",
                provider=ProviderId.SPOTIFY,
                provider_id="disc-album-2",
            ),
        ),
    )
    resolver = FakeResolver(id=ProviderId.SPOTIFY, entity=artist_entity)
    registry = build_fake_registry(resolver)

    result_id: Any = None
    for _ in range(2):  # cold then warm, each in a fresh session
        async with download_sessionmaker() as session:
            service = ResolveService(session=session, registry=registry)
            result = await service.resolve("https://open.spotify.com/artist/artist123")
            await session.commit()
            assert result.entity_type == EntityType.ARTIST.value
            assert result.artist is not None
            assert result.artist.name == "Daft Punk"
            # The captured artist metadata flows snapshot → merge → view.
            assert result.artist.image_url == "https://img/dp-avatar"
            assert tuple(result.artist.genres) == ("french house", "electronic")
            assert result.artist.followers == 9_000_000
            assert result.artist.popularity == 88
            assert {t.name for t in result.artist.tracks} == {"One More Time", "Harder Better"}
            # Nested listing tracks carry their artists but no album sub-object.
            assert all(t.artists == ("Daft Punk",) for t in result.artist.tracks)
            assert all(t.album is None for t in result.artist.tracks)
            # The discography flows snapshot → merge → view (metadata-only, ordered),
            # each album carrying its source ref for resolve-on-open — and survives a
            # fresh-session warm re-resolve without MissingGreenlet.
            assert [a.name for a in result.artist.albums] == ["Discovery", "Homework"]
            assert [a.provider_id for a in result.artist.albums] == [
                "disc-album-1",
                "disc-album-2",
            ]
            assert all(a.provider == "spotify" and not a.tracks for a in result.artist.albums)
            if result_id is None:
                result_id = result.artist.id
            else:  # warm re-resolve reuses the same canonical row (no dup)
                assert result.artist.id == result_id


async def test_discography_fills_album_type_over_a_sparse_search_snapshot(
    download_sessionmaker: Any,
) -> None:
    """Discography must FILL gaps (album_type) on a sparser existing snapshot.

    Regression (found live via Mata): a prior search creates album-hit snapshots
    with only name/artist/year/cover — no ``album_type``. When the artist resolve's
    discography later persists the same album (which DOES know its album_type), the
    get-or-reuse guard must not blindly keep the sparse snapshot (leaving the album
    untyped → no "Albums" tab); it merges the ref's fields in, never downgrading.
    """
    from spotdl_core.model import AlbumRef, ArtistRef
    from spotdl_core.providers import ResolvedEntity

    # 1) Seed a SPARSE album snapshot, exactly the search-hit shape (no album_type).
    async with download_sessionmaker() as session:
        await SnapshotRepository(session).upsert(
            provider=ProviderId.SPOTIFY,
            provider_entity_id="mata-alb-1",
            entity_type=EntityType.ALBUM,
            raw_payload={"name": "Młody Matczak", "album_artist": "Mata", "year": 2021},
            name="Młody Matczak",
            album_name="Młody Matczak",
        )
        await session.commit()

    # 2) The artist's discography knows this album is an ``album`` (not a single).
    artist_entity = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="mata-1",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata"),
        tracks=(),
        albums=(
            AlbumRef(
                name="Młody Matczak",
                year=2021,
                album_type="album",
                track_count=15,
                provider=ProviderId.SPOTIFY,
                provider_id="mata-alb-1",
            ),
        ),
    )
    registry = build_fake_registry(FakeResolver(id=ProviderId.SPOTIFY, entity=artist_entity))

    async with download_sessionmaker() as session:
        svc = ResolveService(session=session, registry=registry)
        artist = await svc.resolve("spotify:artist:mata-1")
        await session.commit()
        (album,) = artist.artist.albums
        assert album.album_type == "album"  # filled from the discography ref
        assert album.track_count == 15


async def test_album_resolve_after_discography_returns_full_tracks_and_label(
    download_sessionmaker: Any,
) -> None:
    """Resolving an album whose artist was resolved first must return the FULL album.

    Regression (found by the E2E audit): the artist resolve persists each
    discography album metadata-only (the simplified ``/artists/albums`` shape — no
    tracks, no label). A later *direct* album resolve must NOT cache-hit on that
    trackless stub (returning 0 tracks + a nulled label); it must fetch the full
    album, and the discography persist must never clobber an already-rich snapshot.
    """
    from spotdl_core.model import AlbumRef, ArtistRef
    from spotdl_core.providers import ResolvedEntity

    disc_ref = AlbumRef(
        name="Discovery",
        year=2001,
        album_type="album",
        provider=ProviderId.SPOTIFY,
        provider_id="disc-1",
    )
    artist_entity = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist-1",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Daft Punk"),
        tracks=(),
        albums=(disc_ref,),
    )
    # The SAME album ref, but fully resolved: carries its label + track listing.
    full_album = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="disc-1",
        entity_type=EntityType.ALBUM,
        album=AlbumRef(name="Discovery", year=2001, album_type="album", label="Virgin"),
        tracks=(
            _track("One More Time", "Daft Punk", isrc="USONE0000031"),
            _track("Aerodynamic", "Daft Punk", isrc="USONE0000032"),
        ),
    )

    class _PerRefResolver:
        id = ProviderId.SPOTIFY

        def __init__(self) -> None:
            self.calls: list[Any] = []

        async def resolve(self, ref: Any) -> ResolvedEntity:
            self.calls.append(ref)
            return artist_entity if ref.entity_type is EntityType.ARTIST else full_album

    registry = build_fake_registry(_PerRefResolver())

    # Resolve the artist first (persists Discovery as a trackless discography stub).
    async with download_sessionmaker() as session:
        svc = ResolveService(session=session, registry=registry)
        artist = await svc.resolve("spotify:artist:artist-1")
        await session.commit()
        assert [a.name for a in artist.artist.albums] == ["Discovery"]

    # Now resolve the album directly — it must return the FULL album, not the stub.
    async with download_sessionmaker() as session:
        svc = ResolveService(session=session, registry=registry)
        album = await svc.resolve("spotify:album:disc-1")
        await session.commit()
        assert album.album is not None
        assert album.album.label == "Virgin"
        assert {t.name for t in album.album.tracks} == {"One More Time", "Aerodynamic"}

    # Re-resolving the artist again must not clobber the now-rich album's label.
    async with download_sessionmaker() as session:
        svc = ResolveService(session=session, registry=registry)
        await svc.resolve("spotify:artist:artist-1")
        await session.commit()
    async with download_sessionmaker() as session:
        svc = ResolveService(session=session, registry=registry)
        again = await svc.resolve("spotify:album:disc-1")
        assert again.album.label == "Virgin"
        assert len(again.album.tracks) == 2


def _uuid(value: str) -> Any:
    import uuid

    return uuid.UUID(value)


async def test_warm_cache_reresolve_in_fresh_session_loads_relationships(
    download_sessionmaker: Any,
) -> None:
    """Re-resolving in a SEPARATE session must not MissingGreenlet.

    Regression (found by a live re-download): after the first resolve the
    canonical track exists; a second resolve in a fresh session (empty identity
    map) reached matching, accessed ``track.album`` — a selectin relationship the
    merge only *expired* via ``refresh`` — and lazy-loaded it outside the await
    context. The single-session cache-hit test above never exercised this because
    its identity map kept the relationships loaded.
    """
    from spotdl_core.model import AlbumRef

    # The track MUST carry an album: `track.album` is the selectin relationship
    # that lazy-loaded on the warm path. A None album never triggers the bug.
    track = Track(
        name="Warm",
        artists=("Cache Artist",),
        duration_ms=200_000,
        isrc="USWARM000001",
        album=AlbumRef(name="Warm Album", year=2021, track_count=1),
    )
    resolver = FakeResolver(id=ProviderId.SPOTIFY, track=track)
    registry = build_fake_registry(resolver)

    for _ in range(2):
        async with download_sessionmaker() as session:
            service = ResolveService(session=session, registry=registry)
            result = await service.resolve(SPOTIFY_URL)
            await session.commit()
            assert result.track is not None
            assert result.track.name == "Warm"
            assert result.track.artists == ("Cache Artist",)
            assert result.track.album is not None
            assert result.track.album.name == "Warm Album"
