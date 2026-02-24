"""Add unified entity/capability architecture tables.

Revision ID: 015_unified_entity_architecture
Revises: 014_download_features
Create Date: 2026-02-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "015_unified_entity_architecture"
down_revision: Union[str, None] = "014_download_features"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create unified entity, snapshot, provenance, relation, and relation vote tables."""
    op.create_table(
        "entities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False, server_default="Unknown"),
        sa.Column("canonical", sa.JSON(), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_merged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("merge_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_key", name="uq_entities_entity_key"),
    )
    op.create_index("ix_entities_type", "entities", ["entity_type"], unique=False)
    op.create_index("ix_entities_name", "entities", ["name"], unique=False)

    op.create_table(
        "entity_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("provider_entity_id", sa.String(length=255), nullable=True),
        sa.Column("provider_url", sa.Text(), nullable=True),
        sa.Column("normalized_payload", sa.JSON(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_id",
            "provider_id",
            "provider_entity_id",
            name="uq_entity_snapshots_entity_provider_id",
        ),
    )
    op.create_index(
        "ix_entity_snapshots_entity_id",
        "entity_snapshots",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_entity_snapshots_provider",
        "entity_snapshots",
        ["provider_id"],
        unique=False,
    )

    op.create_table(
        "entity_field_provenance",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["entity_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_entity_field_provenance_entity",
        "entity_field_provenance",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_entity_field_provenance_snapshot",
        "entity_field_provenance",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_entity_field_provenance_selected",
        "entity_field_provenance",
        ["selected"],
        unique=False,
    )

    op.create_table(
        "entity_relations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("from_entity_id", sa.String(length=36), nullable=False),
        sa.Column("to_entity_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="suggested"),
        sa.Column("discovered_by", sa.String(length=64), nullable=True),
        sa.Column("relation_data", sa.JSON(), nullable=False),
        sa.Column("upvotes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("downvotes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["from_entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "from_entity_id",
            "to_entity_id",
            "relation_type",
            name="uq_entity_relations_triplet",
        ),
    )
    op.create_index(
        "ix_entity_relations_from",
        "entity_relations",
        ["from_entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_entity_relations_to",
        "entity_relations",
        ["to_entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_entity_relations_type",
        "entity_relations",
        ["relation_type"],
        unique=False,
    )

    op.create_table(
        "relation_votes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("relation_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("vote_type", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["relation_id"], ["entity_relations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "relation_id",
            "user_id",
            name="uq_relation_votes_relation_user",
        ),
    )
    op.create_index(
        "ix_relation_votes_relation",
        "relation_votes",
        ["relation_id"],
        unique=False,
    )
    op.create_index(
        "ix_relation_votes_user",
        "relation_votes",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop unified architecture tables."""
    op.drop_index("ix_relation_votes_user", table_name="relation_votes")
    op.drop_index("ix_relation_votes_relation", table_name="relation_votes")
    op.drop_table("relation_votes")

    op.drop_index("ix_entity_relations_type", table_name="entity_relations")
    op.drop_index("ix_entity_relations_to", table_name="entity_relations")
    op.drop_index("ix_entity_relations_from", table_name="entity_relations")
    op.drop_table("entity_relations")

    op.drop_index("ix_entity_field_provenance_selected", table_name="entity_field_provenance")
    op.drop_index("ix_entity_field_provenance_snapshot", table_name="entity_field_provenance")
    op.drop_index("ix_entity_field_provenance_entity", table_name="entity_field_provenance")
    op.drop_table("entity_field_provenance")

    op.drop_index("ix_entity_snapshots_provider", table_name="entity_snapshots")
    op.drop_index("ix_entity_snapshots_entity_id", table_name="entity_snapshots")
    op.drop_table("entity_snapshots")

    op.drop_index("ix_entities_name", table_name="entities")
    op.drop_index("ix_entities_type", table_name="entities")
    op.drop_table("entities")
