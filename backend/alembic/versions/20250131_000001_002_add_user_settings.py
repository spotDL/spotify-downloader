"""Add user_settings table

Revision ID: 002
Revises: 001
Create Date: 2025-01-31 00:00:01.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_settings table
    op.create_table(
        "user_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        # Download settings
        sa.Column("audio_format", sa.String(length=10), nullable=False, server_default="mp3"),
        sa.Column("audio_quality", sa.String(length=10), nullable=False, server_default="best"),
        sa.Column("output_template", sa.String(length=255), nullable=False, server_default="{artist} - {title}"),
        sa.Column("output_directory", sa.String(length=500), nullable=True),
        sa.Column("max_concurrent_downloads", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("overwrite_existing", sa.Boolean(), nullable=False, server_default="false"),
        # Metadata settings
        sa.Column("embed_metadata", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("embed_lyrics", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("embed_cover_art", sa.Boolean(), nullable=False, server_default="true"),
        # Spotify credentials
        sa.Column("spotify_client_id", sa.String(length=255), nullable=True),
        sa.Column("spotify_client_secret", sa.String(length=255), nullable=True),
        sa.Column("spotify_user_auth", sa.Boolean(), nullable=False, server_default="false"),
        # Server settings
        sa.Column("api_url", sa.String(length=500), nullable=False, server_default="http://localhost:8000"),
        sa.Column("api_timeout", sa.Float(), nullable=False, server_default="30.0"),
        sa.Column("offline_mode", sa.Boolean(), nullable=False, server_default="false"),
        # Matching thresholds
        sa.Column("name_match_threshold", sa.Float(), nullable=False, server_default="60.0"),
        sa.Column("artist_match_threshold", sa.Float(), nullable=False, server_default="70.0"),
        sa.Column("time_match_threshold", sa.Float(), nullable=False, server_default="25.0"),
        # Advanced settings
        sa.Column("log_level", sa.String(length=10), nullable=False, server_default="INFO"),
        sa.Column("cookie_file", sa.String(length=500), nullable=True),
        sa.Column("custom_settings", sa.Text(), nullable=True),
        # Timestamps
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_settings_user_id"), "user_settings", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_settings_user_id"), table_name="user_settings")
    op.drop_table("user_settings")
