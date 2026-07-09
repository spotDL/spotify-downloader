"""Match repository: a track's ranked audio targets, votable and re-matchable.

``matches`` is unique on ``(track_id, target_provider, target_id)`` and carries
community state (``status`` ∈ {auto, community_verified, rejected} plus
``upvotes`` / ``downvotes`` / ``net_score``). :meth:`replace_for_track` swaps in
a freshly-ranked AUTO list while **preserving** any community state so Plan 6
votes survive re-resolution with no schema change:

* A target already present with community state (status ∈ {community_verified,
  rejected} or any nonzero tally) keeps its ``status`` and tallies; its scoring
  fields (score, url, features, denormalized candidate) still refresh.
* A stale AUTO target (zero tallies, plain ``auto`` status) no longer in the new
  set is deleted — that is what makes this a *replace*.
* A community-state target absent from the new set is **kept**, never deleted.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from spotdl_core.model import Match, MatchStatus, ProviderId
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.models import Match as MatchModel

_COMMUNITY_STATES = frozenset({MatchStatus.COMMUNITY_VERIFIED, MatchStatus.REJECTED})


def _has_community_state(row: MatchModel) -> bool:
    """A row a fresh AUTO re-match must not overwrite."""
    return (
        row.status in _COMMUNITY_STATES
        or row.upvotes != 0
        or row.downvotes != 0
        or row.net_score != 0
    )


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_for_track(
        self, track_id: uuid.UUID, matches: Sequence[Match], matcher_version: str
    ) -> list[MatchModel]:
        """Replace the AUTO matches for ``track_id`` with ``matches``.

        Upserts each match by target; preserves community status/tallies on
        collision; deletes stale plain-AUTO rows; keeps community rows even when
        absent from the new set. Returns the rows corresponding to ``matches``.
        """
        existing = {
            (row.target_provider, row.target_id): row for row in await self._all_for_track(track_id)
        }
        new_keys: set[tuple[ProviderId, str]] = set()
        result: list[MatchModel] = []

        for match in matches:
            candidate = match.candidate
            key = (candidate.provider, candidate.provider_id)
            new_keys.add(key)
            features = match.features.model_dump() if match.features is not None else None
            row = existing.get(key)
            if row is None:
                row = MatchModel(
                    track_id=track_id,
                    target_provider=candidate.provider,
                    target_id=candidate.provider_id,
                    status=match.status,
                )
                self.session.add(row)
            elif not _has_community_state(row):
                # Plain AUTO row — safe to refresh its status from the new match.
                row.status = match.status
            # Scoring / denormalized fields always refresh from the fresh match.
            row.target_url = candidate.url
            row.score = match.score
            row.matcher_version = matcher_version
            row.features = features
            row.candidate_name = candidate.name
            row.candidate_artists = list(candidate.artists)
            row.candidate_duration_ms = candidate.duration_ms
            result.append(row)

        # Delete stale plain-AUTO rows absent from the new set; keep community rows.
        for key, row in existing.items():
            if key not in new_keys and not _has_community_state(row):
                await self.session.delete(row)

        await self.session.flush()
        return result

    async def list_for_track(self, track_id: uuid.UUID) -> list[MatchModel]:
        """Rows for ``track_id``: community_verified first, then score desc.

        Rejected matches are excluded.
        """
        priority = case((MatchModel.status == MatchStatus.COMMUNITY_VERIFIED, 0), else_=1)
        result = await self.session.execute(
            select(MatchModel)
            .where(
                MatchModel.track_id == track_id,
                MatchModel.status != MatchStatus.REJECTED,
            )
            .order_by(priority, MatchModel.score.desc())
        )
        return list(result.scalars().all())

    async def get(self, match_id: uuid.UUID) -> MatchModel | None:
        return await self.session.get(MatchModel, match_id)

    async def get_by_target(
        self, track_id: uuid.UUID, target_provider: ProviderId, target_id: str
    ) -> MatchModel | None:
        """The match for the Plan 5 unique ``(track_id, target_provider, target_id)``.

        The idempotency key for a community submission: an existing row (whether
        algorithmic or a prior submission) is returned unchanged so ``submit_match``
        never creates a duplicate or clobbers provenance.
        """
        result = await self.session.execute(
            select(MatchModel).where(
                MatchModel.track_id == track_id,
                MatchModel.target_provider == target_provider,
                MatchModel.target_id == target_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_submission(
        self,
        *,
        track_id: uuid.UUID,
        target_provider: ProviderId,
        target_id: str,
        target_url: str,
        matcher_version: str,
        submitted_by: uuid.UUID | None,
    ) -> MatchModel:
        """Insert a community-submitted audio target (Plan 6 Task 9).

        Fixed submission invariants: ``score=0.0`` (no synchronous provider fetch,
        so there is nothing to score) and ``status=AUTO`` — a submission becomes
        ``community_verified`` only through voting (Task 8). ``submitted_by`` set
        marks it as user-provided (algorithmic matches have ``submitted_by IS NULL``);
        the denormalized ``candidate_*`` fields stay NULL for a later enrichment job.
        """
        row = MatchModel(
            track_id=track_id,
            target_provider=target_provider,
            target_id=target_id,
            target_url=target_url,
            score=0.0,
            matcher_version=matcher_version,
            status=MatchStatus.AUTO,
            submitted_by=submitted_by,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def _all_for_track(self, track_id: uuid.UUID) -> list[MatchModel]:
        result = await self.session.execute(
            select(MatchModel).where(MatchModel.track_id == track_id)
        )
        return list(result.scalars().all())
