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
from spotdl_core.providers.metadata.lastfm import (
    LastfmArtistInfo,
    LastfmProvider,
    LastfmTrackInfo,
)
from spotdl_server.repositories.snapshots import SnapshotRepository
from spotdl_server.repositories.stats import EntityStatRepository
from spotdl_server.services.resolve import ResolveService
from sqlalchemy.ext.asyncio import AsyncSession

from apps.server.tests.fakes import (
    FakeMetadataProvider,
    FakeResolver,
    build_fake_registry,
)


class FakeLastfm(LastfmProvider):
    """A Last.fm provider returning canned name-keyed info (no HTTP).

    Subclasses :class:`LastfmProvider` so the resolve layer's ``isinstance`` gate
    accepts it; the two info methods are overridden to serve fixtures and record
    calls. ``__init__`` deliberately skips ``super().__init__`` (there is no client).
    """

    def __init__(
        self,
        *,
        artist: LastfmArtistInfo | None = None,
        track: LastfmTrackInfo | None = None,
        error: Exception | None = None,
    ) -> None:
        self.id = ProviderId.LASTFM
        self._artist = artist
        self._track = track
        self._error = error
        self.artist_calls: list[str] = []
        self.track_calls: list[tuple[str, str]] = []

    async def artist_info(self, name: str) -> LastfmArtistInfo | None:
        self.artist_calls.append(name)
        if self._error is not None:
            raise self._error
        return self._artist

    async def track_info(self, artist: str, track: str) -> LastfmTrackInfo | None:
        self.track_calls.append((artist, track))
        if self._error is not None:
            raise self._error
        return self._track


async def _entity_stats(
    session: AsyncSession, entity_type: EntityType, id: str
) -> set[tuple[str, str, int]]:
    rows = await EntityStatRepository(session).list_for_entity(entity_type, uuid.UUID(id))
    return {(row.provider.value, row.metric, row.value) for row in rows}


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
        "Totally Different",
        "Someone Else",
        isrc="GBXYZ9999999",
        provider=ProviderId.DEEZER,
        provider_id="dz9",
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


def _artist_source(
    provider: ProviderId, provider_id: str, name: str, tracks: tuple[Track, ...]
) -> FakeMetadataProvider:
    """A secondary metadata source whose artist search resolves to ``tracks``."""
    return FakeMetadataProvider(
        id=provider,
        hits=[
            SearchHit(
                entity_type=EntityType.ARTIST,
                provider=provider,
                provider_id=provider_id,
                name=name,
            )
        ],
        resolved={
            EntityType.ARTIST: ResolvedEntity(
                provider=provider,
                provider_id=provider_id,
                entity_type=EntityType.ARTIST,
                artist=ArtistRef(name=name, followers=1_000),
                tracks=tracks,
            )
        },
    )


async def test_artist_top_tracks_dedup_differing_isrc(session: AsyncSession) -> None:
    # Spotify and Deezer both list "ECHO", but Deezer's copy is a different
    # pressing (different ISRC). The union must keep ONE ECHO (the primary's) and
    # still append Deezer's genuinely exclusive track. The bug: the differing ISRC
    # slipped past the name dedupe because the primary seeded only its ISRC, so
    # ECHO was listed twice (each with its own provider's artwork/id).
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata", followers=500_000),
        tracks=(
            _track("ECHO", "Mata", isrc="PLA010000001"),
            _track("Kiss cam", "Mata", isrc="PLA010000002"),
        ),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    deezer = _artist_source(
        ProviderId.DEEZER,
        "dzartist",
        "Mata",
        (
            _track("ECHO", "Mata", isrc="PLA019999999"),  # same song, other pressing
            _track("Fantastine", "Mata", isrc="PLA010000003"),  # Deezer-exclusive
        ),
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    names = [t.name for t in result.artist.tracks]
    assert names.count("ECHO") == 1  # deduped despite the differing ISRC
    assert sorted(names) == ["ECHO", "Fantastine", "Kiss cam"]
    # Rank stability: the primary's listing leads, the secondary-exclusive follows.
    assert names == ["ECHO", "Kiss cam", "Fantastine"]


async def test_artist_top_tracks_dedup_same_title_no_isrc(session: AsyncSession) -> None:
    # Deezer's duplicate carries NO ISRC → dedupe falls back to the case-folded
    # title (the casing even differs), so the same recording is not listed twice.
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata", followers=500_000),
        tracks=(_track("ECHO", "Mata", isrc="PLA010000001"),),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    deezer = _artist_source(
        ProviderId.DEEZER,
        "dzartist",
        "Mata",
        (
            _track("echo", "Mata", isrc=None),  # same song, no ISRC, different casing
            _track("Kiss cam", "Mata", isrc=None),  # Deezer-exclusive
        ),
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    names = [t.name for t in result.artist.tracks]
    assert [n.casefold() for n in names].count("echo") == 1  # name-fallback dedupe
    assert names == ["ECHO", "Kiss cam"]


async def test_artist_top_tracks_dedup_same_isrc(session: AsyncSession) -> None:
    # Both providers agree on the ISRC → the classic ISRC dedupe keeps one copy.
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata", followers=500_000),
        tracks=(_track("ECHO", "Mata", isrc="PLA010000001"),),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    deezer = _artist_source(
        ProviderId.DEEZER,
        "dzartist",
        "Mata",
        (_track("ECHO", "Mata", isrc="PLA010000001"),),  # identical ISRC
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    assert [t.name for t in result.artist.tracks] == ["ECHO"]


# --------------------------------------------------------------------------
# Phase 4 — Last.fm name-keyed enrichment + entity_stat recording
# --------------------------------------------------------------------------


async def test_lastfm_fills_artist_bio_and_adds_source(session: AsyncSession) -> None:
    # Spotify carries followers/popularity but NO bio and NO genres; Last.fm
    # (name-matched) fills the bio + genres and adds a lastfm metadata source.
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Daft Punk", followers=9_000_000, popularity=88),
        tracks=(_track("One More Time", "Daft Punk", isrc="USONE0000011"),),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    lastfm = FakeLastfm(
        artist=LastfmArtistInfo(
            name="Daft Punk",
            listeners=5_000_000,
            playcount=88_000_000,
            bio="French electronic duo",
            genres=("electronic", "house"),
        )
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, lastfm))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    assert result.artist.followers == 9_000_000  # Spotify-first display still wins
    assert result.artist.bio == "French electronic duo"  # Last.fm fills the empty bio
    assert tuple(result.artist.genres) == ("electronic", "house")  # Last.fm fills genres
    assert lastfm.artist_calls == ["Daft Punk"]
    # Last.fm appears as a metadata source alongside Spotify.
    assert await _linked_providers(session, EntityType.ARTIST, result.artist.id) == {
        "spotify",
        "lastfm",
    }
    assert result.degraded_sources == ()
    # entity_stat captured Spotify followers/popularity + Last.fm listeners/playcount.
    assert await _entity_stats(session, EntityType.ARTIST, result.artist.id) == {
        ("spotify", "followers", 9_000_000),
        ("spotify", "popularity", 88),
        ("lastfm", "listeners", 5_000_000),
        ("lastfm", "playcount", 88_000_000),
    }


async def test_lastfm_wrong_artist_bio_is_rejected(session: AsyncSession) -> None:
    # Last.fm returns a DIFFERENT artist (autocorrect gone wrong) → normalized-name
    # mismatch rejects it: no bio, no lastfm source, no error.
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Daft Punk", followers=9_000_000),
        tracks=(),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    lastfm = FakeLastfm(artist=LastfmArtistInfo(name="Some Other Band", bio="Not Daft Punk at all"))
    service = ResolveService(session=session, registry=build_fake_registry(spotify, lastfm))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    assert result.artist.bio is None  # wrong-artist bio not trusted
    assert await _linked_providers(session, EntityType.ARTIST, result.artist.id) == {"spotify"}
    assert result.degraded_sources == ()  # a name mismatch is a miss, not an error


async def test_lastfm_failure_degrades_not_fatal(session: AsyncSession) -> None:
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Daft Punk", followers=9_000_000),
        tracks=(),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    lastfm = FakeLastfm(error=ProviderUnavailable("lastfm down", provider=ProviderId.LASTFM))
    service = ResolveService(session=session, registry=build_fake_registry(spotify, lastfm))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None  # primary still succeeds
    assert ProviderId.LASTFM.value in result.degraded_sources
    assert await _linked_providers(session, EntityType.ARTIST, result.artist.id) == {"spotify"}


async def test_track_resolve_records_stats(session: AsyncSession) -> None:
    # A Spotify track with a popularity + a name-matched Last.fm track → entity_stat
    # captures Spotify popularity and Last.fm listeners/playcount; Last.fm is a source.
    spotify_track = Track(
        name="Hello",
        artists=("Adele",),
        duration_ms=200_000,
        isrc=ISRC,
        popularity=80,
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, track=spotify_track)
    lastfm = FakeLastfm(
        track=LastfmTrackInfo(
            name="Hello", artist="Adele", listeners=1_234_567, playcount=9_876_543
        )
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, lastfm))

    result = await service.resolve(SPOTIFY_TRACK_URL)

    assert result.track is not None
    assert lastfm.track_calls == [("Adele", "Hello")]
    assert await _linked_providers(session, EntityType.TRACK, result.track.id) == {
        "spotify",
        "lastfm",
    }
    assert await _entity_stats(session, EntityType.TRACK, result.track.id) == {
        ("spotify", "popularity", 80),
        ("lastfm", "listeners", 1_234_567),
        ("lastfm", "playcount", 9_876_543),
    }


async def test_artist_enrichment_rejects_same_named_stranger(session: AsyncSession) -> None:
    """A same-named artist with NO content overlap must never contribute data.

    Regression (found live via Mata — four artists named "Mata" on Deezer): the
    name-equality gate alone trusted whichever hit came first, polluting the
    canonical artist and /sources with a stranger's followers and discography.
    """
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata", followers=2_700_000),
        tracks=(_track("KAMIKAZE", "Mata", isrc="USKAM0000001"),),
        albums=(AlbumRef(name="Młody Matczak", provider=ProviderId.SPOTIFY, provider_id="sp-al1"),),
    )
    stranger = ResolvedEntity(
        provider=ProviderId.DEEZER,
        provider_id="dz-stranger",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata", followers=11_589, bio="someone else entirely"),
        tracks=(_track("Bonita", "Mata", isrc="FRSTR0000001"),),
        albums=(AlbumRef(name="Surface", provider=ProviderId.DEEZER, provider_id="dz-al9"),),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    deezer = FakeMetadataProvider(
        id=ProviderId.DEEZER,
        hits=[
            SearchHit(
                entity_type=EntityType.ARTIST,
                provider=ProviderId.DEEZER,
                provider_id="dz-stranger",
                name="Mata",
            )
        ],
        resolved={EntityType.ARTIST: stranger},
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    assert result.artist.bio is None  # the stranger's bio was never trusted
    assert await _linked_providers(session, EntityType.ARTIST, result.artist.id) == {"spotify"}
    assert [a.name for a in result.artist.albums] == ["Młody Matczak"]  # no pollution


async def test_artist_enrichment_unions_confirmed_secondary_discography(
    session: AsyncSession,
) -> None:
    """A content-confirmed secondary's exclusive releases join the discography.

    The artist's discography is the union across all sources: a shared album name
    confirms identity (and dedupes), and a provider-exclusive release appears.
    """
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata", followers=2_700_000),
        tracks=(_track("KAMIKAZE", "Mata", isrc="USKAM0000001"),),
        albums=(AlbumRef(name="Młody Matczak", provider=ProviderId.SPOTIFY, provider_id="sp-al1"),),
    )
    real_deezer = ResolvedEntity(
        provider=ProviderId.DEEZER,
        provider_id="dz-real",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata", followers=1_401),
        albums=(
            AlbumRef(name="Młody Matczak", provider=ProviderId.DEEZER, provider_id="dz-al1"),
            AlbumRef(name="Deezer Exclusive EP", provider=ProviderId.DEEZER, provider_id="dz-al2"),
        ),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    deezer = FakeMetadataProvider(
        id=ProviderId.DEEZER,
        hits=[
            SearchHit(
                entity_type=EntityType.ARTIST,
                provider=ProviderId.DEEZER,
                provider_id="dz-real",
                name="Mata",
            )
        ],
        resolved={EntityType.ARTIST: real_deezer},
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    names = [a.name for a in result.artist.albums]
    assert names == ["Młody Matczak", "Deezer Exclusive EP"]  # union, deduped by name
    assert await _linked_providers(session, EntityType.ARTIST, result.artist.id) == {
        "spotify",
        "deezer",
    }


def _artist_candidate(
    provider: ProviderId, provider_id: str, exclusive_album: str, exclusive_id: str
) -> FakeMetadataProvider:
    """A secondary artist source sharing "Shared Album" (confirms overlap) + one exclusive."""
    artist = ResolvedEntity(
        provider=provider,
        provider_id=provider_id,
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Daft Punk", followers=1_000),
        albums=(
            AlbumRef(name="Shared Album", provider=provider, provider_id=f"{provider_id}-shared"),
            AlbumRef(name=exclusive_album, provider=provider, provider_id=exclusive_id),
        ),
    )
    return FakeMetadataProvider(
        id=provider,
        hits=[
            SearchHit(
                entity_type=EntityType.ARTIST,
                provider=provider,
                provider_id=provider_id,
                name="Daft Punk",
            )
        ],
        resolved={EntityType.ARTIST: artist},
    )


async def test_artist_enrichment_unions_all_four_metadata_sources(session: AsyncSession) -> None:
    """Spotify primary + Deezer/iTunes/MusicBrainz candidates → 4 linked sources.

    Every content-confirmed secondary contributes to the discography union: the
    shared album dedupes to one entry while each provider-exclusive release joins,
    including an iTunes-only and a MusicBrainz-only album.
    """
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Daft Punk", followers=9_000_000),
        tracks=(),
        albums=(
            AlbumRef(name="Shared Album", provider=ProviderId.SPOTIFY, provider_id="sp-shared"),
        ),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    deezer = _artist_candidate(ProviderId.DEEZER, "dz-real", "Deezer Exclusive", "dz-excl")
    itunes = _artist_candidate(ProviderId.ITUNES, "it-real", "iTunes Exclusive", "it-excl")
    musicbrainz = _artist_candidate(
        ProviderId.MUSICBRAINZ, "mb-real", "MusicBrainz Exclusive", "mb-excl"
    )
    service = ResolveService(
        session=session, registry=build_fake_registry(spotify, deezer, itunes, musicbrainz)
    )

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    assert result.artist.followers == 9_000_000  # Spotify-first display wins
    # All four metadata sources are linked to the one canonical artist.
    assert await _linked_providers(session, EntityType.ARTIST, result.artist.id) == {
        "spotify",
        "deezer",
        "itunes",
        "musicbrainz",
    }
    names = [album.name for album in result.artist.albums]
    assert names == [
        "Shared Album",  # deduped across all four sources
        "Deezer Exclusive",
        "iTunes Exclusive",
        "MusicBrainz Exclusive",  # the MB-only release still appears
    ]
    assert result.degraded_sources == ()


async def test_artist_enrichment_rejects_itunes_stranger(session: AsyncSession) -> None:
    """A same-named iTunes artist with NO content overlap contributes nothing.

    The overlap gate is provider-agnostic, so the new iTunes source is held to the
    same identity check as Deezer: a stranger is never linked or merged.
    """
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata", followers=2_700_000),
        albums=(AlbumRef(name="Młody Matczak", provider=ProviderId.SPOTIFY, provider_id="sp-al1"),),
    )
    stranger = ResolvedEntity(
        provider=ProviderId.ITUNES,
        provider_id="it-stranger",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata", followers=42),
        albums=(
            AlbumRef(name="Unrelated Record", provider=ProviderId.ITUNES, provider_id="it-al9"),
        ),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    itunes = FakeMetadataProvider(
        id=ProviderId.ITUNES,
        hits=[
            SearchHit(
                entity_type=EntityType.ARTIST,
                provider=ProviderId.ITUNES,
                provider_id="it-stranger",
                name="Mata",
            )
        ],
        resolved={EntityType.ARTIST: stranger},
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, itunes))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    assert await _linked_providers(session, EntityType.ARTIST, result.artist.id) == {"spotify"}
    assert [a.name for a in result.artist.albums] == ["Młody Matczak"]  # no pollution


async def test_listing_preview_does_not_starve_track_enrichment(session: AsyncSession) -> None:
    """A track first seen via a container listing must still enrich on direct open.

    Regression (found live via Runaway): the artist top-tracks listing persisted a
    full-looking snapshot, so the track's later direct resolve cache-hit it and
    skipped the cross-provider fan-out — leaving the track single-source forever.
    Listing rows are previews (marked partial): the first direct open performs the
    authoritative fetch AND the enrichment.
    """
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Kanye West"),
        tracks=(
            _track(
                "Runaway",
                "Kanye West",
                isrc="USUM71027402",
                provider=ProviderId.SPOTIFY,
                provider_id="sp-run",
            ),
        ),
    )
    full_track = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="sp-run",
        entity_type=EntityType.TRACK,
        track=_track("Runaway", "Kanye West", isrc="USUM71027402"),
    )
    deezer_track = ResolvedEntity(
        provider=ProviderId.DEEZER,
        provider_id="dz-run",
        entity_type=EntityType.TRACK,
        track=_track(
            "Runaway",
            "Kanye West",
            isrc="USUM71027402",
            provider=ProviderId.DEEZER,
            provider_id="dz-run",
        ),
    )

    class _Spotify(FakeResolver):
        async def resolve(self, ref):  # type: ignore[override]
            self.calls.append(ref)
            return spotify_artist if ref.entity_type is EntityType.ARTIST else full_track

    spotify = _Spotify(id=ProviderId.SPOTIFY)
    deezer = FakeMetadataProvider(
        id=ProviderId.DEEZER,
        tracks=[deezer_track.track],
        resolved={EntityType.TRACK: deezer_track},
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    await service.resolve(SPOTIFY_ARTIST_URL)  # listing persists a preview snapshot
    track_calls_before = sum(1 for c in spotify.calls if c.entity_type is EntityType.TRACK)

    result = await service.resolve("spotify:track:sp-run")

    track_calls_after = sum(1 for c in spotify.calls if c.entity_type is EntityType.TRACK)
    assert track_calls_after == track_calls_before + 1  # preview did NOT satisfy the resolve
    assert result.track is not None
    assert await _linked_providers(session, EntityType.TRACK, result.track.id) == {
        "spotify",
        "deezer",
    }


async def test_artist_top_tracks_union_across_confirmed_sources(session: AsyncSession) -> None:
    """A confirmed secondary's exclusive top tracks join the artist listing."""
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata"),
        tracks=(_track("KAMIKAZE", "Mata", isrc="USKAM0000001"),),
    )
    real_deezer = ResolvedEntity(
        provider=ProviderId.DEEZER,
        provider_id="dz-real",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Mata"),
        tracks=(
            _track("KAMIKAZE", "Mata", isrc="USKAM0000001"),  # shared → confirms + dedupes
            _track(
                "Deezer Only Song",
                "Mata",
                isrc="FRDZ00000001",
                provider=ProviderId.DEEZER,
                provider_id="dz-t2",
            ),
        ),
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    deezer = FakeMetadataProvider(
        id=ProviderId.DEEZER,
        hits=[
            SearchHit(
                entity_type=EntityType.ARTIST,
                provider=ProviderId.DEEZER,
                provider_id="dz-real",
                name="Mata",
            )
        ],
        resolved={EntityType.ARTIST: real_deezer},
    )
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    names = [t.name for t in result.artist.tracks]
    assert names == ["KAMIKAZE", "Deezer Only Song"]  # union, deduped by ISRC/name


async def test_renamed_artist_confirmed_by_strict_overlap(session: AsyncSession) -> None:
    """A provider's canonical RENAME still enriches when content proves identity.

    Regression (found live): MusicBrainz lists Kanye West as "Ye", so the
    name-equality gate rejected the correct artist and MB never contributed. A
    non-name-matching top hit is now resolved and accepted ONLY when its content
    overlaps the primary's (strict gate — no lenient no-content fallback).
    """
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Kanye West"),
        tracks=(),
        albums=(AlbumRef(name="Graduation", provider=ProviderId.SPOTIFY, provider_id="sp-al1"),),
    )
    ye = ResolvedEntity(
        provider=ProviderId.DEEZER,
        provider_id="dz-ye",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Ye", genres=("hip hop",)),
        albums=(AlbumRef(name="Graduation", provider=ProviderId.DEEZER, provider_id="dz-al1"),),
    )
    deezer = FakeMetadataProvider(
        id=ProviderId.DEEZER,
        hits=[
            SearchHit(
                entity_type=EntityType.ARTIST,
                provider=ProviderId.DEEZER,
                provider_id="dz-ye",
                name="Ye",  # canonical rename — does NOT normalize-equal the query
            )
        ],
        resolved={EntityType.ARTIST: ye},
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    assert await _linked_providers(session, EntityType.ARTIST, result.artist.id) == {
        "spotify",
        "deezer",
    }


async def test_non_matching_hit_without_overlap_is_rejected(session: AsyncSession) -> None:
    """A non-name-matching top hit with NO shared content must never be trusted
    (the strict gate has no lenient fallback — a tribute band named differently
    with a disjoint catalogue contributes nothing)."""
    spotify_artist = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="artist123",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Kanye West"),
        tracks=(),
        albums=(AlbumRef(name="Graduation", provider=ProviderId.SPOTIFY, provider_id="sp-al1"),),
    )
    tribute = ResolvedEntity(
        provider=ProviderId.DEEZER,
        provider_id="dz-trib",
        entity_type=EntityType.ARTIST,
        artist=ArtistRef(name="Kanye West Tribute Band"),
        albums=(AlbumRef(name="Karaoke Hits", provider=ProviderId.DEEZER, provider_id="dz-k1"),),
    )
    deezer = FakeMetadataProvider(
        id=ProviderId.DEEZER,
        hits=[
            SearchHit(
                entity_type=EntityType.ARTIST,
                provider=ProviderId.DEEZER,
                provider_id="dz-trib",
                name="Kanye West Tribute Band",
            )
        ],
        resolved={EntityType.ARTIST: tribute},
    )
    spotify = FakeResolver(id=ProviderId.SPOTIFY, entity=spotify_artist)
    service = ResolveService(session=session, registry=build_fake_registry(spotify, deezer))

    result = await service.resolve(SPOTIFY_ARTIST_URL)

    assert result.artist is not None
    assert await _linked_providers(session, EntityType.ARTIST, result.artist.id) == {"spotify"}
    assert [a.name for a in result.artist.albums] == ["Graduation"]  # no pollution
