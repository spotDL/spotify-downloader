"""The full spec §6.1 ORM schema — THE anti-churn contract.

Every column, type, default, constraint and index below is fixed by
``docs/superpowers/plans/…-plan-5-server-foundation.md`` §"THE SCHEMA". Plan 6
(auth/votes/reports) and Plan 7 (downloads/WS) add only NEW tables — they never
ALTER a table defined here. The ``download_batches`` / ``download_jobs`` tables
and the deferred ``submitted_by`` / ``requested_by`` user columns are created
now (as plain nullable UUIDs with NO foreign key) precisely so those plans ship
zero migrations against this schema.

Cross-dialect rules (portable across SQLite + Postgres):
  * PKs are ``sa.Uuid(as_uuid=True)`` with Python-side ``default=uuid.uuid4``.
  * Enums are ``sa.Enum(..., native_enum=False, length=32)`` → VARCHAR + CHECK.
  * Timestamps are ``sa.DateTime(timezone=True)`` with Python-side defaults.
  * JSON is used only for provider payloads and small normalized value lists.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from spotdl_core.model import EntityType, LyricsKind, MatchStatus, ProviderId
from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl_server.db.base import Base, TimestampMixin
from spotdl_server.db.enums import BatchKind, DownloadStatus, LinkStatus


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _enum(py_enum: type[enum.Enum]) -> sa.Enum:
    """Non-native VARCHAR+CHECK enum, identical on both dialects."""
    return sa.Enum(py_enum, native_enum=False, validate_strings=True, length=32)


# --------------------------------------------------------------------------- #
# provider_snapshots — permanent metadata cache + external-ID map
# --------------------------------------------------------------------------- #
class ProviderSnapshot(Base, TimestampMixin):
    __tablename__ = "provider_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_entity_id",
            name="uq_provider_snapshots_provider_entity",
        ),
        Index("ix_provider_snapshots_isrc", "isrc"),
        Index("ix_provider_snapshots_provider_entity_type", "provider", "entity_type"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    provider: Mapped[ProviderId] = mapped_column(_enum(ProviderId), nullable=False)
    provider_entity_id: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(_enum(EntityType), nullable=False)
    raw_payload: Mapped[Any] = mapped_column(sa.JSON, nullable=False)
    name: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    isrc: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    artist_names: Mapped[list[str] | None] = mapped_column(sa.JSON, nullable=True)
    album_name: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    art_url: Mapped[str | None] = mapped_column(sa.String(2048), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)


# --------------------------------------------------------------------------- #
# association tables (ordered M2M) — plain Table objects, position payload only
# --------------------------------------------------------------------------- #
track_artists = Table(
    "track_artists",
    Base.metadata,
    Column(
        "track_id",
        sa.Uuid(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "artist_id",
        sa.Uuid(as_uuid=True),
        ForeignKey("artists.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("position", sa.Integer, nullable=False),
    Index("ix_track_artists_artist_id", "artist_id"),
)

playlist_tracks = Table(
    "playlist_tracks",
    Base.metadata,
    Column(
        "playlist_id",
        sa.Uuid(as_uuid=True),
        ForeignKey("playlists.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "track_id",
        sa.Uuid(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("position", sa.Integer, nullable=False),
    Index("ix_playlist_tracks_track_id", "track_id"),
)


# --------------------------------------------------------------------------- #
# albums
# --------------------------------------------------------------------------- #
class Album(Base, TimestampMixin):
    __tablename__ = "albums"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    album_artist: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    year: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    track_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(sa.String(2048), nullable=True)

    tracks: Mapped[list[Track]] = relationship(
        "Track",
        back_populates="album",
        lazy="selectin",
        passive_deletes=True,
    )


# --------------------------------------------------------------------------- #
# artists
# --------------------------------------------------------------------------- #
class Artist(Base, TimestampMixin):
    __tablename__ = "artists"
    __table_args__ = (UniqueConstraint("normalized_name", name="uq_artists_normalized_name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    normalized_name: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    genres: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False, default=list)
    image_url: Mapped[str | None] = mapped_column(sa.String(2048), nullable=True)

    tracks: Mapped[list[Track]] = relationship(
        "Track",
        secondary=track_artists,
        back_populates="artists",
        lazy="selectin",
        passive_deletes=True,
    )


# --------------------------------------------------------------------------- #
# tracks
# --------------------------------------------------------------------------- #
class Track(Base, TimestampMixin):
    __tablename__ = "tracks"
    __table_args__ = (
        Index("ix_tracks_isrc", "isrc"),
        Index("ix_tracks_album_id", "album_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    duration_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    isrc: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    explicit: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    track_number: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    disc_number: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    year: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    genres: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False, default=list)
    popularity: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    album_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("albums.id", ondelete="SET NULL"),
        nullable=True,
    )

    album: Mapped[Album | None] = relationship("Album", back_populates="tracks", lazy="selectin")
    artists: Mapped[list[Artist]] = relationship(
        "Artist",
        secondary=track_artists,
        order_by=track_artists.c.position,
        back_populates="tracks",
        lazy="selectin",
        passive_deletes=True,
    )
    matches: Mapped[list[Match]] = relationship(
        "Match",
        back_populates="track",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    lyrics: Mapped[list[Lyrics]] = relationship(
        "Lyrics",
        back_populates="track",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# --------------------------------------------------------------------------- #
# playlists
# --------------------------------------------------------------------------- #
class Playlist(Base, TimestampMixin):
    __tablename__ = "playlists"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(sa.String(2048), nullable=True)

    tracks: Mapped[list[Track]] = relationship(
        "Track",
        secondary=playlist_tracks,
        order_by=playlist_tracks.c.position,
        lazy="selectin",
        passive_deletes=True,
    )


# --------------------------------------------------------------------------- #
# entity_links — canonical entity ↔ snapshot linkage; votable
# --------------------------------------------------------------------------- #
class EntityLink(Base, TimestampMixin):
    __tablename__ = "entity_links"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "snapshot_id",
            name="uq_entity_links_entity_type_entity_id_snapshot_id",
        ),
        Index("ix_entity_links_snapshot_id", "snapshot_id"),
        Index("ix_entity_links_entity_type_entity_id", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    entity_type: Mapped[EntityType] = mapped_column(_enum(EntityType), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("provider_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[LinkStatus] = mapped_column(
        _enum(LinkStatus), nullable=False, default=LinkStatus.AUTO
    )
    upvotes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    downvotes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    net_score: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)


# --------------------------------------------------------------------------- #
# matches — provider-agnostic track → audio target; votable
# --------------------------------------------------------------------------- #
class Match(Base, TimestampMixin):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint(
            "track_id",
            "target_provider",
            "target_id",
            name="uq_matches_track_id_target_provider_target_id",
        ),
        Index("ix_matches_track_id_status", "track_id", "status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    track_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_provider: Mapped[ProviderId] = mapped_column(_enum(ProviderId), nullable=False)
    target_id: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    target_url: Mapped[str] = mapped_column(sa.String(2048), nullable=False)
    score: Mapped[float] = mapped_column(sa.Float, nullable=False)
    matcher_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    status: Mapped[MatchStatus] = mapped_column(
        _enum(MatchStatus), nullable=False, default=MatchStatus.AUTO
    )
    features: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True)
    candidate_name: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    candidate_artists: Mapped[list[str] | None] = mapped_column(sa.JSON, nullable=True)
    candidate_duration_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    # Deferred user reference: plain nullable UUID, NO foreign key. Plan 6 creates
    # `users` and adds `votes` FKing INTO this table (additive, no ALTER here).
    # NULL = auto-generated match. App-level integrity for the back-reference.
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid(as_uuid=True), nullable=True)
    upvotes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    downvotes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    net_score: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    track: Mapped[Track] = relationship("Track", back_populates="matches")


# --------------------------------------------------------------------------- #
# lyrics — per track, per source, per kind; votable
# --------------------------------------------------------------------------- #
class Lyrics(Base, TimestampMixin):
    __tablename__ = "lyrics"
    __table_args__ = (
        UniqueConstraint("track_id", "source", "kind", name="uq_lyrics_track_id_source_kind"),
        Index("ix_lyrics_track_id", "track_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    track_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[ProviderId] = mapped_column(_enum(ProviderId), nullable=False)
    kind: Mapped[LyricsKind] = mapped_column(_enum(LyricsKind), nullable=False)
    text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # Deferred user reference: plain nullable UUID, NO foreign key (Plan 6 pattern).
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid(as_uuid=True), nullable=True)
    upvotes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    downvotes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    net_score: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    track: Mapped[Track] = relationship("Track", back_populates="lyrics")


# --------------------------------------------------------------------------- #
# download_batches — schema only; created here, UNUSED until Plan 7
# --------------------------------------------------------------------------- #
class DownloadBatch(Base, TimestampMixin):
    __tablename__ = "download_batches"
    __table_args__ = (Index("ix_download_batches_requested_by", "requested_by"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    kind: Mapped[BatchKind] = mapped_column(_enum(BatchKind), nullable=False)
    source: Mapped[str | None] = mapped_column(sa.String(2048), nullable=True)
    name: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    output_format: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    bitrate: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    output_template: Mapped[str | None] = mapped_column(sa.String(2048), nullable=True)
    generate_m3u: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    m3u_template: Mapped[str | None] = mapped_column(sa.String(2048), nullable=True)
    generate_save_file: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    save_file_path: Mapped[str | None] = mapped_column(sa.String(2048), nullable=True)
    update_archive: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    embed_lyrics: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    generate_lrc: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    sponsor_block: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    total_jobs: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    finalized_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    # Deferred user reference: plain nullable UUID, NO foreign key (Plan 6 pattern).
    requested_by: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid(as_uuid=True), nullable=True)


# --------------------------------------------------------------------------- #
# download_jobs — schema only; created here, UNUSED until Plan 7
# --------------------------------------------------------------------------- #
class DownloadJob(Base, TimestampMixin):
    __tablename__ = "download_jobs"
    __table_args__ = (
        Index("ix_download_jobs_status", "status"),
        Index("ix_download_jobs_track_id", "track_id"),
        # batch_id index comes from `index=True` on the column below.
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("download_batches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    track_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("tracks.id", ondelete="SET NULL"),
        nullable=True,
    )
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("matches.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[DownloadStatus] = mapped_column(
        _enum(DownloadStatus), nullable=False, default=DownloadStatus.QUEUED
    )
    list_position: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    output_format: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    bitrate: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    output_template: Mapped[str | None] = mapped_column(sa.String(2048), nullable=True)
    output_path: Mapped[str | None] = mapped_column(sa.String(2048), nullable=True)
    progress: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    error_step: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    skip_reason: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    attempts: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    # Deferred user reference: plain nullable UUID, NO foreign key (Plan 6 pattern).
    requested_by: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid(as_uuid=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
