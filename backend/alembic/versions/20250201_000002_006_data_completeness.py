"""Add data completeness fields to Song and Lyrics

Revision ID: 006_data_completeness
Revises: 005_add_admin_fields
Create Date: 2025-02-01

Adds:
- Song: field_sources, musicbrainz_id, discogs_id, enriched_at for metadata tracking
- Lyrics: content_hash, quality_score, is_verified, line_count for deduplication/quality
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006_data_completeness"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Detect dialect for JSON type
    bind = op.get_bind()
    dialect = bind.dialect.name

    # JSON type: JSONB for PostgreSQL, TEXT for SQLite
    if dialect == "postgresql":
        json_type = postgresql.JSONB
    else:
        json_type = sa.Text

    # === Song table additions ===
    # field_sources: tracks which metadata source provided which field
    # Example: {"genres": "musicbrainz", "label": "discogs", "bpm": "spotify"}
    op.add_column(
        "songs",
        sa.Column("field_sources", json_type, nullable=True),
    )

    # External IDs for re-fetching metadata
    op.add_column(
        "songs",
        sa.Column("musicbrainz_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "songs",
        sa.Column("discogs_id", sa.String(length=64), nullable=True),
    )

    # Last enrichment timestamp for staleness checking
    op.add_column(
        "songs",
        sa.Column("enriched_at", sa.DateTime(), nullable=True),
    )

    # Create indexes for external ID lookups
    op.create_index(
        "ix_songs_musicbrainz_id",
        "songs",
        ["musicbrainz_id"],
        unique=False,
    )
    op.create_index(
        "ix_songs_discogs_id",
        "songs",
        ["discogs_id"],
        unique=False,
    )

    # === Lyrics table additions ===
    # content_hash: SHA256 hash for deduplication
    op.add_column(
        "lyrics",
        sa.Column("content_hash", sa.String(length=64), nullable=True),
    )

    # quality_score: 0-1 float indicating lyrics quality
    op.add_column(
        "lyrics",
        sa.Column("quality_score", sa.Float(), nullable=True, server_default="0.5"),
    )

    # is_verified: whether lyrics have been human-verified
    op.add_column(
        "lyrics",
        sa.Column("is_verified", sa.Boolean(), nullable=True, server_default="false"),
    )

    # line_count: number of lines for quality assessment
    op.add_column(
        "lyrics",
        sa.Column("line_count", sa.Integer(), nullable=True),
    )

    # Create index for content hash deduplication lookups
    op.create_index(
        "ix_lyrics_content_hash",
        "lyrics",
        ["content_hash"],
        unique=False,
    )

    # Composite index for finding duplicates per song
    op.create_index(
        "ix_lyrics_song_hash",
        "lyrics",
        ["song_id", "content_hash"],
        unique=False,
    )


def downgrade() -> None:
    # === Remove Lyrics indexes and columns ===
    op.drop_index("ix_lyrics_song_hash", table_name="lyrics")
    op.drop_index("ix_lyrics_content_hash", table_name="lyrics")
    op.drop_column("lyrics", "line_count")
    op.drop_column("lyrics", "is_verified")
    op.drop_column("lyrics", "quality_score")
    op.drop_column("lyrics", "content_hash")

    # === Remove Song indexes and columns ===
    op.drop_index("ix_songs_discogs_id", table_name="songs")
    op.drop_index("ix_songs_musicbrainz_id", table_name="songs")
    op.drop_column("songs", "enriched_at")
    op.drop_column("songs", "discogs_id")
    op.drop_column("songs", "musicbrainz_id")
    op.drop_column("songs", "field_sources")
