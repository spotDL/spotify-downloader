"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2025-01-31 00:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, default=False),
        sa.Column("reputation_score", sa.Integer(), nullable=False, default=0),
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
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # Create songs table
    op.create_table(
        "songs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("platform_id", sa.String(length=255), nullable=False),
        sa.Column("platform_url", sa.Text(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("artists", sa.JSON(), nullable=False),
        sa.Column("album_name", sa.String(length=500), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("isrc", sa.String(length=20), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
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
        sa.UniqueConstraint("platform", "platform_id", name="uq_songs_platform_id"),
    )
    op.create_index(op.f("ix_songs_platform"), "songs", ["platform"], unique=False)
    op.create_index(op.f("ix_songs_platform_id"), "songs", ["platform_id"], unique=False)
    op.create_index(op.f("ix_songs_isrc"), "songs", ["isrc"], unique=False)

    # Create matches table
    op.create_table(
        "matches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_song_id", sa.UUID(), nullable=True),
        sa.Column("source_platform", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("target_platform", sa.String(length=50), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("match_type", sa.String(length=20), nullable=False, default="system"),
        sa.Column("match_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("upvotes", sa.Integer(), nullable=False, default=0),
        sa.Column("downvotes", sa.Integer(), nullable=False, default=0),
        sa.Column("submitted_by", sa.UUID(), nullable=True),
        sa.Column("verified_by", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["source_song_id"],
            ["songs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["verified_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_url",
            "target_platform",
            "target_url",
            name="uq_matches_source_target",
        ),
    )
    op.create_index(
        op.f("ix_matches_source_song_id"), "matches", ["source_song_id"], unique=False
    )
    op.create_index(
        op.f("ix_matches_source_platform"), "matches", ["source_platform"], unique=False
    )
    op.create_index(
        op.f("ix_matches_source_url"), "matches", ["source_url"], unique=False
    )
    op.create_index(
        op.f("ix_matches_target_platform"), "matches", ["target_platform"], unique=False
    )

    # Create votes table
    op.create_table(
        "votes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("match_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("vote_type", sa.String(length=4), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["matches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", "user_id", name="uq_votes_match_user"),
    )
    op.create_index(op.f("ix_votes_match_id"), "votes", ["match_id"], unique=False)
    op.create_index(op.f("ix_votes_user_id"), "votes", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("votes")
    op.drop_table("matches")
    op.drop_table("songs")
    op.drop_table("users")
