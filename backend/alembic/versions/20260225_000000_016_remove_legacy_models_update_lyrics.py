"""Remove legacy models and update lyrics to unified entities.

Revision ID: 016_remove_legacy_models_update_lyrics
Revises: 015_unified_entity_architecture
Create Date: 2026-02-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "016_remove_legacy_models_update_lyrics"
down_revision: str | None = "015_unified_entity_architecture"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    uuid_type = postgresql.UUID(as_uuid=True) if dialect == "postgresql" else sa.String(36)

    # 1. Update lyrics table
    op.execute("DELETE FROM lyrics")
    
    with op.batch_alter_table("lyrics") as batch_op:
        batch_op.add_column(sa.Column('entity_id', uuid_type, nullable=True))
        batch_op.add_column(sa.Column('upvotes', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('downvotes', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('status', sa.String(length=32), server_default='suggested', nullable=False))
        
        # In SQLite, constraint names might be slightly different or need named conventions.
        # We will wrap dropping constraints in try-except for safety across DBs if needed, 
        # but typical declarative setup names them.
        batch_op.drop_constraint('uq_lyrics_song_source', type_='unique')
        batch_op.drop_constraint('lyrics_song_id_fkey', type_='foreignkey')
        batch_op.drop_index('ix_lyrics_song_id')
        batch_op.drop_column('song_id')

    with op.batch_alter_table("lyrics") as batch_op:
        batch_op.alter_column('entity_id', nullable=False)
        batch_op.create_index('ix_lyrics_entity_id', ['entity_id'], unique=False)
        batch_op.create_foreign_key('lyrics_entity_id_fkey', 'entities', ['entity_id'], ['id'], ondelete='CASCADE')
        batch_op.create_unique_constraint('uq_lyrics_entity_source', ['entity_id', 'source'])

    # 2. Drop legacy tables
    
    with op.batch_alter_table("matches") as batch_op:
        batch_op.drop_index('ix_matches_platform_id')
        batch_op.drop_index('ix_matches_source_song_id')
    op.drop_table('matches')

    with op.batch_alter_table("metadata_snapshots") as batch_op:
        batch_op.drop_index('ix_metadata_snapshots_song_id')
        batch_op.drop_index('ix_metadata_snapshots_source')
    op.drop_table('metadata_snapshots')

    with op.batch_alter_table("playlist_tracks") as batch_op:
        batch_op.drop_index('ix_playlist_tracks_playlist_id')
        batch_op.drop_index('ix_playlist_tracks_song_id')
    op.drop_table('playlist_tracks')
    
    with op.batch_alter_table("songs") as batch_op:
        batch_op.drop_index('ix_songs_album_id')
        batch_op.drop_index('ix_songs_artist_id')
        batch_op.drop_index('ix_songs_discogs_id')
        batch_op.drop_index('ix_songs_isrc')
        batch_op.drop_index('ix_songs_musicbrainz_id')
        batch_op.drop_index('ix_songs_platform')
        batch_op.drop_index('ix_songs_platform_id')
    op.drop_table('songs')

    with op.batch_alter_table("album_platform_links") as batch_op:
        batch_op.drop_index('ix_album_platform_links_album_id')
        batch_op.drop_index('ix_album_platform_links_platform')
        batch_op.drop_index('ix_album_platform_links_platform_id')
    op.drop_table('album_platform_links')

    with op.batch_alter_table("albums") as batch_op:
        batch_op.drop_index('ix_albums_artist_id')
        batch_op.drop_index('ix_albums_name_normalized')
    op.drop_table('albums')

    with op.batch_alter_table("artist_platform_links") as batch_op:
        batch_op.drop_index('ix_artist_platform_links_artist_id')
        batch_op.drop_index('ix_artist_platform_links_platform')
        batch_op.drop_index('ix_artist_platform_links_platform_id')
    op.drop_table('artist_platform_links')

    with op.batch_alter_table("artists") as batch_op:
        batch_op.drop_index('ix_artists_name_normalized')
    op.drop_table('artists')

    with op.batch_alter_table("playlist_platform_links") as batch_op:
        batch_op.drop_index('ix_playlist_platform_links_platform')
        batch_op.drop_index('ix_playlist_platform_links_platform_id')
        batch_op.drop_index('ix_playlist_platform_links_playlist_id')
    op.drop_table('playlist_platform_links')

    op.drop_table('playlists')

def downgrade() -> None:
    pass
