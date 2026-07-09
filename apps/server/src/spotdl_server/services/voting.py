"""VoteService — the vote state machine + derived status (spec §6.2, CONTRACT).

One public method, :meth:`VoteService.vote`, runs the whole cast-a-vote operation
as a single unit of work (the ``get_session`` dependency owns commit/rollback):

1. **Verify the votable exists** — ``load_tallies`` takes the votable's row lock
   (``FOR UPDATE`` on Postgres; SQLite serializes writers) and returns ``None``
   for a missing id → :class:`~spotdl_server.services.errors.NotFoundError` (404).
2. **Read the caller's existing vote** and map ``(old, action)`` to the counter
   deltas ``(Δup, Δdown)`` from the CONTRACT state-machine table.
3. **Apply the tally** with ``apply_tally_delta`` (pure ``col = col + delta`` SQL).
4. **Write the ledger row** — insert / update / delete. The insert path is guarded
   by a savepoint: a concurrent voter that wins the unique ``(user, votable)``
   race trips an ``IntegrityError``, and we retry as an update.
5. **Reload the fresh tallies** and **recompute the derived status** from the
   injected :class:`~spotdl_server.policies.voting.VotePolicy`
   (``matches`` / ``entity_links`` only; ``lyrics`` has no status).

The result is a frozen :class:`VoteOutcome` the router maps to its response
schema. Nothing here imports FastAPI, and the only ORM the service touches is via
the repository — its own return type is a plain dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeVar
from uuid import UUID

from spotdl_core.model import MatchStatus
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.enums import LinkStatus, VotableType
from spotdl_server.policies.voting import VOTE_POLICY_V1, VotePolicy
from spotdl_server.repositories.votes import VoteRepository
from spotdl_server.services.errors import NotFoundError

VoteAction = Literal["up", "down", "retract"]

# The CONTRACT state-machine table: (old vote value | None, action) -> (Δup, Δdown).
# `old` is None (no prior vote), +1 (up) or -1 (down). Counter deltas applied to
# the votable row; net_score delta is always Δup - Δdown.
_DELTAS: dict[tuple[int | None, VoteAction], tuple[int, int]] = {
    (None, "up"): (1, 0),
    (None, "down"): (0, 1),
    (None, "retract"): (0, 0),
    (1, "up"): (0, 0),  # no-op
    (1, "down"): (-1, 1),
    (1, "retract"): (-1, 0),
    (-1, "up"): (1, -1),
    (-1, "down"): (0, 0),  # no-op
    (-1, "retract"): (0, -1),
}

_ACTION_VALUE: dict[VoteAction, int] = {"up": 1, "down": -1}

_StatusT = TypeVar("_StatusT", MatchStatus, LinkStatus)


@dataclass(frozen=True)
class VoteOutcome:
    """The result of a vote: the fresh tallies, derived status, and the caller's
    own vote value (``+1`` / ``-1`` / ``None`` after a retract)."""

    votable_type: VotableType
    votable_id: UUID
    upvotes: int
    downvotes: int
    net_score: int
    status: str | None
    your_vote: int | None


class VoteService:
    """Cast a vote and recompute the votable's derived community status."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        votes: VoteRepository,
        policy: VotePolicy = VOTE_POLICY_V1,
    ) -> None:
        self._session = session
        self._votes = votes
        self._policy = policy

    async def vote(
        self,
        *,
        user_id: UUID,
        votable_type: VotableType,
        votable_id: UUID,
        action: VoteAction,
    ) -> VoteOutcome:
        """Apply ``action`` for ``user_id`` on the votable; return the new state.

        Raises :class:`NotFoundError` if the votable id does not exist.
        """
        # 1. Verify existence + lock the votable row.
        if await self._votes.load_tallies(votable_type, votable_id) is None:
            raise NotFoundError(entity_type=votable_type, entity_id=votable_id)

        # 2. Read the caller's existing vote and compute the counter deltas.
        existing = await self._votes.get_vote(
            user_id=user_id, votable_type=votable_type, votable_id=votable_id
        )
        old_value = existing.value if existing is not None else None
        d_up, d_down = _DELTAS[(old_value, action)]

        # 3. Apply the tally atomically.
        if d_up or d_down:
            await self._votes.apply_tally_delta(votable_type, votable_id, d_up=d_up, d_down=d_down)

        # 4. Write the ledger row (insert / update / delete).
        your_vote = await self._persist_ledger(
            user_id=user_id,
            votable_type=votable_type,
            votable_id=votable_id,
            action=action,
            existing_present=existing is not None,
        )

        # 5. Reload fresh tallies + recompute the derived status.
        tallies = await self._votes.load_tallies(votable_type, votable_id)
        assert tallies is not None  # existence checked above, within one transaction
        upvotes, downvotes, net_score = tallies
        status = await self._recompute_status(
            votable_type, votable_id, upvotes=upvotes, downvotes=downvotes, net_score=net_score
        )

        return VoteOutcome(
            votable_type=votable_type,
            votable_id=votable_id,
            upvotes=upvotes,
            downvotes=downvotes,
            net_score=net_score,
            status=status,
            your_vote=your_vote,
        )

    async def _persist_ledger(
        self,
        *,
        user_id: UUID,
        votable_type: VotableType,
        votable_id: UUID,
        action: VoteAction,
        existing_present: bool,
    ) -> int | None:
        """Insert / update / delete the ledger row; return the caller's new value.

        Returns ``None`` after a retract (the row is gone), else ``+1`` / ``-1``.
        """
        if action == "retract":
            if existing_present:
                vote = await self._votes.get_vote(
                    user_id=user_id, votable_type=votable_type, votable_id=votable_id
                )
                if vote is not None:
                    await self._votes.delete(vote)
            return None

        value = _ACTION_VALUE[action]
        if existing_present:
            await self._votes.upsert_value(
                user_id=user_id, votable_type=votable_type, votable_id=votable_id, value=value
            )
            return value

        # No prior vote: insert, guarded against a concurrent inserter winning the
        # unique-constraint race. On IntegrityError the savepoint rolls back just
        # the failed insert and we retry as an update of the now-existing row.
        try:
            async with self._session.begin_nested():
                await self._votes.upsert_value(
                    user_id=user_id,
                    votable_type=votable_type,
                    votable_id=votable_id,
                    value=value,
                )
        except IntegrityError:
            await self._votes.upsert_value(
                user_id=user_id, votable_type=votable_type, votable_id=votable_id, value=value
            )
        return value

    async def _recompute_status(
        self,
        votable_type: VotableType,
        votable_id: UUID,
        *,
        upvotes: int,
        downvotes: int,
        net_score: int,
    ) -> str | None:
        """Derive and persist the votable's status from the policy; ``None`` for lyrics."""
        total = upvotes + downvotes
        policy = self._policy
        if votable_type is VotableType.MATCH:
            match_status = self._threshold(
                total,
                net_score,
                verify=policy.match_verify_net_score,
                reject=policy.match_reject_net_score,
                yes=MatchStatus.COMMUNITY_VERIFIED,
                no=MatchStatus.REJECTED,
                neutral=MatchStatus.AUTO,
            )
            await self._votes.set_match_status(votable_id, match_status)
            return match_status.value
        if votable_type is VotableType.ENTITY_LINK:
            link_status = self._threshold(
                total,
                net_score,
                verify=policy.link_verify_net_score,
                reject=policy.link_dispute_net_score,
                yes=LinkStatus.VERIFIED,
                no=LinkStatus.DISPUTED,
                neutral=LinkStatus.AUTO,
            )
            await self._votes.set_link_status(votable_id, link_status)
            return link_status.value
        # VotableType.LYRICS has no status column — voting only maintains tallies.
        return None

    def _threshold(
        self,
        total: int,
        net_score: int,
        *,
        verify: int,
        reject: int,
        yes: _StatusT,
        no: _StatusT,
        neutral: _StatusT,
    ) -> _StatusT:
        """Map ``(total, net_score)`` to a status via the policy thresholds.

        No transition until ``total >= min_votes_for_status``; then ``net_score``
        above ``verify`` promotes, below ``reject`` demotes, else neutral. All
        transitions are reversible.
        """
        if total >= self._policy.min_votes_for_status:
            if net_score >= verify:
                return yes
            if net_score <= reject:
                return no
        return neutral
