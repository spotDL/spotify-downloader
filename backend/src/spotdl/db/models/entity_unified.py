"""Unified entity models for capability-based metadata orchestration."""

from __future__ import annotations

import uuid  # noqa: TC003
from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import GUID, Base, TimestampMixin, generate_uuid, utc_now

if TYPE_CHECKING:
    from spotdl.db.models.user import User


class Entity(Base, TimestampMixin):
    """Canonical merged entity across providers."""

    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("entity_key", name="uq_entities_entity_key"),
        Index("ix_entities_type", "entity_type"),
        Index("ix_entities_name", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    entity_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    entity_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        default="Unknown",
    )
    canonical: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    capabilities: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    quality_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    last_merged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    merge_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    snapshots: Mapped[list[EntitySnapshot]] = relationship(
        "EntitySnapshot",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    provenance: Mapped[list[EntityFieldProvenance]] = relationship(
        "EntityFieldProvenance",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    outgoing_relations: Mapped[list[EntityRelation]] = relationship(
        "EntityRelation",
        back_populates="from_entity",
        foreign_keys="EntityRelation.from_entity_id",
        cascade="all, delete-orphan",
    )
    incoming_relations: Mapped[list[EntityRelation]] = relationship(
        "EntityRelation",
        back_populates="to_entity",
        foreign_keys="EntityRelation.to_entity_id",
        cascade="all, delete-orphan",
    )


class EntitySnapshot(Base, TimestampMixin):
    """Provider-specific snapshot for an entity."""

    __tablename__ = "entity_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "entity_id",
            "provider_id",
            "provider_entity_id",
            name="uq_entity_snapshots_entity_provider_id",
        ),
        Index("ix_entity_snapshots_entity_id", "entity_id"),
        Index("ix_entity_snapshots_provider", "provider_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    provider_entity_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    provider_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    normalized_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    capabilities: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    entity: Mapped[Entity] = relationship(
        "Entity",
        back_populates="snapshots",
    )
    field_provenance: Mapped[list[EntityFieldProvenance]] = relationship(
        "EntityFieldProvenance",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )


class EntityFieldProvenance(Base, TimestampMixin):
    """Field-level merge provenance for canonical entity values."""

    __tablename__ = "entity_field_provenance"
    __table_args__ = (
        Index("ix_entity_field_provenance_entity", "entity_id"),
        Index("ix_entity_field_provenance_snapshot", "snapshot_id"),
        Index("ix_entity_field_provenance_selected", "selected"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("entity_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    selected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    entity: Mapped[Entity] = relationship(
        "Entity",
        back_populates="provenance",
    )
    snapshot: Mapped[EntitySnapshot] = relationship(
        "EntitySnapshot",
        back_populates="field_provenance",
    )


class EntityRelation(Base, TimestampMixin):
    """Relationship between canonical entities."""

    __tablename__ = "entity_relations"
    __table_args__ = (
        UniqueConstraint(
            "from_entity_id",
            "to_entity_id",
            "relation_type",
            name="uq_entity_relations_triplet",
        ),
        Index("ix_entity_relations_from", "from_entity_id"),
        Index("ix_entity_relations_to", "to_entity_id"),
        Index("ix_entity_relations_type", "relation_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    from_entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    match_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="suggested",
    )
    discovered_by: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    relation_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    upvotes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    downvotes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    from_entity: Mapped[Entity] = relationship(
        "Entity",
        back_populates="outgoing_relations",
        foreign_keys=[from_entity_id],
    )
    to_entity: Mapped[Entity] = relationship(
        "Entity",
        back_populates="incoming_relations",
        foreign_keys=[to_entity_id],
    )
    votes: Mapped[list[RelationVote]] = relationship(
        "RelationVote",
        back_populates="relation",
        cascade="all, delete-orphan",
    )

    @property
    def net_votes(self) -> int:
        return self.upvotes - self.downvotes


class RelationVote(Base, TimestampMixin):
    """User vote on a relation."""

    __tablename__ = "relation_votes"
    __table_args__ = (
        UniqueConstraint(
            "relation_id",
            "user_id",
            name="uq_relation_votes_relation_user",
        ),
        Index("ix_relation_votes_relation", "relation_id"),
        Index("ix_relation_votes_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    relation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("entity_relations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    vote_type: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
    )

    relation: Mapped[EntityRelation] = relationship(
        "EntityRelation",
        back_populates="votes",
    )
    user: Mapped[User] = relationship("User")
