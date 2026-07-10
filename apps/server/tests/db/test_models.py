"""The schema spec, mechanically enforced.

These tests ARE the §6.1 contract: they build every table into a fresh SQLite
engine and assert the exact column list, nullability, defaults, constraints,
indexes and relational behaviour. Any drift from the contract fails here.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from spotdl_core.model import EntityType, LyricsKind, MatchStatus, ProviderId
from spotdl_server.db.base import Base
from spotdl_server.db.enums import BatchKind, DownloadStatus, LinkStatus
from spotdl_server.db.models import (
    Album,
    Artist,
    DownloadBatch,
    DownloadJob,
    EntityLink,
    Lyrics,
    Match,
    Playlist,
    ProviderSnapshot,
    Track,
    playlist_tracks,
    track_artists,
)
from sqlalchemy import Column, Table, create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

EXPECTED_TABLES = {
    "provider_snapshots",
    "albums",
    "artists",
    "tracks",
    "playlists",
    "track_artists",
    "playlist_tracks",
    "artist_albums",
    "entity_links",
    "entity_stat",
    "matches",
    "lyrics",
    "download_batches",
    "download_jobs",
    # Plan 6 community layer (additive; NEVER an ALTER of the tables above).
    "users",
    "oauth_identities",
    "refresh_tokens",
    "api_tokens",
    "votes",
    "reports",
}


# --------------------------------------------------------------------------- #
# schema descriptor helpers
# --------------------------------------------------------------------------- #
def _default(col: Column[Any]) -> Any:
    d = col.default
    if d is None:
        return None
    if getattr(d, "is_scalar", False):
        return d.arg
    if getattr(d, "is_callable", False):
        return "callable"
    return repr(getattr(d, "arg", d))


def describe(table: Table) -> dict[str, tuple[str, int | None, bool, Any]]:
    """Map column name -> (type class name, length, nullable, scalar default)."""
    return {
        c.name: (
            type(c.type).__name__,
            getattr(c.type, "length", None),
            c.nullable,
            _default(c),
        )
        for c in table.columns
    }


def tbl(name: str) -> Table:
    return Base.metadata.tables[name]


# --------------------------------------------------------------------------- #
# engine fixture (FK enforcement on for SQLite)
# --------------------------------------------------------------------------- #
@pytest.fixture
def engine() -> Iterator[Engine]:
    eng = create_engine("sqlite://")

    @event.listens_for(eng, "connect")
    def _fk_on(dbapi_conn: Any, _rec: Any) -> None:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as s:
        yield s


# --------------------------------------------------------------------------- #
# table set
# --------------------------------------------------------------------------- #
def test_all_tables_present() -> None:
    assert set(Base.metadata.tables.keys()) == EXPECTED_TABLES


# --------------------------------------------------------------------------- #
# per-table column contracts
# --------------------------------------------------------------------------- #
def test_provider_snapshots_columns_and_unique() -> None:
    assert describe(tbl("provider_snapshots")) == {
        "id": ("Uuid", None, False, "callable"),
        "provider": ("Enum", 32, False, None),
        "provider_entity_id": ("String", 256, False, None),
        "entity_type": ("Enum", 32, False, None),
        "raw_payload": ("JSON", None, False, None),
        "name": ("String", 1024, True, None),
        "isrc": ("String", 32, True, None),
        "duration_ms": ("Integer", None, True, None),
        "artist_names": ("JSON", None, True, None),
        "album_name": ("String", 1024, True, None),
        "art_url": ("String", 2048, True, None),
        "fetched_at": ("DateTime", None, False, "callable"),
        "expires_at": ("DateTime", None, True, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }
    uq_names = {c.name for c in tbl("provider_snapshots").constraints if c.name}
    assert "uq_provider_snapshots_provider_entity" in uq_names


def test_albums_columns() -> None:
    assert describe(tbl("albums")) == {
        "id": ("Uuid", None, False, "callable"),
        "name": ("String", 1024, False, None),
        "album_artist": ("String", 1024, True, None),
        "year": ("Integer", None, True, None),
        "track_count": ("Integer", None, True, None),
        "cover_url": ("String", 2048, True, None),
        "label": ("String", 1024, True, None),
        "copyright_text": ("String", 1024, True, None),
        "popularity": ("Integer", None, True, None),
        "genres": ("JSON", None, False, "callable"),
        "album_type": ("String", 32, True, None),
        "provider": ("Enum", 32, True, None),
        "provider_id": ("String", 256, True, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_artists_columns() -> None:
    assert describe(tbl("artists")) == {
        "id": ("Uuid", None, False, "callable"),
        "name": ("String", 1024, False, None),
        "normalized_name": ("String", 1024, False, None),
        "genres": ("JSON", None, False, "callable"),
        "image_url": ("String", 2048, True, None),
        "popularity": ("Integer", None, True, None),
        "followers": ("Integer", None, True, None),
        "bio": ("Text", None, True, None),
        "country": ("String", 8, True, None),
        "header_url": ("String", 2048, True, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_tracks_columns() -> None:
    assert describe(tbl("tracks")) == {
        "id": ("Uuid", None, False, "callable"),
        "name": ("String", 1024, False, None),
        "duration_ms": ("Integer", None, False, 0),
        "isrc": ("String", 32, True, None),
        "explicit": ("Boolean", None, True, None),
        "track_number": ("Integer", None, True, None),
        "disc_number": ("Integer", None, True, None),
        "year": ("Integer", None, True, None),
        "genres": ("JSON", None, False, "callable"),
        "popularity": ("Integer", None, True, None),
        "date": ("String", 32, True, None),
        "publisher": ("String", 1024, True, None),
        "copyright_text": ("String", 1024, True, None),
        "album_id": ("Uuid", None, True, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_playlists_columns() -> None:
    assert describe(tbl("playlists")) == {
        "id": ("Uuid", None, False, "callable"),
        "name": ("String", 1024, False, None),
        "description": ("Text", None, True, None),
        "owner": ("String", 512, True, None),
        "cover_url": ("String", 2048, True, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_track_artists_columns() -> None:
    assert describe(tbl("track_artists")) == {
        "track_id": ("Uuid", None, False, None),
        "artist_id": ("Uuid", None, False, None),
        "position": ("Integer", None, False, None),
    }
    pk = {c.name for c in tbl("track_artists").primary_key.columns}
    assert pk == {"track_id", "artist_id"}


def test_playlist_tracks_columns() -> None:
    assert describe(tbl("playlist_tracks")) == {
        "playlist_id": ("Uuid", None, False, None),
        "track_id": ("Uuid", None, False, None),
        "position": ("Integer", None, False, None),
    }
    pk = {c.name for c in tbl("playlist_tracks").primary_key.columns}
    assert pk == {"playlist_id", "track_id"}


def test_entity_links_columns() -> None:
    assert describe(tbl("entity_links")) == {
        "id": ("Uuid", None, False, "callable"),
        "entity_type": ("Enum", 32, False, None),
        "entity_id": ("Uuid", None, False, None),
        "snapshot_id": ("Uuid", None, False, None),
        "status": ("Enum", 32, False, LinkStatus.AUTO),
        "upvotes": ("Integer", None, False, 0),
        "downvotes": ("Integer", None, False, 0),
        "net_score": ("Integer", None, False, 0),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_entity_stat_columns() -> None:
    assert describe(tbl("entity_stat")) == {
        "id": ("Uuid", None, False, "callable"),
        "entity_type": ("Enum", 32, False, None),
        "entity_id": ("Uuid", None, False, None),
        "provider": ("Enum", 32, False, None),
        "metric": ("String", 32, False, None),
        "value": ("BigInteger", None, False, None),
        "captured_at": ("DateTime", None, False, "callable"),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }
    ix_names = {ix.name for ix in tbl("entity_stat").indexes}
    assert "ix_entity_stat_entity_type_entity_id_metric" in ix_names


def test_matches_columns() -> None:
    assert describe(tbl("matches")) == {
        "id": ("Uuid", None, False, "callable"),
        "track_id": ("Uuid", None, False, None),
        "target_provider": ("Enum", 32, False, None),
        "target_id": ("String", 512, False, None),
        "target_url": ("String", 2048, False, None),
        "score": ("Float", None, False, None),
        "matcher_version": ("String", 32, False, None),
        "status": ("Enum", 32, False, MatchStatus.AUTO),
        "features": ("JSON", None, True, None),
        "candidate_name": ("String", 1024, True, None),
        "candidate_artists": ("JSON", None, True, None),
        "candidate_duration_ms": ("Integer", None, True, None),
        "submitted_by": ("Uuid", None, True, None),
        "upvotes": ("Integer", None, False, 0),
        "downvotes": ("Integer", None, False, 0),
        "net_score": ("Integer", None, False, 0),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_lyrics_columns() -> None:
    assert describe(tbl("lyrics")) == {
        "id": ("Uuid", None, False, "callable"),
        "track_id": ("Uuid", None, False, None),
        "source": ("Enum", 32, False, None),
        "kind": ("Enum", 32, False, None),
        "text": ("Text", None, False, None),
        "submitted_by": ("Uuid", None, True, None),
        "upvotes": ("Integer", None, False, 0),
        "downvotes": ("Integer", None, False, 0),
        "net_score": ("Integer", None, False, 0),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_download_batches_columns() -> None:
    assert describe(tbl("download_batches")) == {
        "id": ("Uuid", None, False, "callable"),
        "kind": ("Enum", 32, False, None),
        "source": ("String", 2048, True, None),
        "name": ("String", 1024, True, None),
        "output_format": ("String", 16, True, None),
        "bitrate": ("String", 16, True, None),
        "output_template": ("String", 2048, True, None),
        "overwrite": ("String", 16, True, None),
        "generate_m3u": ("Boolean", None, False, False),
        "m3u_template": ("String", 2048, True, None),
        "generate_save_file": ("Boolean", None, False, False),
        "save_file_path": ("String", 2048, True, None),
        "update_archive": ("Boolean", None, False, False),
        "embed_lyrics": ("Boolean", None, False, True),
        "generate_lrc": ("Boolean", None, False, False),
        "sponsor_block": ("Boolean", None, False, False),
        "total_jobs": ("Integer", None, False, 0),
        "finalized_at": ("DateTime", None, True, None),
        "requested_by": ("Uuid", None, True, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_download_jobs_columns() -> None:
    assert describe(tbl("download_jobs")) == {
        "id": ("Uuid", None, False, "callable"),
        "batch_id": ("Uuid", None, True, None),
        "track_id": ("Uuid", None, True, None),
        "match_id": ("Uuid", None, True, None),
        "status": ("Enum", 32, False, DownloadStatus.QUEUED),
        "list_position": ("Integer", None, True, None),
        "output_format": ("String", 16, True, None),
        "bitrate": ("String", 16, True, None),
        "output_template": ("String", 2048, True, None),
        "output_path": ("String", 2048, True, None),
        "progress": ("Float", None, False, 0.0),
        "error_message": ("Text", None, True, None),
        "error_step": ("String", 32, True, None),
        "skip_reason": ("String", 32, True, None),
        "attempts": ("Integer", None, False, 0),
        "requested_by": ("Uuid", None, True, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
        "started_at": ("DateTime", None, True, None),
        "finished_at": ("DateTime", None, True, None),
    }


# --------------------------------------------------------------------------- #
# vote tallies
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["matches", "lyrics", "entity_links"])
def test_vote_tally_columns_present(name: str) -> None:
    cols = tbl(name).columns
    for tally in ("upvotes", "downvotes", "net_score"):
        col = cols[tally]
        assert col.nullable is False
        assert type(col.type).__name__ == "Integer"
        assert col.default is not None and col.default.arg == 0


# --------------------------------------------------------------------------- #
# constraints / uniqueness
# --------------------------------------------------------------------------- #
def test_artists_normalized_name_unique(session: Session) -> None:
    normalized = tbl("artists").columns["normalized_name"]
    assert normalized.nullable is False
    uq_names = {c.name for c in tbl("artists").constraints if c.name}
    assert "uq_artists_normalized_name" in uq_names

    session.add(Artist(name="A", normalized_name="dup"))
    session.commit()
    session.add(Artist(name="B", normalized_name="dup"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


# --------------------------------------------------------------------------- #
# enum columns
# --------------------------------------------------------------------------- #
def test_enum_columns_are_non_native_varchar(session: Session) -> None:
    for name, col in (
        ("provider_snapshots", "provider"),
        ("entity_links", "status"),
        ("matches", "status"),
        ("lyrics", "kind"),
        ("download_jobs", "status"),
        ("download_batches", "kind"),
    ):
        assert tbl(name).columns[col].type.native_enum is False  # type: ignore[attr-defined]

    snap = ProviderSnapshot(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="p1",
        entity_type=EntityType.TRACK,
        raw_payload={"x": 1},
    )
    track = Track(name="t", duration_ms=1000)
    session.add_all([snap, track])
    session.flush()

    link = EntityLink(
        entity_type=EntityType.TRACK,
        entity_id=track.id,
        snapshot_id=snap.id,
        status=LinkStatus.DISPUTED,
    )
    match = Match(
        track_id=track.id,
        target_provider=ProviderId.YOUTUBE,
        target_id="y1",
        target_url="https://x/y1",
        score=1.0,
        matcher_version="v5.0",
        status=MatchStatus.COMMUNITY_VERIFIED,
    )
    lyric = Lyrics(
        track_id=track.id,
        source=ProviderId.LRCLIB,
        kind=LyricsKind.SYNCED,
        text="[00:00.00] hi",
    )
    batch = DownloadBatch(kind=BatchKind.PLAYLIST)
    session.add_all([link, match, lyric, batch])
    session.flush()
    job = DownloadJob(status=DownloadStatus.QUEUED, batch_id=batch.id)
    session.add(job)
    session.commit()

    assert snap.provider is ProviderId.SPOTIFY
    assert link.status is LinkStatus.DISPUTED
    assert match.status is MatchStatus.COMMUNITY_VERIFIED
    assert lyric.kind is LyricsKind.SYNCED
    assert batch.kind is BatchKind.PLAYLIST
    assert job.status is DownloadStatus.QUEUED


# --------------------------------------------------------------------------- #
# ordered M2M
# --------------------------------------------------------------------------- #
def test_ordered_m2m_positions(session: Session) -> None:
    a0 = Artist(name="Main", normalized_name="main")
    a1 = Artist(name="Feat1", normalized_name="feat1")
    a2 = Artist(name="Feat2", normalized_name="feat2")
    track = Track(name="song", duration_ms=1000)
    session.add_all([a0, a1, a2, track])
    session.flush()
    session.execute(
        track_artists.insert(),
        [
            {"track_id": track.id, "artist_id": a0.id, "position": 0},
            {"track_id": track.id, "artist_id": a2.id, "position": 2},
            {"track_id": track.id, "artist_id": a1.id, "position": 1},
        ],
    )
    session.commit()
    session.refresh(track)
    assert [a.name for a in track.artists] == ["Main", "Feat1", "Feat2"]

    pl = Playlist(name="mix")
    t0 = Track(name="one", duration_ms=1000)
    t1 = Track(name="two", duration_ms=1000)
    session.add_all([pl, t0, t1])
    session.flush()
    session.execute(
        playlist_tracks.insert(),
        [
            {"playlist_id": pl.id, "track_id": t1.id, "position": 1},
            {"playlist_id": pl.id, "track_id": t0.id, "position": 0},
        ],
    )
    session.commit()
    session.refresh(pl)
    assert [t.name for t in pl.tracks] == ["one", "two"]


# --------------------------------------------------------------------------- #
# FK behaviour
# --------------------------------------------------------------------------- #
def test_track_album_fk_set_null(session: Session) -> None:
    album = Album(name="LP")
    session.add(album)
    session.flush()
    track = Track(name="t", duration_ms=1000, album_id=album.id)
    session.add(track)
    session.commit()

    session.delete(album)
    session.commit()
    session.refresh(track)
    assert track.album_id is None


def test_cascade_deletes(session: Session) -> None:
    artist = Artist(name="A", normalized_name="a")
    track = Track(name="t", duration_ms=1000)
    pl = Playlist(name="p")
    session.add_all([artist, track, pl])
    session.flush()
    snap = ProviderSnapshot(
        provider=ProviderId.SPOTIFY,
        provider_entity_id="p1",
        entity_type=EntityType.TRACK,
        raw_payload={},
    )
    session.add(snap)
    session.flush()

    session.execute(
        track_artists.insert(),
        [{"track_id": track.id, "artist_id": artist.id, "position": 0}],
    )
    session.execute(
        playlist_tracks.insert(),
        [{"playlist_id": pl.id, "track_id": track.id, "position": 0}],
    )
    session.add_all(
        [
            Match(
                track_id=track.id,
                target_provider=ProviderId.YOUTUBE,
                target_id="y1",
                target_url="https://x/y1",
                score=1.0,
                matcher_version="v5.0",
            ),
            Lyrics(
                track_id=track.id,
                source=ProviderId.LRCLIB,
                kind=LyricsKind.PLAIN,
                text="hi",
            ),
        ]
    )
    session.commit()

    tid = track.id
    session.delete(track)
    session.commit()

    for table in (track_artists, playlist_tracks):
        rows = session.execute(select(table).where(table.c.track_id == tid)).all()
        assert rows == []
    assert session.execute(select(Match).where(Match.track_id == tid)).all() == []
    assert session.execute(select(Lyrics).where(Lyrics.track_id == tid)).all() == []


# --------------------------------------------------------------------------- #
# deferred user references — NO FK
# --------------------------------------------------------------------------- #
def test_no_user_fk_on_votable_tables() -> None:
    for name, col in (
        ("matches", "submitted_by"),
        ("lyrics", "submitted_by"),
        ("download_jobs", "requested_by"),
        ("download_batches", "requested_by"),
    ):
        column = tbl(name).columns[col]
        assert column.foreign_keys == set()
        assert type(column.type).__name__ == "Uuid"
        assert column.nullable is True


# --------------------------------------------------------------------------- #
# download_jobs batch FK
# --------------------------------------------------------------------------- #
def test_download_job_batch_fk_cascade(session: Session) -> None:
    batch_col = tbl("download_jobs").columns["batch_id"]
    fks = list(batch_col.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column is tbl("download_batches").columns["id"]
    assert fks[0].ondelete == "CASCADE"
    assert batch_col.index is True

    for c in ("batch_id", "list_position", "skip_reason"):
        assert tbl("download_jobs").columns[c].nullable is True

    attempts = tbl("download_jobs").columns["attempts"]
    assert type(attempts.type).__name__ == "Integer"
    assert attempts.nullable is False
    assert attempts.default is not None and attempts.default.arg == 0

    batch = DownloadBatch(kind=BatchKind.ALBUM)
    session.add(batch)
    session.flush()
    job = DownloadJob(batch_id=batch.id)
    session.add(job)
    session.commit()
    jid = job.id

    session.delete(batch)
    session.commit()
    assert session.get(DownloadJob, jid) is None
