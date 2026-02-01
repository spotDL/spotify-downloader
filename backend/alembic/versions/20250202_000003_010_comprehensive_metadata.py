"""Add comprehensive multi-source metadata support.

Revision ID: 010_comprehensive_metadata
Revises: 009_refresh_cooldowns
Create Date: 2025-02-02

Adds:
- raw_response column to metadata_snapshots for complete API responses
- provider_track_id, has_translations, language columns to lyrics table
- Indexes for efficient queries
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "010_comprehensive_metadata"
down_revision: Union[str, None] = "009_refresh_cooldowns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add comprehensive metadata columns."""
    # Detect dialect for JSON type
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        json_type = postgresql.JSONB
    else:
        json_type = sa.Text

    # Add raw_response column to metadata_snapshots
    op.add_column(
        "metadata_snapshots",
        sa.Column("raw_response", json_type, nullable=True),
    )

    # Add new columns to lyrics table for provider-specific metadata
    op.add_column(
        "lyrics",
        sa.Column(
            "provider_track_id",
            sa.String(255),
            nullable=True,
            comment="Track ID on the lyrics provider (for refetching)",
        ),
    )
    op.add_column(
        "lyrics",
        sa.Column(
            "has_translations",
            sa.Boolean,
            nullable=True,
            comment="Whether translations are available (MusixMatch)",
        ),
    )
    op.add_column(
        "lyrics",
        sa.Column(
            "language",
            sa.String(10),
            nullable=True,
            comment="Detected language of lyrics",
        ),
    )

    # Add index for lyrics quality queries
    op.create_index(
        "ix_lyrics_song_quality",
        "lyrics",
        ["song_id", "quality_score"],
    )


def downgrade() -> None:
    """Remove comprehensive metadata columns."""
    # Remove lyrics index
    op.drop_index("ix_lyrics_song_quality", table_name="lyrics")

    # Remove lyrics columns
    op.drop_column("lyrics", "language")
    op.drop_column("lyrics", "has_translations")
    op.drop_column("lyrics", "provider_track_id")

    # Remove metadata_snapshots column
    op.drop_column("metadata_snapshots", "raw_response")
