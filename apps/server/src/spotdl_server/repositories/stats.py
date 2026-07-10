"""Stats repositories: admin dashboard counts + entity engagement time-series (§6.2).

:class:`StatsRepository` is the sole holder of the aggregate-count SQL that backs
``GET /admin/stats`` (one ``SELECT count(*)`` per method). :class:`EntityStatRepository`
owns the ``entity_stat`` engagement time-series (Phase 4): an append-only
``record`` plus a latest-per-metric read for the current numbers the Stats/Sources
panels display. Neither commits — the caller owns the unit of work.

``StatsRepository`` is kept deliberately granular (one count per method) so
:class:`AdminService` can assemble the ``AdminStats`` view while this module stays
the only place the ORM / SQLAlchemy count queries live (the layering contract, §6).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from spotdl_core.model import EntityType, MatchStatus, ProviderId
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.enums import ReportStatus
from spotdl_server.db.models import EntityStat, Match, Report, User, Vote


class StatsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_users(self) -> int:
        """Total number of registered users."""
        return int(await self.session.scalar(select(func.count()).select_from(User)) or 0)

    async def count_matches(self) -> int:
        """Total number of match rows (all statuses)."""
        return int(await self.session.scalar(select(func.count()).select_from(Match)) or 0)

    async def count_matches_in_status(self, status: MatchStatus) -> int:
        """Number of matches currently in ``status`` (e.g. community-verified)."""
        return int(
            await self.session.scalar(
                select(func.count()).select_from(Match).where(Match.status == status)
            )
            or 0
        )

    async def count_votes(self) -> int:
        """Total number of vote-ledger rows."""
        return int(await self.session.scalar(select(func.count()).select_from(Vote)) or 0)

    async def count_reports(self) -> int:
        """Total number of correction reports (all statuses)."""
        return int(await self.session.scalar(select(func.count()).select_from(Report)) or 0)

    async def count_reports_in_status(self, status: ReportStatus) -> int:
        """Number of reports currently in ``status`` (e.g. pending review)."""
        return int(
            await self.session.scalar(
                select(func.count()).select_from(Report).where(Report.status == status)
            )
            or 0
        )


class EntityStatRepository:
    """Append + latest-per-metric access to the ``entity_stat`` time series.

    One row per ``(entity, provider, metric, capture)``. :meth:`record` always
    inserts — the table is a time series, so re-resolving an entity later appends a
    fresh capture (powering sparklines) rather than overwriting history.
    :meth:`latest_per_metric` collapses the series to the current value per
    ``(provider, metric)`` for the "current numbers" the Stats/Sources panels show.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        entity_type: EntityType,
        entity_id: uuid.UUID,
        provider: ProviderId,
        metric: str,
        value: int,
        captured_at: datetime | None = None,
    ) -> EntityStat:
        """Append one engagement capture (``captured_at`` defaults to now).

        Always inserts (no upsert) — the table is a time series. The caller is
        responsible for not emitting duplicate ``(provider, metric)`` rows within a
        single capture; the resolve layer dedupes before calling. ``captured_at`` is
        accepted for deterministic backfill/tests (the model default is used when
        ``None``).
        """
        row = EntityStat(
            entity_type=entity_type,
            entity_id=entity_id,
            provider=provider,
            metric=metric,
            value=value,
            **({"captured_at": captured_at} if captured_at is not None else {}),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_for_entity(
        self, entity_type: EntityType, entity_id: uuid.UUID
    ) -> list[EntityStat]:
        """Every captured stat for ``(entity_type, entity_id)``, newest first."""
        result = await self.session.execute(
            select(EntityStat)
            .where(
                EntityStat.entity_type == entity_type,
                EntityStat.entity_id == entity_id,
            )
            .order_by(EntityStat.captured_at.desc())
        )
        return list(result.scalars().all())

    async def latest_per_metric(
        self, entity_type: EntityType, entity_id: uuid.UUID
    ) -> list[EntityStat]:
        """The newest capture for each ``(provider, metric)`` of an entity.

        Collapses the series to one row per provider+metric (the current value the
        UI shows), ordered by (provider, metric) for a deterministic result.
        """
        rows = await self.list_for_entity(entity_type, entity_id)  # newest-first
        latest: dict[tuple[ProviderId, str], EntityStat] = {}
        for row in rows:
            latest.setdefault((row.provider, row.metric), row)
        return sorted(latest.values(), key=lambda r: (r.provider.value, r.metric))
