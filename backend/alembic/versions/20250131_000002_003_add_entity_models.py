"""Add entity models (Artist, Album, Playlist) with platform links

Revision ID: 003
Revises: 002
Create Date: 2025-01-31 00:00:02.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create artists table
    op.create_table(
        "artists",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("name_normalized", sa.String(length=500), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("genres", sa.JSON(), nullable=False, server_default="[]"),
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
    )
    op.create_index(
        op.f("ix_artists_name_normalized"), "artists", ["name_normalized"], unique=False
    )

    # Create artist_platform_links table
    op.create_table(
        "artist_platform_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("artist_id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("platform_id", sa.String(length=255), nullable=False),
        sa.Column("platform_url", sa.Text(), nullable=False),
        sa.Column("followers", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("platform", "platform_id", name="uq_artist_platform_link"),
    )
    op.create_index(
        op.f("ix_artist_platform_links_artist_id"),
        "artist_platform_links",
        ["artist_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_artist_platform_links_platform"),
        "artist_platform_links",
        ["platform"],
        unique=False,
    )
    op.create_index(
        op.f("ix_artist_platform_links_platform_id"),
        "artist_platform_links",
        ["platform_id"],
        unique=False,
    )

    # Create albums table
    op.create_table(
        "albums",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("name_normalized", sa.String(length=500), nullable=False),
        sa.Column("artist_id", sa.UUID(), nullable=True),
        sa.Column("artist_name", sa.String(length=500), nullable=False),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("total_tracks", sa.Integer(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"], ondelete="SET NULL"),
    )
    op.create_index(
        op.f("ix_albums_name_normalized"), "albums", ["name_normalized"], unique=False
    )
    op.create_index(op.f("ix_albums_artist_id"), "albums", ["artist_id"], unique=False)

    # Create album_platform_links table
    op.create_table(
        "album_platform_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("album_id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("platform_id", sa.String(length=255), nullable=False),
        sa.Column("platform_url", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("platform", "platform_id", name="uq_album_platform_link"),
    )
    op.create_index(
        op.f("ix_album_platform_links_album_id"),
        "album_platform_links",
        ["album_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_album_platform_links_platform"),
        "album_platform_links",
        ["platform"],
        unique=False,
    )
    op.create_index(
        op.f("ix_album_platform_links_platform_id"),
        "album_platform_links",
        ["platform_id"],
        unique=False,
    )

    # Create playlists table
    op.create_table(
        "playlists",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("name_normalized", sa.String(length=500), nullable=False),
        sa.Column("owner_name", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.Column("total_tracks", sa.Integer(), nullable=False, server_default="0"),
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
    )
    op.create_index(
        op.f("ix_playlists_name_normalized"),
        "playlists",
        ["name_normalized"],
        unique=False,
    )

    # Create playlist_platform_links table
    op.create_table(
        "playlist_platform_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("playlist_id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("platform_id", sa.String(length=255), nullable=False),
        sa.Column("platform_url", sa.Text(), nullable=False),
        sa.Column("followers", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "platform", "platform_id", name="uq_playlist_platform_link"
        ),
    )
    op.create_index(
        op.f("ix_playlist_platform_links_playlist_id"),
        "playlist_platform_links",
        ["playlist_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_playlist_platform_links_platform"),
        "playlist_platform_links",
        ["platform"],
        unique=False,
    )
    op.create_index(
        op.f("ix_playlist_platform_links_platform_id"),
        "playlist_platform_links",
        ["platform_id"],
        unique=False,
    )

    # Create playlist_tracks table
    op.create_table(
        "playlist_tracks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("playlist_id", sa.UUID(), nullable=False),
        sa.Column("song_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("playlist_id", "position", name="uq_playlist_track_position"),
    )
    op.create_index(
        op.f("ix_playlist_tracks_playlist_id"),
        "playlist_tracks",
        ["playlist_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_playlist_tracks_song_id"),
        "playlist_tracks",
        ["song_id"],
        unique=False,
    )

    # Add artist_id and album_id columns to songs table
    op.add_column("songs", sa.Column("artist_id", sa.UUID(), nullable=True))
    op.add_column("songs", sa.Column("album_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_songs_artist_id",
        "songs",
        "artists",
        ["artist_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_songs_album_id",
        "songs",
        "albums",
        ["album_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_songs_artist_id"), "songs", ["artist_id"], unique=False)
    op.create_index(op.f("ix_songs_album_id"), "songs", ["album_id"], unique=False)


def downgrade() -> None:
    # Remove foreign keys and columns from songs
    op.drop_index(op.f("ix_songs_album_id"), table_name="songs")
    op.drop_index(op.f("ix_songs_artist_id"), table_name="songs")
    op.drop_constraint("fk_songs_album_id", "songs", type_="foreignkey")
    op.drop_constraint("fk_songs_artist_id", "songs", type_="foreignkey")
    op.drop_column("songs", "album_id")
    op.drop_column("songs", "artist_id")

    # Drop playlist_tracks
    op.drop_index(op.f("ix_playlist_tracks_song_id"), table_name="playlist_tracks")
    op.drop_index(op.f("ix_playlist_tracks_playlist_id"), table_name="playlist_tracks")
    op.drop_table("playlist_tracks")

    # Drop playlist_platform_links
    op.drop_index(
        op.f("ix_playlist_platform_links_platform_id"),
        table_name="playlist_platform_links",
    )
    op.drop_index(
        op.f("ix_playlist_platform_links_platform"),
        table_name="playlist_platform_links",
    )
    op.drop_index(
        op.f("ix_playlist_platform_links_playlist_id"),
        table_name="playlist_platform_links",
    )
    op.drop_table("playlist_platform_links")

    # Drop playlists
    op.drop_index(op.f("ix_playlists_name_normalized"), table_name="playlists")
    op.drop_table("playlists")

    # Drop album_platform_links
    op.drop_index(
        op.f("ix_album_platform_links_platform_id"),
        table_name="album_platform_links",
    )
    op.drop_index(
        op.f("ix_album_platform_links_platform"),
        table_name="album_platform_links",
    )
    op.drop_index(
        op.f("ix_album_platform_links_album_id"),
        table_name="album_platform_links",
    )
    op.drop_table("album_platform_links")

    # Drop albums
    op.drop_index(op.f("ix_albums_artist_id"), table_name="albums")
    op.drop_index(op.f("ix_albums_name_normalized"), table_name="albums")
    op.drop_table("albums")

    # Drop artist_platform_links
    op.drop_index(
        op.f("ix_artist_platform_links_platform_id"),
        table_name="artist_platform_links",
    )
    op.drop_index(
        op.f("ix_artist_platform_links_platform"),
        table_name="artist_platform_links",
    )
    op.drop_index(
        op.f("ix_artist_platform_links_artist_id"),
        table_name="artist_platform_links",
    )
    op.drop_table("artist_platform_links")

    # Drop artists
    op.drop_index(op.f("ix_artists_name_normalized"), table_name="artists")
    op.drop_table("artists")
