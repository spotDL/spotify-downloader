"""Add download features settings to user_settings.

Adds SponsorBlock, LRC, M3U, archive, overwrite modes, proxy,
custom args, and other download-related settings. Also renames
overwrite_existing (bool) to overwrite (str) and embed_cover_art
to embed_cover for CLI consistency.

Revision ID: 014_download_features
Revises: 013_appearance_settings
Create Date: 2025-02-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "014_download_features"
down_revision: Union[str, None] = "013_appearance_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add download features columns and rename overwrite/embed_cover."""
    # Rename overwrite_existing (bool) -> overwrite (str)
    # SQLite doesn't support ALTER COLUMN, so we add new + copy + drop old
    op.add_column(
        "user_settings",
        sa.Column("overwrite", sa.String(10), nullable=False, server_default="skip"),
    )
    # Migrate data: True -> "force", False -> "skip"
    op.execute(
        "UPDATE user_settings SET overwrite = CASE "
        "WHEN overwrite_existing = true THEN 'force' "
        "ELSE 'skip' END"
    )
    op.drop_column("user_settings", "overwrite_existing")

    # Rename embed_cover_art -> embed_cover
    op.add_column(
        "user_settings",
        sa.Column("embed_cover", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.execute("UPDATE user_settings SET embed_cover = embed_cover_art")
    op.drop_column("user_settings", "embed_cover_art")

    # New download settings
    op.add_column(
        "user_settings",
        sa.Column("bitrate", sa.String(20), nullable=True),
    )
    op.add_column(
        "user_settings",
        sa.Column("max_filename_length", sa.Integer(), nullable=False, server_default="255"),
    )
    op.add_column(
        "user_settings",
        sa.Column("restrict", sa.String(10), nullable=True),
    )
    op.add_column(
        "user_settings",
        sa.Column("id3_separator", sa.String(5), nullable=False, server_default="/"),
    )

    # SponsorBlock
    op.add_column(
        "user_settings",
        sa.Column("sponsor_block", sa.Boolean(), nullable=False, server_default="false"),
    )

    # LRC
    op.add_column(
        "user_settings",
        sa.Column("generate_lrc", sa.Boolean(), nullable=False, server_default="false"),
    )

    # M3U
    op.add_column(
        "user_settings",
        sa.Column("m3u", sa.String(255), nullable=True),
    )

    # Archive
    op.add_column(
        "user_settings",
        sa.Column("archive", sa.String(500), nullable=True),
    )

    # Content filtering
    op.add_column(
        "user_settings",
        sa.Column("skip_explicit", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "user_settings",
        sa.Column("scan_for_songs", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Playlist options
    op.add_column(
        "user_settings",
        sa.Column("playlist_numbering", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "user_settings",
        sa.Column("fetch_albums", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Proxy
    op.add_column(
        "user_settings",
        sa.Column("proxy", sa.String(500), nullable=True),
    )

    # Custom arguments
    op.add_column(
        "user_settings",
        sa.Column("ffmpeg_args", sa.String(500), nullable=True),
    )
    op.add_column(
        "user_settings",
        sa.Column("yt_dlp_args", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    """Remove download features columns and restore old names."""
    op.drop_column("user_settings", "yt_dlp_args")
    op.drop_column("user_settings", "ffmpeg_args")
    op.drop_column("user_settings", "proxy")
    op.drop_column("user_settings", "fetch_albums")
    op.drop_column("user_settings", "playlist_numbering")
    op.drop_column("user_settings", "scan_for_songs")
    op.drop_column("user_settings", "skip_explicit")
    op.drop_column("user_settings", "archive")
    op.drop_column("user_settings", "m3u")
    op.drop_column("user_settings", "generate_lrc")
    op.drop_column("user_settings", "sponsor_block")
    op.drop_column("user_settings", "id3_separator")
    op.drop_column("user_settings", "restrict")
    op.drop_column("user_settings", "max_filename_length")
    op.drop_column("user_settings", "bitrate")

    # Restore embed_cover_art from embed_cover
    op.add_column(
        "user_settings",
        sa.Column("embed_cover_art", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.execute("UPDATE user_settings SET embed_cover_art = embed_cover")
    op.drop_column("user_settings", "embed_cover")

    # Restore overwrite_existing from overwrite
    op.add_column(
        "user_settings",
        sa.Column("overwrite_existing", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.execute(
        "UPDATE user_settings SET overwrite_existing = CASE "
        "WHEN overwrite = 'force' THEN true "
        "ELSE false END"
    )
    op.drop_column("user_settings", "overwrite")
