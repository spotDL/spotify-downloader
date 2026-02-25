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
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    uuid_type = postgresql.UUID(as_uuid=True) if dialect == "postgresql" else sa.String(36)

    # 1. Migrate lyrics table from song_id -> entity_id
    if "lyrics" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("lyrics")}

        if "song_id" in existing_cols:
            # Clear existing lyrics — they reference songs which are about to be dropped.
            op.execute("DELETE FROM lyrics")

            with op.batch_alter_table("lyrics") as batch_op:
                if "entity_id" not in existing_cols:
                    batch_op.add_column(sa.Column("entity_id", uuid_type, nullable=True))
                if "upvotes" not in existing_cols:
                    batch_op.add_column(
                        sa.Column("upvotes", sa.Integer(), server_default="0", nullable=False)
                    )
                if "downvotes" not in existing_cols:
                    batch_op.add_column(
                        sa.Column("downvotes", sa.Integer(), server_default="0", nullable=False)
                    )
                if "status" not in existing_cols:
                    batch_op.add_column(
                        sa.Column(
                            "status",
                            sa.String(length=32),
                            server_default="suggested",
                            nullable=False,
                        )
                    )

                # Drop the old unique constraint if present.
                existing_uq = {
                    c["name"] for c in inspector.get_unique_constraints("lyrics")
                }
                if "uq_lyrics_song_source" in existing_uq:
                    batch_op.drop_constraint("uq_lyrics_song_source", type_="unique")

                # Drop the old FK if present.
                existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("lyrics")}
                if "lyrics_song_id_fkey" in existing_fks:
                    batch_op.drop_constraint("lyrics_song_id_fkey", type_="foreignkey")

                # Drop the old index on song_id if present.
                existing_idx = {idx["name"] for idx in inspector.get_indexes("lyrics")}
                if "ix_lyrics_song_id" in existing_idx:
                    batch_op.drop_index("ix_lyrics_song_id")

                batch_op.drop_column("song_id")

        # Re-inspect after the first batch to reflect new column state.
        existing_cols2 = {c["name"] for c in inspector.get_columns("lyrics")}

        if "entity_id" in existing_cols2:
            with op.batch_alter_table("lyrics") as batch_op:
                batch_op.alter_column("entity_id", nullable=False)

                existing_idx2 = {idx["name"] for idx in inspector.get_indexes("lyrics")}
                if "ix_lyrics_entity_id" not in existing_idx2:
                    batch_op.create_index("ix_lyrics_entity_id", ["entity_id"], unique=False)

                existing_fks2 = {fk["name"] for fk in inspector.get_foreign_keys("lyrics")}
                if "lyrics_entity_id_fkey" not in existing_fks2:
                    batch_op.create_foreign_key(
                        "lyrics_entity_id_fkey",
                        "entities",
                        ["entity_id"],
                        ["id"],
                        ondelete="CASCADE",
                    )

                existing_uq2 = {
                    c["name"] for c in inspector.get_unique_constraints("lyrics")
                }
                if "uq_lyrics_entity_source" not in existing_uq2:
                    batch_op.create_unique_constraint(
                        "uq_lyrics_entity_source", ["entity_id", "source"]
                    )

    # 2. Drop legacy tables.
    # On PostgreSQL, DROP TABLE ... CASCADE removes all dependent indexes, FKs, and
    # referencing rows automatically so no explicit index/FK cleanup is needed.
    # We also drop `votes` which has a FK into `matches`.
    legacy_tables = [
        "playlist_tracks",
        "metadata_snapshots",
        "matches",
        "votes",
        "songs",
        "album_platform_links",
        "albums",
        "artist_platform_links",
        "artists",
        "playlist_platform_links",
        "playlists",
    ]

    if dialect == "postgresql":
        for table in legacy_tables:
            op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    else:
        # SQLite does not support CASCADE on DROP TABLE; drop dependents first.
        for table in legacy_tables:
            if table in existing_tables:
                for idx in inspector.get_indexes(table):
                    with op.batch_alter_table(table) as batch_op:
                        batch_op.drop_index(idx["name"])
                op.drop_table(table)


def downgrade() -> None:
    pass
