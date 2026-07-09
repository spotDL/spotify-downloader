"""Entity-link repository: canonical entity ↔ provider-snapshot linkage.

One row per ``(entity_type, entity_id, snapshot_id)`` triple (the table's unique
constraint). ``entity_links`` is votable (Plan 6 writes ``upvotes`` /
``downvotes`` / ``net_score`` and promotes ``status``), so ``upsert`` is
idempotent on the triple and **never** clobbers an existing row's ``status`` or
tallies — a re-resolve that re-links the same snapshot leaves a human-verified
link untouched. New status is set only on insert (via ``status``) or explicitly
through :meth:`set_status`.
"""

from __future__ import annotations

import uuid

from spotdl_core.model import EntityType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.enums import LinkStatus
from spotdl_server.db.models import EntityLink


class EntityLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        entity_type: EntityType,
        entity_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        status: LinkStatus = LinkStatus.AUTO,
    ) -> EntityLink:
        """Create the link for the triple, or return the existing one unchanged.

        Idempotent on ``(entity_type, entity_id, snapshot_id)``. On an existing
        row the ``status``/tallies are preserved (a fresh AUTO re-link must not
        demote a community-verified link); use :meth:`set_status` to change it.
        """
        existing = await self._get(entity_type, entity_id, snapshot_id)
        if existing is not None:
            return existing
        link = EntityLink(
            entity_type=entity_type,
            entity_id=entity_id,
            snapshot_id=snapshot_id,
            status=status,
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def for_entity(self, entity_type: EntityType, entity_id: uuid.UUID) -> list[EntityLink]:
        result = await self.session.execute(
            select(EntityLink).where(
                EntityLink.entity_type == entity_type,
                EntityLink.entity_id == entity_id,
            )
        )
        return list(result.scalars().all())

    async def set_status(self, link: EntityLink, status: LinkStatus) -> EntityLink:
        link.status = status
        await self.session.flush()
        return link

    async def entity_for_snapshot(
        self, snapshot_id: uuid.UUID
    ) -> tuple[EntityType, uuid.UUID] | None:
        """The canonical ``(entity_type, entity_id)`` a snapshot is linked to.

        The reverse of :meth:`for_entity`: given a provider snapshot, find the
        canonical entity it contributes to (used cache-first to reload an
        already-merged entity without touching the network). ``None`` when the
        snapshot has not been merged yet.
        """
        result = await self.session.execute(
            select(EntityLink.entity_type, EntityLink.entity_id)
            .where(EntityLink.snapshot_id == snapshot_id)
            .limit(1)
        )
        row = result.first()
        return (row[0], row[1]) if row is not None else None

    async def _get(
        self, entity_type: EntityType, entity_id: uuid.UUID, snapshot_id: uuid.UUID
    ) -> EntityLink | None:
        result = await self.session.execute(
            select(EntityLink).where(
                EntityLink.entity_type == entity_type,
                EntityLink.entity_id == entity_id,
                EntityLink.snapshot_id == snapshot_id,
            )
        )
        return result.scalar_one_or_none()
