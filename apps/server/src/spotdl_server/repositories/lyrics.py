"""Lyrics repository: per-track lyrics, keyed by source and kind, votable.

``lyrics`` is unique on ``(track_id, source, kind)`` and carries vote tallies
(``upvotes`` / ``downvotes`` / ``net_score``). :meth:`upsert` refreshes the text
for an existing triple while **preserving** its tallies (a re-fetch must not
reset community votes). :meth:`list_for_track` returns synced lyrics before
plain, each group ordered by ``net_score`` descending.
"""

from __future__ import annotations

import uuid

from spotdl_core.model import LyricsKind, ProviderId
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.models import Lyrics


class LyricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self, track_id: uuid.UUID, source: ProviderId, kind: LyricsKind, text: str
    ) -> Lyrics:
        """Create or refresh the lyrics row for ``(track_id, source, kind)``.

        Idempotent on the triple; updates ``text`` on an existing row and leaves
        its vote tallies untouched.
        """
        existing = await self._get_by_triple(track_id, source, kind)
        if existing is not None:
            existing.text = text
            await self.session.flush()
            return existing
        row = Lyrics(track_id=track_id, source=source, kind=kind, text=text)
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_for_track(self, track_id: uuid.UUID) -> list[Lyrics]:
        """Rows for ``track_id``: synced before plain, then ``net_score`` desc."""
        priority = case((Lyrics.kind == LyricsKind.SYNCED, 0), else_=1)
        result = await self.session.execute(
            select(Lyrics)
            .where(Lyrics.track_id == track_id)
            .order_by(priority, Lyrics.net_score.desc())
        )
        return list(result.scalars().all())

    async def get(self, id: uuid.UUID) -> Lyrics | None:
        return await self.session.get(Lyrics, id)

    async def _get_by_triple(
        self, track_id: uuid.UUID, source: ProviderId, kind: LyricsKind
    ) -> Lyrics | None:
        result = await self.session.execute(
            select(Lyrics).where(
                Lyrics.track_id == track_id,
                Lyrics.source == source,
                Lyrics.kind == kind,
            )
        )
        return result.scalar_one_or_none()
