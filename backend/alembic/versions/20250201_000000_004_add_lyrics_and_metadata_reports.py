"""Add lyrics and metadata reports, extend song/artist/album models

Revision ID: 004
Revises: 003
Create Date: 2025-02-01 00:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create lyrics table
    op.create_table(
        "lyrics",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("song_id", sa.UUID(), nullable=False),
        sa.Column("lyrics_text", sa.Text(), nullable=False),
        sa.Column("lyrics_synced", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("song_id", "source", name="uq_lyrics_song_source"),
    )
    op.create_index(op.f("ix_lyrics_song_id"), "lyrics", ["song_id"], unique=False)
    op.create_index(op.f("ix_lyrics_source"), "lyrics", ["source"], unique=False)

    # Create metadata_reports table
    op.create_table(
        "metadata_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("reporter_id", sa.UUID(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("current_value", sa.Text(), nullable=False),
        sa.Column("suggested_value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        op.f("ix_metadata_reports_reporter_id"),
        "metadata_reports",
        ["reporter_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metadata_reports_status"),
        "metadata_reports",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_metadata_reports_entity",
        "metadata_reports",
        ["entity_type", "entity_id"],
        unique=False,
    )

    # Add audio features columns to songs table
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table("songs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bpm", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("energy", sa.Numeric(precision=3, scale=2), nullable=True))
        batch_op.add_column(sa.Column("danceability", sa.Numeric(precision=3, scale=2), nullable=True))
        batch_op.add_column(sa.Column("valence", sa.Numeric(precision=3, scale=2), nullable=True))
        batch_op.add_column(sa.Column("key", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("mode", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("loudness", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("speechiness", sa.Numeric(precision=3, scale=2), nullable=True))
        batch_op.add_column(sa.Column("acousticness", sa.Numeric(precision=3, scale=2), nullable=True))
        batch_op.add_column(sa.Column("instrumentalness", sa.Numeric(precision=3, scale=2), nullable=True))
        batch_op.add_column(sa.Column("liveness", sa.Numeric(precision=3, scale=2), nullable=True))
        batch_op.add_column(sa.Column("time_signature", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("popularity", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("label", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("copyright_text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("release_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("explicit", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("genres", sa.JSON(), nullable=True))

    # Note: artists and albums extended metadata columns are already in migration 003


def downgrade() -> None:
    # Remove audio features columns from songs table
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table("songs", schema=None) as batch_op:
        batch_op.drop_column("genres")
        batch_op.drop_column("explicit")
        batch_op.drop_column("release_date")
        batch_op.drop_column("copyright_text")
        batch_op.drop_column("label")
        batch_op.drop_column("popularity")
        batch_op.drop_column("time_signature")
        batch_op.drop_column("liveness")
        batch_op.drop_column("instrumentalness")
        batch_op.drop_column("acousticness")
        batch_op.drop_column("speechiness")
        batch_op.drop_column("loudness")
        batch_op.drop_column("mode")
        batch_op.drop_column("key")
        batch_op.drop_column("valence")
        batch_op.drop_column("danceability")
        batch_op.drop_column("energy")
        batch_op.drop_column("bpm")

    # Drop metadata_reports table
    op.drop_index("ix_metadata_reports_entity", table_name="metadata_reports")
    op.drop_index(op.f("ix_metadata_reports_status"), table_name="metadata_reports")
    op.drop_index(op.f("ix_metadata_reports_reporter_id"), table_name="metadata_reports")
    op.drop_table("metadata_reports")

    # Drop lyrics table
    op.drop_index(op.f("ix_lyrics_source"), table_name="lyrics")
    op.drop_index(op.f("ix_lyrics_song_id"), table_name="lyrics")
    op.drop_table("lyrics")
