"""Rekey track entities: ISRC-first entity key, drop ISRC from fallback key.

Previously track entity keys used the format:
    track:{name}:{artist}:{duration_bucket}:{isrc}

This caused duplicate entities when the same track was discovered with and
without an ISRC (the two forms produced different keys → different rows → two
`contains` relations from the album, i.e. duplicate tracks on album/artist pages).

New format:
  - With ISRC   → track:{isrc}           (globally unique, provider-agnostic)
  - Without ISRC → track:{name}:{artist}:{duration_bucket}  (no empty suffix)

This migration renames all existing entity_key values in the `entities` table.
After renaming, rows whose new key would collide with an already-renamed row are
merged: the surviving row keeps the lower UUID (stable merge), all relations and
snapshots that pointed at the deleted row are re-targeted, and the duplicate row
is deleted.

Revision ID: 017_rekey_track_entities
Revises: 016_remove_legacy_models_update_lyrics
Create Date: 2026-02-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "017_rekey_track_entities"
down_revision: str | None = "016_drop_legacy_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Fetch all track entities with their current key + canonical JSON
    # ------------------------------------------------------------------
    rows = conn.execute(
        sa.text(
            """
            SELECT id, entity_key,
                   canonical->>'isrc'     AS isrc,
                   canonical->>'name'     AS name,
                   canonical->>'artist'   AS artist,
                   (canonical->>'duration')::float AS duration
            FROM entities
            WHERE entity_type = 'track'
            ORDER BY id
            """
        )
    ).fetchall()

    def _slug(s: str) -> str:
        import re
        if not s:
            return ""
        s = s.lower().strip()
        s = re.sub(r"[^a-z0-9]+", "-", s)
        return s.strip("-")

    def new_key(isrc: str | None, name: str | None, artist: str | None, duration: float | None) -> str:
        isrc_slug = _slug(isrc or "")
        if isrc_slug:
            return f"track:{isrc_slug}"
        name_slug = _slug(name or "unknown")
        artist_slug = _slug(artist or "unknown")
        dur = int(duration or 0)
        bucket = int(round(dur / 5.0) * 5) if dur > 0 else 0
        return f"track:{name_slug}:{artist_slug}:{bucket}"

    # Build mapping: old_key → new_key, indexed by id
    updates: list[tuple[str, str, str]] = []  # (id, old_key, computed_new_key)
    for row in rows:
        nk = new_key(row.isrc, row.name, row.artist, row.duration)
        updates.append((str(row.id), row.entity_key, nk))

    # ------------------------------------------------------------------
    # 2. Apply key renames, merging any collisions
    # ------------------------------------------------------------------
    # Track which new_key is already in the DB (keyed by new_key → survivor id)
    occupied: dict[str, str] = {}  # new_key → id of entity already using it

    # Pre-populate with rows whose new_key didn't change (they already own it)
    unchanged = {uid for uid, old_k, new_k in updates if old_k == new_k}
    for uid, old_k, new_k in updates:
        if uid in unchanged:
            occupied[new_k] = uid

    for uid, old_k, new_k in updates:
        if old_k == new_k:
            continue  # nothing to do

        if new_k not in occupied:
            # Simple rename
            conn.execute(
                sa.text("UPDATE entities SET entity_key = :nk WHERE id = :id"),
                {"nk": new_k, "id": uid},
            )
            occupied[new_k] = uid
        else:
            # Collision: merge this row into the survivor
            survivor_id = occupied[new_k]

            # Re-target snapshots
            conn.execute(
                sa.text(
                    "UPDATE entity_snapshots SET entity_id = :s WHERE entity_id = :d"
                ),
                {"s": survivor_id, "d": uid},
            )
            # Re-target provenance
            conn.execute(
                sa.text(
                    "UPDATE entity_field_provenance SET entity_id = :s WHERE entity_id = :d"
                ),
                {"s": survivor_id, "d": uid},
            )
            # Re-target outgoing relations (avoid creating duplicates)
            conn.execute(
                sa.text(
                    """
                    UPDATE entity_relations SET from_entity_id = :s
                    WHERE from_entity_id = :d
                      AND NOT EXISTS (
                          SELECT 1 FROM entity_relations er2
                          WHERE er2.from_entity_id = :s
                            AND er2.to_entity_id   = entity_relations.to_entity_id
                            AND er2.relation_type  = entity_relations.relation_type
                      )
                    """
                ),
                {"s": survivor_id, "d": uid},
            )
            conn.execute(
                sa.text(
                    "DELETE FROM entity_relations WHERE from_entity_id = :d"
                ),
                {"d": uid},
            )
            # Re-target incoming relations
            conn.execute(
                sa.text(
                    """
                    UPDATE entity_relations SET to_entity_id = :s
                    WHERE to_entity_id = :d
                      AND NOT EXISTS (
                          SELECT 1 FROM entity_relations er2
                          WHERE er2.from_entity_id = entity_relations.from_entity_id
                            AND er2.to_entity_id   = :s
                            AND er2.relation_type  = entity_relations.relation_type
                      )
                    """
                ),
                {"s": survivor_id, "d": uid},
            )
            conn.execute(
                sa.text(
                    "DELETE FROM entity_relations WHERE to_entity_id = :d"
                ),
                {"d": uid},
            )
            # Delete the duplicate entity (cascade handles leftover snapshots/provenance)
            conn.execute(
                sa.text("DELETE FROM entities WHERE id = :d"),
                {"d": uid},
            )


def downgrade() -> None:
    # Reversing the merge step is not feasible (merged duplicates are gone).
    # We can restore the key format for surviving entities, but merged data
    # cannot be recovered.
    conn = op.get_bind()

    rows = conn.execute(
        sa.text(
            """
            SELECT id, entity_key,
                   canonical->>'isrc'   AS isrc,
                   canonical->>'name'   AS name,
                   canonical->>'artist' AS artist,
                   (canonical->>'duration')::float AS duration
            FROM entities
            WHERE entity_type = 'track'
            """
        )
    ).fetchall()

    import re

    def _slug(s: str) -> str:
        if not s:
            return ""
        s = s.lower().strip()
        s = re.sub(r"[^a-z0-9]+", "-", s)
        return s.strip("-")

    for row in rows:
        name_slug = _slug(row.name or "unknown")
        artist_slug = _slug(row.artist or "unknown")
        dur = int(row.duration or 0)
        bucket = int(round(dur / 5.0) * 5) if dur > 0 else 0
        isrc_slug = _slug(row.isrc or "")
        old_key = f"track:{name_slug}:{artist_slug}:{bucket}:{isrc_slug}"
        conn.execute(
            sa.text("UPDATE entities SET entity_key = :k WHERE id = :id"),
            {"k": old_key, "id": str(row.id)},
        )
