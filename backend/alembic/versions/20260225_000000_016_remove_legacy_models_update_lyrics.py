"""Remove legacy models and update lyrics to unified entities.

Revision ID: 016_remove_legacy_models_update_lyrics
Revises: 015_unified_entity_architecture
Create Date: 2026-02-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "016_remove_legacy_models_update_lyrics"
down_revision: str | None = "015_unified_entity_architecture"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_TABLES = [
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


def _col_exists(bind: sa.engine.Connection, table: str, column: str) -> bool:
    row = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns"
            " WHERE table_name = :t AND column_name = :c"
        ).bindparams(t=table, c=column)
    ).fetchone()
    return row is not None


def _pg_constraint_exists(bind: sa.engine.Connection, name: str) -> bool:
    row = bind.execute(
        sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n").bindparams(n=name)
    ).fetchone()
    return row is not None



def _upgrade_postgresql(bind: sa.engine.Connection) -> None:
    """Migrate lyrics and drop legacy tables on PostgreSQL using raw SQL.

    Uses raw SQL throughout to avoid SQLAlchemy Inspector caching issues
    and to benefit from PostgreSQL's native IF EXISTS / IF NOT EXISTS support.
    """

    def exe(sql: str) -> None:
        bind.execute(sa.text(sql))

    # -------------------------------------------------------------------------
    # 1. Migrate lyrics: song_id → entity_id
    # -------------------------------------------------------------------------
    if _col_exists(bind, "lyrics", "song_id"):
        # Clear lyrics — they reference songs which are about to be dropped.
        exe("DELETE FROM lyrics")

        # Add new columns (IF NOT EXISTS is safe on repeated runs).
        exe("ALTER TABLE lyrics ADD COLUMN IF NOT EXISTS entity_id UUID")
        exe("ALTER TABLE lyrics ADD COLUMN IF NOT EXISTS upvotes INTEGER NOT NULL DEFAULT 0")
        exe("ALTER TABLE lyrics ADD COLUMN IF NOT EXISTS downvotes INTEGER NOT NULL DEFAULT 0")
        exe(
            "ALTER TABLE lyrics"
            " ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'suggested'"
        )

        # Drop old constraints / indexes before dropping the column.
        exe("ALTER TABLE lyrics DROP CONSTRAINT IF EXISTS uq_lyrics_song_source")
        exe("ALTER TABLE lyrics DROP CONSTRAINT IF EXISTS lyrics_song_id_fkey")
        exe("DROP INDEX IF EXISTS ix_lyrics_song_id")
        exe("ALTER TABLE lyrics DROP COLUMN IF EXISTS song_id")

    # -------------------------------------------------------------------------
    # 2. Finalise entity_id (set NOT NULL, add index / FK / unique constraint).
    # -------------------------------------------------------------------------
    if _col_exists(bind, "lyrics", "entity_id"):
        exe("ALTER TABLE lyrics ALTER COLUMN entity_id SET NOT NULL")
        exe("CREATE INDEX IF NOT EXISTS ix_lyrics_entity_id ON lyrics(entity_id)")
        exe("CREATE INDEX IF NOT EXISTS ix_lyrics_source ON lyrics(source)")

        if not _pg_constraint_exists(bind, "lyrics_entity_id_fkey"):
            exe(
                "ALTER TABLE lyrics ADD CONSTRAINT lyrics_entity_id_fkey"
                " FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE"
            )
        if not _pg_constraint_exists(bind, "uq_lyrics_entity_source"):
            exe(
                "ALTER TABLE lyrics ADD CONSTRAINT uq_lyrics_entity_source"
                " UNIQUE (entity_id, source)"
            )

    # -------------------------------------------------------------------------
    # 3. Drop legacy tables (CASCADE removes dependent FKs automatically).
    # -------------------------------------------------------------------------
    for table in _LEGACY_TABLES:
        bind.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))


def _upgrade_sqlite(bind: sa.engine.Connection) -> None:
    """Migrate lyrics and drop legacy tables on SQLite."""
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # --- Lyrics: song_id → entity_id ---
    if "lyrics" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("lyrics")}

        if "song_id" in existing_cols:
            op.execute(sa.text("DELETE FROM lyrics"))

            # Collect constraints to drop before entering the batch.
            existing_uq = {c["name"] for c in inspector.get_unique_constraints("lyrics")}
            existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("lyrics")}
            existing_idx = {idx["name"] for idx in inspector.get_indexes("lyrics")}

            with op.batch_alter_table("lyrics") as batch_op:
                if "entity_id" not in existing_cols:
                    batch_op.add_column(sa.Column("entity_id", sa.String(36), nullable=True))
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
                if "uq_lyrics_song_source" in existing_uq:
                    batch_op.drop_constraint("uq_lyrics_song_source", type_="unique")
                if "lyrics_song_id_fkey" in existing_fks:
                    batch_op.drop_constraint("lyrics_song_id_fkey", type_="foreignkey")
                if "ix_lyrics_song_id" in existing_idx:
                    batch_op.drop_index("ix_lyrics_song_id")
                batch_op.drop_column("song_id")

        # Re-inspect after the first batch (fresh inspector — no cache).
        inspector2 = sa.inspect(bind)
        existing_cols2 = {c["name"] for c in inspector2.get_columns("lyrics")}
        existing_idx2 = {idx["name"] for idx in inspector2.get_indexes("lyrics")}
        existing_fks2 = {fk["name"] for fk in inspector2.get_foreign_keys("lyrics")}
        existing_uq2 = {c["name"] for c in inspector2.get_unique_constraints("lyrics")}

        if "entity_id" in existing_cols2:
            with op.batch_alter_table("lyrics") as batch_op:
                batch_op.alter_column("entity_id", nullable=False)
                if "ix_lyrics_entity_id" not in existing_idx2:
                    batch_op.create_index("ix_lyrics_entity_id", ["entity_id"], unique=False)
                if "lyrics_entity_id_fkey" not in existing_fks2:
                    batch_op.create_foreign_key(
                        "lyrics_entity_id_fkey",
                        "entities",
                        ["entity_id"],
                        ["id"],
                        ondelete="CASCADE",
                    )
                if "uq_lyrics_entity_source" not in existing_uq2:
                    batch_op.create_unique_constraint(
                        "uq_lyrics_entity_source", ["entity_id", "source"]
                    )

    # --- Drop legacy tables ---
    for table in _LEGACY_TABLES:
        if table in existing_tables:
            # Drop all indexes first (SQLite doesn't support CASCADE on DROP TABLE).
            idx_inspector = sa.inspect(bind)
            table_indexes = [idx["name"] for idx in idx_inspector.get_indexes(table)]
            if table_indexes:
                with op.batch_alter_table(table) as batch_op:
                    for idx_name in table_indexes:
                        batch_op.drop_index(idx_name)
            op.drop_table(table)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _upgrade_postgresql(bind)
    else:
        _upgrade_sqlite(bind)


def downgrade() -> None:
    pass
