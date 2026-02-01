"""Add refresh cooldowns table.

Revision ID: 009_refresh_cooldowns
Revises: 008_metadata_snapshots
Create Date: 2025-02-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "009_refresh_cooldowns"
down_revision = "008_metadata_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create refresh_cooldowns table."""
    op.create_table(
        "refresh_cooldowns",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", "user_id", name="uq_refresh_cooldown_entity_user"),
    )

    # Index for fast lookups
    op.create_index(
        "ix_refresh_cooldowns_entity",
        "refresh_cooldowns",
        ["entity_type", "entity_id"],
    )


def downgrade() -> None:
    """Drop refresh_cooldowns table."""
    op.drop_index("ix_refresh_cooldowns_entity", table_name="refresh_cooldowns")
    op.drop_table("refresh_cooldowns")
