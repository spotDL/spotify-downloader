"""Cross-provider metadata enrichment (spec §Phase 3) — offline ResolveService tests.

On a cache miss the resolve fans out to the OTHER canonical metadata providers,
snapshots the same real-world entity from each, and links those snapshots so the
deterministic merge folds every source into the canonical row — Spotify still
wins display fields, but a Deezer-only field fills a gap. The fan-out is
best-effort (a failing secondary degrades, never fatal) and cached (a warm
re-resolve does not re-fan-out).
"""

from __future__ import annotations

import uuid

from spotdl_core.model import (
    AlbumRef,
    ArtistRef,
    EntityType,
    ProviderId,
    SearchHit,
    Track,
)
from spotdl_core.providers import ProviderUnavailable, ResolvedEntity
from spotdl_server.repositories.snapshots import SnapshotRepository
from spotdl_server.services.resolve import ResolveService
from sqlalchemy.ext.asyncio import AsyncSession

from apps.server.tests.fakes import (
    FakeMetadataProvider,
    FakeResolver,
    build_fake_registry,
)

SPOTIFY_TRACK_URL = "https://open.spotify.com/track/track123"
SPOTIFY_ALBUM_URL = "https://open.spotify.com/album/album123"
SPOTIFY_ARTIST_URL = "https://open.spotify.com/artist/artist123"
ISRC = "USABC1234567"


def _track(
    name: str,
    artist: str,
    *,
    isrc: str | None = ISRC,
    genres: tuple[str, ...] = (),
    provider: ProviderId | None = None,
    provider_id: str | None = None,
) -> Track:
    return Track(
        name=name,
        artists=(artist,),
        duration_ms=200_000,
        isrc=isrc,
        genres=genres,
        provider=provider,
        provider_id=provider_id,
    )


async def _linked_providers(session: AsyncSession, entity_type: EntityType, id: str) -> set[str]:
    snapshots = await SnapshotRepository(session).list_for_entity(entity_type, uuid.UUID(id))
    return {snapshot.provider.value for snapshot in snapshots}


def _deezer_track_source(*, genres: tuple[str, ...]) -> FakeMetadataProvider:
    """A Deezer metadata source whose search hit + resolved track carry ``genres``."""
    hit = _track("Hello", "Adele", provider=ProviderId.DEEZER, provider_id="dz1")
    full = _track("Hello", "Adele", genres=genres, provider=ProviderId.DEEZER, provider_id="dz1")
    return FakeMetadataProvider(
        id=ProviderId.DEEZER,
        tracks=[hit],
        resolved={
            EntityType.TRACK: ResolvedEntity(
                provider=ProviderId.DEEZER,
                provider_id="dz1",
                entity_type=EntityType.TRACK,
                track=full,
            )
        },
    )


async def test_track_enrichment_links_and_merges_secondary(session: AsyncSession) -> None:
    # Spotify's track carries no genres; Deezer's does → the merge fills the gap
    # while Spotify still wins the display name.
    spotify = FakeResolver(id=ProviderId.SPOTIFY, track=_track("Hello", "Adele"))
    deezer = _deezer_track_source(genres=("pop",))
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_TRACK_URL)

    assert result.track is not None
    assert result.track.name == "Hello"  # Spotify-first display
    assert tuple(result.track.genres) == ("pop",)  # Deezer-only field fills the gap
    assert result.degraded_sources == ()
    # BOTH providers' snapshots are linked to the one canonical track.
    assert await _linked_providers(session, EntityType.TRACK, result.track.id) == {
        "spotify",
        "deezer",
    }
    assert deezer.resolve_calls and deezer.resolve_calls[0].entity_id == "dz1"


async def test_warm_reresolve_does_not_refanout(session: AsyncSession) -> None:
    spotify = FakeResolver(id=ProviderId.SPOTIFY, track=_track("Hello", "Adele"))
    deezer = _deezer_track_source(genres=("pop",))
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    first = await service.resolve(SPOTIFY_TRACK_URL)
    calls_after_cold = list(deezer.search_calls)
    second = await service.resolve(SPOTIFY_TRACK_URL)

    assert first.track is not None and second.track is not None
    assert first.track.id == second.track.id
    # The warm re-resolve hit the snapshot cache: no second fan-out to Deezer …
    assert deezer.search_calls == calls_after_cold
    assert len(deezer.search_calls) == 1  # one ISRC search, cold only
    # … yet the cached secondary snapshot still merges (genres survive).
    assert tuple(second.track.genres) == ("pop",)


async def test_failing_secondary_is_degraded_not_fatal(session: AsyncSession) -> None:
    spotify = FakeResolver(id=ProviderId.SPOTIFY, track=_track("Hello", "Adele"))
    deezer = FakeMetadataProvider(
        id=ProviderId.DEEZER,
        error=ProviderUnavailable("deezer down", provider=ProviderId.DEEZER),
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_TRACK_URL)

    assert result.track is not None  # primary still succeeds
    assert result.track.name == "Hello"
    assert ProviderId.DEEZER.value in result.degraded_sources
    # Only the primary linked; the failed secondary contributed nothing.
    assert await _linked_providers(session, EntityType.TRACK, result.track.id) == {"spotify"}


async def test_track_enrichment_skips_non_matching_hit(session: AsyncSession) -> None:
    # A Deezer hit for a different recording (different title/artist, no shared ISRC)
    # fails the matcher gate → not linked, a clean miss (not degraded).
    spotify = FakeResolver(id=ProviderId.SPOTIFY, track=_track("Hello", "Adele"))
    unrelated = _track(
        "Totally Different", "Someone Else", isrc="GBXYZ9999999",
        provider=ProviderId.DEEZER, provider_id="dz9",
    )
    deezer = FakeMetadataProvider(id=ProviderId.DEEZER, tracks=[unrelated])
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_TRACK_URL)

    assert result.track is not None
    assert result.degraded_sources == ()  # a non-match is a miss, not an error
    assert await _linked_providers(session, EntityType.TRACK, result.track.id) == {"spotify"}


async def test_album_enrichment_fills_gap(session: AsyncSession) -> None:
    spotify_album = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="album123",
        entity_type=EntityType.ALBUM,
        album=AlbumRef(name="Greatest Hits", year=2020, track_count=2),  # no label
        tracks=(_track("One", "Adele", isrc="USONE0000001"),),
    )
    deezer_album = ResolvedEntity(
        provider=ProviderId.DEEZER,
        provider_id="dzalbum",
        entity_type=EntityType.ALBUM,
        album=AlbumRef(name="Greatest Hits", year=2020, label="Deezer Label"),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_album)
    deezer = FakeMetadataProvider(
        id=ProviderId.DEEZER,
        hits=[
            SearchHit(
                entity_type=EntityType.ALBUM,
                provider=ProviderId.DEEZER,
                provider_id="dzalbum",
                name="Greatest Hits",
                year=2020,
            )
        ],
        resolved={EntityType.ALBUM: deezer_album},
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_ALBUM_URL)

    assert result.album is not None
    assert result.album.name == "Greatest Hits"
    assert result.album.label == "Deezer Label"  # Deezer-only field fills the gap
    assert await _linked_providers(session, EntityType.ALBUM, result.album.id) == {
        "spotify",
        "deezer",
    }


async def test_artist_enrichment_fills_gap(session: AsyncSession) -> None:
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Daft Punk", followers=9_000_000, popularity=88),  # no bio
        tracks=(_track("One More Time", "Daft Punk", isrc="USONE0000011"),),
    )
    deezer_artist = ResolvedEntity(
        provider=ProviderId.DEEZER,
        provider_id="dzartist",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Daft Punk", followers=1_000, bio="French electronic duo"),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    deezer = FakeMetadataProvider(
        id=ProviderId.DEEZER,
        hits=[
            SearchHit(
                entity_type=EntityType.ARTIST,
                provider=ProviderId.DEEZER,
                provider_id="dzartist",
                name="Daft Punk",
            )
        ],
        resolved={EntityType.ARTIST: deezer_artist},
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    assert result.artist.followers == 9_000_000  # Spotify-first display wins
    assert result.artist.bio == "French electronic duo"  # Deezer-only field fills the gap
    assert await _linked_providers(session, EntityType.ARTIST, result.artist.id) == {
        "spotify",
        "deezer",
    }
