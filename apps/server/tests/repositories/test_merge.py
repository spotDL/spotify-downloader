"""Offline (in-memory SQLite) tests for the deterministic canonical merger.

The merger consumes ``ProviderSnapshot`` rows and produces canonical entities by
the source-priority-per-field-class contract (spec §6.1). Snapshots here store
their structured metadata as a normalized ``Track``/``AlbumRef``-shaped dict in
``raw_payload`` (plus the repository's normalized key columns) — the convention
the merger reads from. See ``merge.py``'s module docstring.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any

from spotdl_core.model import EntityType, ProviderId
from spotdl_server.db.base import Base
from spotdl_server.db.models import Album, Artist, EntityLink, ProviderSnapshot, Track
from spotdl_server.repositories.merge import SOURCE_PRIORITY, CanonicalMerger
from spotdl_server.repositories.snapshots import SnapshotRepository
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@asynccontextmanager
async def _fresh_session() -> AsyncIterator[AsyncSession]:
    """An independent in-memory SQLite session (own DB) for order-independence
    tests that must merge the same snapshot set into two separate databases."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_fk(dbapi_conn: Any, _record: Any) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db_session:
        try:
            yield db_session
        finally:
            await db_session.rollback()
    await engine.dispose()


async def _track_snapshot(
    session: AsyncSession,
    provider: ProviderId,
    provider_entity_id: str,
    *,
    name: str | None = None,
    isrc: str | None = None,
    duration_ms: int | None = None,
    artists: Sequence[str] | None = None,
    album: dict[str, Any] | None = None,
    cover_url: str | None = None,
    explicit: bool | None = None,
    track_number: int | None = None,
    disc_number: int | None = None,
    year: int | None = None,
    genres: Sequence[str] | None = None,
    popularity: int | None = None,
    date: str | None = None,
    publisher: str | None = None,
    copyright_text: str | None = None,
) -> ProviderSnapshot:
    payload: dict[str, Any] = {
        "name": name,
        "duration_ms": duration_ms,
        "isrc": isrc,
        "artists": list(artists) if artists else None,
        "album": album,
        "cover_url": cover_url,
        "explicit": explicit,
        "track_number": track_number,
        "disc_number": disc_number,
        "year": year,
        "genres": list(genres) if genres else [],
        "popularity": popularity,
        "date": date,
        "publisher": publisher,
        "copyright_text": copyright_text,
    }
    return await SnapshotRepository(session).upsert(
        provider=provider,
        provider_entity_id=provider_entity_id,
        entity_type=EntityType.TRACK,
        raw_payload=payload,
        name=name,
        isrc=isrc,
        duration_ms=duration_ms,
        artist_names=list(artists) if artists else None,
        album_name=album["name"] if album else None,
        art_url=cover_url,
    )


async def _count(session: AsyncSession, model: type[Any]) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


# --------------------------------------------------------------------------- #
# source-priority per field class
# --------------------------------------------------------------------------- #
def test_source_priority_order_is_the_contract() -> None:
    assert SOURCE_PRIORITY == (
        ProviderId.SPOTIFY,
        ProviderId.DEEZER,
        ProviderId.ITUNES,
        ProviderId.MUSICBRAINZ,
    )


async def test_priority_prefers_spotify_name(session: AsyncSession) -> None:
    spotify = await _track_snapshot(
        session, ProviderId.SPOTIFY, "s1", name="Spotify Name", artists=["A"]
    )
    deezer = await _track_snapshot(
        session, ProviderId.DEEZER, "d1", name="Deezer Name", artists=["A"]
    )
    track = await CanonicalMerger(session).merge_track([spotify, deezer])
    assert track.name == "Spotify Name"


async def test_isrc_falls_through_to_deezer_when_spotify_missing(session: AsyncSession) -> None:
    spotify = await _track_snapshot(
        session, ProviderId.SPOTIFY, "s1", name="Song", artists=["A"], isrc=None
    )
    deezer = await _track_snapshot(
        session, ProviderId.DEEZER, "d1", name="Song", artists=["A"], isrc="DEEZER0000001"
    )
    track = await CanonicalMerger(session).merge_track([spotify, deezer])
    assert track.isrc == "DEEZER0000001"


async def test_genres_first_nonempty(session: AsyncSession) -> None:
    spotify = await _track_snapshot(
        session, ProviderId.SPOTIFY, "s1", name="Song", artists=["A"], genres=[]
    )
    musicbrainz = await _track_snapshot(
        session,
        ProviderId.MUSICBRAINZ,
        "m1",
        name="Song",
        artists=["A"],
        genres=["rock", "pop"],
    )
    track = await CanonicalMerger(session).merge_track([spotify, musicbrainz])
    assert list(track.genres) == ["rock", "pop"]


async def test_track_metadata_fields_merge_spotify_first(session: AsyncSession) -> None:
    # Spotify wins each new canonical field; a lower-priority source only fills a
    # gap the higher-priority snapshot leaves ``None`` (``copyright_text`` here).
    spotify = await _track_snapshot(
        session,
        ProviderId.SPOTIFY,
        "s1",
        name="Song",
        artists=["A"],
        isrc="META00000001",
        date="2001-03-12",
        publisher="Virgin",
        copyright_text=None,
    )
    deezer = await _track_snapshot(
        session,
        ProviderId.DEEZER,
        "d1",
        name="Song",
        artists=["A"],
        isrc="META00000001",
        date="1999-01-01",
        publisher="Deezer Label",
        copyright_text="© 2001 Deezer",
    )
    track = await CanonicalMerger(session).merge_track([spotify, deezer])
    assert track.date == "2001-03-12"
    assert track.publisher == "Virgin"
    assert track.copyright_text == "© 2001 Deezer"


def _track_fields(track: Track) -> tuple[Any, ...]:
    return (
        track.name,
        track.duration_ms,
        track.isrc,
        track.explicit,
        track.track_number,
        track.disc_number,
        track.year,
        tuple(track.genres),
        track.popularity,
        tuple(a.name for a in track.artists),
        track.album.name if track.album else None,
    )


async def test_merge_is_order_independent() -> None:
    async def _merge(order: list[str]) -> tuple[Any, ...]:
        async with _fresh_session() as session:
            spotify = await _track_snapshot(
                session,
                ProviderId.SPOTIFY,
                "s1",
                name="Spotify Name",
                artists=["Main", "Feat"],
                duration_ms=210000,
                isrc="SPOT00000001",
                explicit=True,
                track_number=3,
                disc_number=1,
                year=2001,
                genres=["house"],
                popularity=77,
                album={"name": "Discovery", "year": 2001},
                cover_url="https://img/spot.jpg",
            )
            deezer = await _track_snapshot(
                session,
                ProviderId.DEEZER,
                "d1",
                name="Deezer Name",
                artists=["Other"],
                duration_ms=209000,
                isrc="DEEZ00000001",
                genres=["electro"],
                album={"name": "Deezer Album"},
            )
            by_id = {"spotify": spotify, "deezer": deezer}
            merged = await CanonicalMerger(session).merge_track([by_id[k] for k in order])
            fetched = await CanonicalMerger(session)._tracks.get(merged.id)
            assert fetched is not None
            return _track_fields(fetched)

    forward = await _merge(["deezer", "spotify"])
    reverse = await _merge(["spotify", "deezer"])
    assert forward == reverse


async def test_merge_is_rerunnable(session: AsyncSession) -> None:
    spotify = await _track_snapshot(
        session, ProviderId.SPOTIFY, "s1", name="Song", artists=["A"], isrc="ISRC00000001"
    )
    deezer = await _track_snapshot(
        session, ProviderId.DEEZER, "d1", name="Song", artists=["A"], isrc="ISRC00000001"
    )
    merger = CanonicalMerger(session)

    first = await merger.merge_track([spotify, deezer])
    fields_first = _track_fields(await merger._tracks.get(first.id))  # type: ignore[arg-type]
    assert await _count(session, Track) == 1
    assert await _count(session, EntityLink) == 2

    second = await merger.merge_track([spotify, deezer])
    assert second.id == first.id
    assert await _count(session, Track) == 1
    assert await _count(session, EntityLink) == 2
    fields_second = _track_fields(await merger._tracks.get(second.id))  # type: ignore[arg-type]
    assert fields_first == fields_second


async def test_merge_dedupes_by_isrc(session: AsyncSession) -> None:
    spotify = await _track_snapshot(
        session, ProviderId.SPOTIFY, "s1", name="Song", artists=["A"], isrc="DUPE00000001"
    )
    deezer = await _track_snapshot(
        session, ProviderId.DEEZER, "d1", name="Song", artists=["A"], isrc="DUPE00000001"
    )
    track = await CanonicalMerger(session).merge_track([spotify, deezer])
    assert await _count(session, Track) == 1

    links = await session.execute(
        select(EntityLink).where(
            EntityLink.entity_type == EntityType.TRACK,
            EntityLink.entity_id == track.id,
        )
    )
    assert {link.snapshot_id for link in links.scalars()} == {spotify.id, deezer.id}


async def test_duration_unit_trust(session: AsyncSession) -> None:
    # Providers normalize durations to ms (Plan 2). The merger must not re-scale.
    deezer = await _track_snapshot(
        session, ProviderId.DEEZER, "d1", name="Song", artists=["A"], duration_ms=200000
    )
    track = await CanonicalMerger(session).merge_track([deezer])
    assert track.duration_ms == 200000


async def test_merge_resolves_artists_by_normalized_name(session: AsyncSession) -> None:
    spotify = await _track_snapshot(
        session,
        ProviderId.SPOTIFY,
        "s1",
        name="Get Lucky",
        artists=["Daft Punk", "Pharrell Williams"],
        isrc="GETLUCKY0001",
    )
    merger = CanonicalMerger(session)
    track = await merger.merge_track([spotify])

    fetched = await merger._tracks.get(track.id)
    assert fetched is not None
    assert [a.name for a in fetched.artists] == ["Daft Punk", "Pharrell Williams"]
    assert await _count(session, Artist) == 2

    # Re-merge with a lower-priority Deezer snapshot whose artist names differ
    # only in case/whitespace: no new artist rows are created.
    deezer = await _track_snapshot(
        session,
        ProviderId.DEEZER,
        "d1",
        name="Get Lucky",
        artists=["daft punk", "  pharrell   williams "],
        isrc="GETLUCKY0001",
    )
    await merger.merge_track([spotify, deezer])
    assert await _count(session, Artist) == 2


async def test_merge_artist_set_single_source_ordered(session: AsyncSession) -> None:
    musicbrainz = await _track_snapshot(
        session,
        ProviderId.MUSICBRAINZ,
        "m1",
        name="Song",
        artists=["MB One", "MB Two", "MB Three"],
    )
    merger = CanonicalMerger(session)
    track = await merger.merge_track([musicbrainz])
    fetched = await merger._tracks.get(track.id)
    assert fetched is not None
    assert [a.name for a in fetched.artists] == ["MB One", "MB Two", "MB Three"]

    # A higher-priority Spotify source appears with a different (shorter) artist
    # set. The winner is the single highest-priority snapshot's ordered tuple; the
    # M2M is fully replaced (no stale link rows from MusicBrainz's three).
    spotify = await _track_snapshot(
        session,
        ProviderId.SPOTIFY,
        "s1",
        name="Song",
        artists=["Sp One", "Sp Two"],
    )
    same = await merger.merge_track([spotify, musicbrainz])
    assert same.id == track.id
    fetched = await merger._tracks.get(track.id)
    assert fetched is not None
    assert [a.name for a in fetched.artists] == ["Sp One", "Sp Two"]

    from spotdl_server.db.models import track_artists

    link_rows = await session.execute(
        select(func.count()).select_from(track_artists).where(track_artists.c.track_id == track.id)
    )
    assert int(link_rows.scalar_one()) == 2


# --------------------------------------------------------------------------- #
# album / artist / playlist merge (same rule set)
# --------------------------------------------------------------------------- #
async def test_merge_artist_direct_resolve_by_normalized_name(session: AsyncSession) -> None:
    def _artist_snap(
        session: AsyncSession,
        provider: ProviderId,
        pid: str,
        name: str,
        genres: list[str],
        image_url: str | None,
    ) -> Any:
        return SnapshotRepository(session).upsert(
            provider=provider,
            provider_entity_id=pid,
            entity_type=EntityType.ARTIST,
            raw_payload={"name": name, "genres": genres, "image_url": image_url},
            name=name,
        )

    spotify = await _artist_snap(
        session, ProviderId.SPOTIFY, "s1", "Daft Punk", ["french house"], "https://img/dp.jpg"
    )
    deezer = await _artist_snap(session, ProviderId.DEEZER, "d1", "daft punk", [], None)

    merger = CanonicalMerger(session)
    artist = await merger.merge_artist([spotify, deezer])
    assert artist.name == "Daft Punk"
    assert artist.normalized_name == "daft punk"
    assert list(artist.genres) == ["french house"]
    assert artist.image_url == "https://img/dp.jpg"
    assert await _count(session, Artist) == 1

    # Re-run converges: still one row, one link per snapshot.
    again = await merger.merge_artist([spotify, deezer])
    assert again.id == artist.id
    assert await _count(session, Artist) == 1
    links = await session.execute(
        select(func.count())
        .select_from(EntityLink)
        .where(EntityLink.entity_type == EntityType.ARTIST)
    )
    assert int(links.scalar_one()) == 2


async def test_merge_album_builds_ordered_tracks(session: AsyncSession) -> None:
    album_snap = await SnapshotRepository(session).upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="alb1",
        entity_type=EntityType.ALBUM,
        raw_payload={
            "name": "Discovery",
            "album_artist": "Daft Punk",
            "year": 2001,
            "track_count": 2,
            "cover_url": "https://img/disc.jpg",
        },
        name="Discovery",
    )
    t0 = await _track_snapshot(
        session, ProviderId.SPOTIFY, "t0", name="One More Time", artists=["Daft Punk"]
    )
    t1 = await _track_snapshot(
        session, ProviderId.SPOTIFY, "t1", name="Aerodynamic", artists=["Daft Punk"]
    )

    merger = CanonicalMerger(session)
    album = await merger.merge_album([album_snap], {0: [t0], 1: [t1]})
    assert album.name == "Discovery"
    assert album.album_artist == "Daft Punk"
    assert album.year == 2001
    assert album.track_count == 2

    fetched = await merger._albums.get(album.id)
    assert fetched is not None
    assert {t.name for t in fetched.tracks} == {"One More Time", "Aerodynamic"}
    assert all(t.album_id == album.id for t in fetched.tracks)


async def test_merge_album_rerunnable_when_tracks_embed_album(session: AsyncSession) -> None:
    # Member tracks carry their own (sparser) embedded ``album`` sub-object — a
    # real provider shape. ``merge_album`` must position them into the explicitly
    # merged album without the per-track embedded-album side channel creating
    # orphan Album rows or clobbering the merged album's fields on re-run.
    album_snap = await SnapshotRepository(session).upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="alb1",
        entity_type=EntityType.ALBUM,
        raw_payload={
            "name": "Discovery",
            "album_artist": "Daft Punk",
            "year": 2001,
            "track_count": 2,
            "cover_url": "https://img/disc.jpg",
        },
        name="Discovery",
    )
    embedded = {"name": "Discovery (track view)"}
    t0 = await _track_snapshot(
        session,
        ProviderId.SPOTIFY,
        "t0",
        name="One More Time",
        artists=["Daft Punk"],
        album=embedded,
    )
    t1 = await _track_snapshot(
        session,
        ProviderId.SPOTIFY,
        "t1",
        name="Aerodynamic",
        artists=["Daft Punk"],
        album=embedded,
    )

    merger = CanonicalMerger(session)

    def _album_fields(album: Any) -> tuple[Any, ...]:
        return (album.name, album.album_artist, album.year, album.track_count)

    first = await merger.merge_album([album_snap], {0: [t0], 1: [t1]})
    assert _album_fields(first) == ("Discovery", "Daft Punk", 2001, 2)
    # Exactly one Album row — no orphan created by the tracks' embedded album.
    assert await _count(session, Album) == 1

    second = await merger.merge_album([album_snap], {0: [t0], 1: [t1]})
    assert second.id == first.id
    # Identical inputs => identical fields (no clobber from the track's album view).
    assert _album_fields(second) == ("Discovery", "Daft Punk", 2001, 2)
    assert await _count(session, Album) == 1
    fetched = await merger._albums.get(second.id)
    assert fetched is not None
    assert {t.name for t in fetched.tracks} == {"One More Time", "Aerodynamic"}
    assert all(t.album_id == second.id for t in fetched.tracks)


async def test_merge_playlist_orders_tracks(session: AsyncSession) -> None:
    pl_snap = await SnapshotRepository(session).upsert(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="pl1",
        entity_type=EntityType.PLAYLIST,
        raw_payload={
            "name": "My Mix",
            "description": "the best",
            "owner": "kuba",
            "cover_url": "https://img/pl.jpg",
        },
        name="My Mix",
    )
    t0 = await _track_snapshot(session, ProviderId.SPOTIFY, "t0", name="First", artists=["A"])
    t1 = await _track_snapshot(session, ProviderId.SPOTIFY, "t1", name="Second", artists=["B"])

    merger = CanonicalMerger(session)
    playlist = await merger.merge_playlist([pl_snap], [[t1], [t0]])
    assert playlist.name == "My Mix"
    assert playlist.description == "the best"
    assert playlist.owner == "kuba"

    fetched = await merger._playlists.get(playlist.id)
    assert fetched is not None
    assert [t.name for t in fetched.tracks] == ["Second", "First"]


# --------------------------------------------------------------------------- #
# multi-provider metadata fields (Phase 1b) — Spotify-first per SOURCE_PRIORITY
# --------------------------------------------------------------------------- #
async def test_merge_artist_metadata_fields_spotify_first(session: AsyncSession) -> None:
    async def _artist_snap(
        provider: ProviderId, pid: str, **payload: Any
    ) -> ProviderSnapshot:
        return await SnapshotRepository(session).upsert(
            provider=provider,
            provider_entity_id=pid,
            entity_type=EntityType.ARTIST,
            raw_payload={"name": "Daft Punk", **payload},
            name="Daft Punk",
        )

    # Spotify carries popularity/followers/header_url but no bio/country; Deezer
    # (lower priority) fills those gaps and is overridden where Spotify has a value.
    spotify = await _artist_snap(
        ProviderId.SPOTIFY,
        "s1",
        popularity=88,
        followers=12_000_000,
        header_url="https://img/dp-hero.jpg",
    )
    deezer = await _artist_snap(
        ProviderId.DEEZER,
        "d1",
        popularity=70,
        followers=1,
        bio="French house duo.",
        country="FR",
        header_url="https://img/deezer-hero.jpg",
    )
    artist = await CanonicalMerger(session).merge_artist([spotify, deezer])
    assert artist.popularity == 88
    assert artist.followers == 12_000_000
    assert artist.header_url == "https://img/dp-hero.jpg"
    assert artist.bio == "French house duo."
    assert artist.country == "FR"


async def test_merge_album_metadata_fields_spotify_first(session: AsyncSession) -> None:
    async def _album_snap(
        provider: ProviderId, pid: str, **payload: Any
    ) -> ProviderSnapshot:
        return await SnapshotRepository(session).upsert(
            provider=provider,
            provider_entity_id=pid,
            entity_type=EntityType.ALBUM,
            raw_payload={"name": "Discovery", **payload},
            name="Discovery",
        )

    spotify = await _album_snap(
        ProviderId.SPOTIFY,
        "s1",
        label="Virgin",
        popularity=64,
        album_type="album",
        genres=["french house"],
    )
    deezer = await _album_snap(
        ProviderId.DEEZER,
        "d1",
        label="Deezer Label",
        popularity=10,
        copyright_text="© 2001 Virgin",
        album_type="compilation",
        genres=["electro"],
    )
    album = await CanonicalMerger(session).merge_album([spotify, deezer], {})
    assert album.label == "Virgin"
    assert album.popularity == 64
    assert album.album_type == "album"
    assert list(album.genres) == ["french house"]
    # Gap-fill from the lower-priority source where Spotify is silent.
    assert album.copyright_text == "© 2001 Virgin"
