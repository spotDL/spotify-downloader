"""Provider-snapshot repository: the permanent metadata cache + external-ID map.

One row per ``(provider, provider_entity_id)``. ``upsert`` is a portable
select-then-insert/update keyed on that unique constraint — deliberately not a
dialect-specific ``ON CONFLICT`` so a single code path serves SQLite and
Postgres alike.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from spotdl_core.model import EntityType, ProviderId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.models import EntityLink, ProviderSnapshot

#: Payload marker set by preview writers on a LISTING-derived track snapshot
#: (search hits, album/playlist/top-tracks rows). ``ResolveService`` treats a
#: partial snapshot as a cache miss, so a track's first direct open performs the
#: authoritative provider fetch AND the cross-provider enrichment fan-out (whose
#: persist overwrites the payload, clearing the marker) — a preview must never
#: leave a track single-source or ISRC-less.
PARTIAL_MARKER = "partial"


def is_partial(snapshot: ProviderSnapshot) -> bool:
    """True when ``snapshot`` is a marked-partial listing preview (see marker doc)."""
    payload = snapshot.raw_payload
    return isinstance(payload, dict) and bool(payload.get(PARTIAL_MARKER))


def _fill_payload(existing: Any, incoming: Any) -> Any:
    """Merge a preview payload into an existing one, filling gaps only.

    Every existing key wins unless its value is a null gap (``None`` / ``[]`` /
    ``""``), in which case a non-null incoming value fills it. Keys only the
    incoming payload knows are added — except :data:`PARTIAL_MARKER`, a writer
    lifecycle flag that must never be grafted onto an already-full snapshot.
    Non-dict payloads keep the existing value.
    """
    if not isinstance(existing, dict) or not isinstance(incoming, dict):
        return existing
    merged = dict(existing)
    for key, value in incoming.items():
        if value is None or key == PARTIAL_MARKER:
            continue
        current = merged.get(key)
        if current is None or current == [] or current == "":
            merged[key] = value
    return merged


def _as_aware(value: datetime) -> datetime:
    """Coerce a possibly-naive datetime to aware UTC.

    SQLite drops ``tzinfo`` on read even for ``DateTime(timezone=True)`` columns,
    so freshness comparisons normalize both operands to aware UTC.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class SnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        *,
        provider: ProviderId,
        provider_entity_id: str,
        entity_type: EntityType,
        raw_payload: Any,
        name: str | None = None,
        isrc: str | None = None,
        duration_ms: int | None = None,
        artist_names: list[str] | None = None,
        album_name: str | None = None,
        art_url: str | None = None,
        expires_at: datetime | None = None,
        fill_only: bool = False,
    ) -> ProviderSnapshot:
        """Create or refresh the snapshot for ``(provider, provider_entity_id)``.

        The default (authoritative) mode refreshes ``raw_payload``, the normalized
        key fields, and ``fetched_at`` on an existing row; inserts otherwise.

        ``fill_only=True`` is the PREVIEW writer's mode (search hits, discography
        refs, container track listings): a preview may be *sparser* than what a
        full resolve already persisted, so it must never clobber. On an existing
        row it only fills gaps — payload keys the row lacks (or holds as
        null/empty) and normalized columns that are ``None`` — and leaves
        ``fetched_at``/``expires_at`` untouched (a preview does not renew a full
        snapshot's freshness). On a missing row it inserts normally.
        """
        now = datetime.now(UTC)
        snapshot = await self.get(provider, provider_entity_id)
        if snapshot is None:
            snapshot = ProviderSnapshot(
                provider=provider,
                provider_entity_id=provider_entity_id,
                entity_type=entity_type,
                raw_payload=raw_payload,
                name=name,
                isrc=isrc,
                duration_ms=duration_ms,
                artist_names=artist_names,
                album_name=album_name,
                art_url=art_url,
                fetched_at=now,
                expires_at=expires_at,
            )
            self.session.add(snapshot)
        elif fill_only:
            snapshot.raw_payload = _fill_payload(snapshot.raw_payload, raw_payload)
            snapshot.name = snapshot.name or name
            snapshot.isrc = snapshot.isrc or isrc
            snapshot.duration_ms = (
                snapshot.duration_ms if snapshot.duration_ms is not None else duration_ms
            )
            snapshot.artist_names = snapshot.artist_names or artist_names
            snapshot.album_name = snapshot.album_name or album_name
            snapshot.art_url = snapshot.art_url or art_url
        else:
            snapshot.entity_type = entity_type
            snapshot.raw_payload = raw_payload
            snapshot.name = name
            snapshot.isrc = isrc
            snapshot.duration_ms = duration_ms
            snapshot.artist_names = artist_names
            snapshot.album_name = album_name
            snapshot.art_url = art_url
            snapshot.fetched_at = now
            snapshot.expires_at = expires_at
        await self.session.flush()
        return snapshot

    async def get(self, provider: ProviderId, provider_entity_id: str) -> ProviderSnapshot | None:
        result = await self.session.execute(
            select(ProviderSnapshot).where(
                ProviderSnapshot.provider == provider,
                ProviderSnapshot.provider_entity_id == provider_entity_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_isrc(self, isrc: str) -> list[ProviderSnapshot]:
        result = await self.session.execute(
            select(ProviderSnapshot).where(ProviderSnapshot.isrc == isrc)
        )
        return list(result.scalars().all())

    async def list_for_entity(
        self, entity_type: EntityType, entity_id: uuid.UUID
    ) -> list[ProviderSnapshot]:
        """Every snapshot linked to the canonical ``(entity_type, entity_id)``.

        The complete provenance set a re-resolve re-merges so the canonical
        fields stay independent of which single provider triggered the refresh
        (deterministic merge over the full contributor set).
        """
        result = await self.session.execute(
            select(ProviderSnapshot)
            .join(EntityLink, EntityLink.snapshot_id == ProviderSnapshot.id)
            .where(EntityLink.entity_type == entity_type, EntityLink.entity_id == entity_id)
        )
        return list(result.scalars().all())

    async def get_fresh(
        self, provider: ProviderId, provider_entity_id: str, now: datetime
    ) -> ProviderSnapshot | None:
        """Return the snapshot only if it has not expired at ``now``.

        ``expires_at IS NULL`` means a permanent entry (always fresh).
        """
        snapshot = await self.get(provider, provider_entity_id)
        if snapshot is None:
            return None
        if snapshot.expires_at is not None and _as_aware(now) >= _as_aware(snapshot.expires_at):
            return None
        return snapshot
