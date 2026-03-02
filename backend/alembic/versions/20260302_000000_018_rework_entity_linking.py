"""Rework entity linking: slim Entity, add entity_canonicals, NOT NULL provider_entity_id.

Clean-slate migration that drops all entity data and recreates tables with the new schema.
Entity becomes slim (id + entity_type only). Merged canonical data moves to entity_canonicals.
EntitySnapshot gets NOT NULL provider_entity_id and a global dedup unique index.

Revision ID: 018_rework_entity_link
Revises: 017_rekey_track_entities
Create Date: 2026-03-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "018_rework_entity_link"
down_revision: str | None = "017_rekey_track_entities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Drop all entity-related data in FK order
    op.execute("DELETE FROM relation_votes")
    op.execute("DELETE FROM entity_relations")
    op.execute("DELETE FROM entity_field_provenance")
    op.execute("DELETE FROM entity_snapshots")
    op.execute("DELETE FROM lyrics")
    op.execute("DROP TABLE IF EXISTS entity_canonicals")
    op.execute("DELETE FROM entities")

    # 2. Slim down entities table: drop removed columns and their indexes/constraints
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("entities") as batch_op:
        batch_op.drop_index("ix_entities_name")
        batch_op.drop_constraint("uq_entities_entity_key", type_="unique")
        batch_op.drop_column("entity_key")
        batch_op.drop_column("name")
        batch_op.drop_column("canonical")
        batch_op.drop_column("capabilities")
        batch_op.drop_column("quality_score")
        batch_op.drop_column("last_merged_at")
        batch_op.drop_column("merge_version")

    # 3. Create entity_canonicals table
    op.create_table(
        "entity_canonicals",
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False, server_default="Unknown"),
        sa.Column("canonical", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("merge_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # 4. Update entity_snapshots: make provider_entity_id NOT NULL + add global dedup index
    # All rows are already deleted, so we can safely alter
    with op.batch_alter_table("entity_snapshots") as batch_op:
        batch_op.alter_column("provider_entity_id", nullable=False)
        batch_op.create_unique_constraint(
            "uq_snapshots_provider_entity",
            ["provider_id", "provider_entity_id"],
        )


def downgrade() -> None:
    # Remove global dedup index, make provider_entity_id nullable again
    with op.batch_alter_table("entity_snapshots") as batch_op:
        batch_op.drop_constraint("uq_snapshots_provider_entity", type_="unique")
        batch_op.alter_column("provider_entity_id", nullable=True)

    # Drop entity_canonicals
    op.drop_table("entity_canonicals")

    # Re-add removed columns to entities
    with op.batch_alter_table("entities") as batch_op:
        batch_op.add_column(sa.Column("entity_key", sa.String(255), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("name", sa.String(512), nullable=False, server_default="Unknown"))
        batch_op.add_column(sa.Column("canonical", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("capabilities", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"))
        batch_op.add_column(sa.Column("last_merged_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
        batch_op.add_column(sa.Column("merge_version", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_unique_constraint("uq_entities_entity_key", ["entity_key"])
        batch_op.create_index("ix_entities_name", ["name"])
