"""Add metadata_snapshots table for multi-source metadata

Revision ID: 008_metadata_snapshots
Revises: 007_provider_preferences
Create Date: 2025-02-02

Adds a table to store metadata snapshots from different sources,
allowing users to view and compare metadata from multiple providers.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008_metadata_snapshots"
down_revision: Union[str, None] = "007_provider_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Detect dialect for JSON type and UUID type
    bind = op.get_bind()
    dialect = bind.dialect.name

    # JSON type: JSONB for PostgreSQL, TEXT for SQLite
    if dialect == "postgresql":
        json_type = postgresql.JSONB
        uuid_type = postgresql.UUID(as_uuid=True)
    else:
        json_type = sa.Text
        uuid_type = sa.String(36)

    # Create metadata_snapshots table
    op.create_table(
        "metadata_snapshots",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "song_id",
            uuid_type,
            sa.ForeignKey("songs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("source", sa.String(50), nullable=False, index=True),
        sa.Column("snapshot_data", json_type, nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create composite index for efficient lookups
    op.create_index(
        "ix_metadata_snapshots_song_source",
        "metadata_snapshots",
        ["song_id", "source"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_metadata_snapshots_song_source", table_name="metadata_snapshots")
    op.drop_table("metadata_snapshots")
