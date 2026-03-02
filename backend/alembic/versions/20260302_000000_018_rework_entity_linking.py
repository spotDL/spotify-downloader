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

from spotdl.db.models.base import GUID

revision: str = "018_rework_entity_link"
down_revision: str | None = "017_rekey_track_entities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    # 1. Drop all entity-related data in FK order
    op.execute(sa.text("DELETE FROM relation_votes"))
    op.execute(sa.text("DELETE FROM entity_relations"))
    op.execute(sa.text("DELETE FROM entity_field_provenance"))
    op.execute(sa.text("DELETE FROM entity_snapshots"))
    op.execute(sa.text("DELETE FROM lyrics"))
    op.execute(sa.text("DROP TABLE IF EXISTS entity_canonicals"))
    op.execute(sa.text("DELETE FROM entities"))

    # 2. Slim down entities table: drop removed columns and their indexes/constraints
    if _is_sqlite():
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
    else:
        op.drop_index("ix_entities_name", table_name="entities")
        op.drop_constraint("uq_entities_entity_key", table_name="entities", type_="unique")
        op.drop_column("entities", "entity_key")
        op.drop_column("entities", "name")
        op.drop_column("entities", "canonical")
        op.drop_column("entities", "capabilities")
        op.drop_column("entities", "quality_score")
        op.drop_column("entities", "last_merged_at")
        op.drop_column("entities", "merge_version")

    # 3. Create entity_canonicals table
    op.create_table(
        "entity_canonicals",
        sa.Column("entity_id", GUID(), sa.ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False, server_default="Unknown"),
        sa.Column("canonical", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("merge_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # 4. Update entity_snapshots: make provider_entity_id NOT NULL + add global dedup index
    if _is_sqlite():
        with op.batch_alter_table("entity_snapshots") as batch_op:
            batch_op.alter_column("provider_entity_id", nullable=False)
            batch_op.create_unique_constraint(
                "uq_snapshots_provider_entity",
                ["provider_id", "provider_entity_id"],
            )
    else:
        op.alter_column("entity_snapshots", "provider_entity_id", nullable=False)
        op.create_unique_constraint(
            "uq_snapshots_provider_entity",
            "entity_snapshots",
            ["provider_id", "provider_entity_id"],
        )


def downgrade() -> None:
    # Remove global dedup index, make provider_entity_id nullable again
    if _is_sqlite():
        with op.batch_alter_table("entity_snapshots") as batch_op:
            batch_op.drop_constraint("uq_snapshots_provider_entity", type_="unique")
            batch_op.alter_column("provider_entity_id", nullable=True)
    else:
        op.drop_constraint("uq_snapshots_provider_entity", "entity_snapshots", type_="unique")
        op.alter_column("entity_snapshots", "provider_entity_id", nullable=True)

    # Drop entity_canonicals
    op.drop_table("entity_canonicals")

    # Re-add removed columns to entities
    if _is_sqlite():
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
    else:
        op.add_column("entities", sa.Column("entity_key", sa.String(255), nullable=False, server_default=""))
        op.add_column("entities", sa.Column("name", sa.String(512), nullable=False, server_default="Unknown"))
        op.add_column("entities", sa.Column("canonical", sa.JSON(), nullable=False, server_default="{}"))
        op.add_column("entities", sa.Column("capabilities", sa.JSON(), nullable=False, server_default="{}"))
        op.add_column("entities", sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"))
        op.add_column("entities", sa.Column("last_merged_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
        op.add_column("entities", sa.Column("merge_version", sa.Integer(), nullable=False, server_default="1"))
        op.create_unique_constraint("uq_entities_entity_key", "entities", ["entity_key"])
        op.create_index("ix_entities_name", "entities", ["name"])
