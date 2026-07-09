"""Vote repository: the vote ledger + the atomic-tally SQL (spec §6.2, CONTRACT).

Two responsibilities, both the sole holder of their SQL:

* the **ledger** — one ``votes`` row per ``(user, votable_type, votable_id)``,
  with :meth:`get_vote` / :meth:`upsert_value` / :meth:`delete`; the unique
  constraint on that triple is the concurrency race guard the service relies on.
* the **atomic tallies** — :meth:`apply_tally_delta` mutates the votable row's
  ``upvotes`` / ``downvotes`` / ``net_score`` with pure ``col = col + :delta``
  SQL expressions (never a Python read-modify-write), so concurrent votes can
  never drift the counters from the ledger. :meth:`load_tallies` reads them back
  (and doubles as the votable-exists check — ``None`` means "no such votable").

``votable_type`` polymorphically selects the target table (``match`` → ``matches``,
``lyrics`` → ``lyrics``, ``entity_link`` → ``entity_links``); the tally columns
are identical across all three. Status transitions live in :meth:`set_match_status`
/ :meth:`set_link_status` (``lyrics`` has no status). The repository never commits
— the caller owns the unit of work.
"""

from __future__ import annotations

import uuid

from spotdl_core.model import MatchStatus
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.enums import LinkStatus, VotableType
from spotdl_server.db.models import EntityLink, Lyrics, Match, Vote

# Polymorphic dispatch: a votable_type -> its ORM model. Every target carries the
# identical ``upvotes`` / ``downvotes`` / ``net_score`` columns, so one code path
# serves all three tables.
_VOTABLE_MODEL: dict[VotableType, type[Match] | type[Lyrics] | type[EntityLink]] = {
    VotableType.MATCH: Match,
    VotableType.LYRICS: Lyrics,
    VotableType.ENTITY_LINK: EntityLink,
}


class VoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_vote(
        self, *, user_id: uuid.UUID, votable_type: VotableType, votable_id: uuid.UUID
    ) -> Vote | None:
        """Return the caller's existing vote on this votable, or ``None``.

        Scoped by the unique ``(user_id, votable_type, votable_id)`` triple, so at
        most one row can match.
        """
        result = await self.session.execute(
            select(Vote).where(
                Vote.user_id == user_id,
                Vote.votable_type == votable_type,
                Vote.votable_id == votable_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_value(
        self, *, user_id: uuid.UUID, votable_type: VotableType, votable_id: uuid.UUID, value: int
    ) -> Vote:
        """Insert the caller's vote row, or update its ``value`` if it exists.

        The insert path can lose a race to a concurrent voter (the unique
        constraint fires an ``IntegrityError``); the service wraps that call in a
        savepoint and retries as an update, at which point this method finds the
        now-existing row and mutates it in place.
        """
        existing = await self.get_vote(
            user_id=user_id, votable_type=votable_type, votable_id=votable_id
        )
        if existing is None:
            vote = Vote(
                user_id=user_id,
                votable_type=votable_type,
                votable_id=votable_id,
                value=value,
            )
            self.session.add(vote)
            await self.session.flush()
            return vote
        existing.value = value
        await self.session.flush()
        return existing

    async def delete(self, vote: Vote) -> None:
        """Delete a ledger row (retraction removes the vote, never keeps a zero)."""
        await self.session.delete(vote)
        await self.session.flush()

    async def apply_tally_delta(
        self, votable_type: VotableType, votable_id: uuid.UUID, *, d_up: int, d_down: int
    ) -> None:
        """Atomically move the votable's counters by ``(d_up, d_down)``.

        Emits ``UPDATE <table> SET upvotes = upvotes + :d_up,
        downvotes = downvotes + :d_down, net_score = net_score + (:d_up - :d_down)
        WHERE id = :id`` against the table selected by ``votable_type``. Because
        the counters mutate via SQL expressions (not a read in Python), the tally
        can never drift from the ledger under concurrency.
        """
        model = _VOTABLE_MODEL[votable_type]
        await self.session.execute(
            update(model)
            .where(model.id == votable_id)
            .values(
                upvotes=model.upvotes + d_up,
                downvotes=model.downvotes + d_down,
                net_score=model.net_score + (d_up - d_down),
            )
        )

    async def load_tallies(
        self, votable_type: VotableType, votable_id: uuid.UUID
    ) -> tuple[int, int, int] | None:
        """Return ``(upvotes, downvotes, net_score)`` for the votable, or ``None``.

        ``None`` means the votable does not exist — the service turns that into a
        404. The read takes a ``FOR UPDATE`` row lock on Postgres (silently a
        no-op on SQLite, which serializes writers) so the service's
        read-existing-vote → apply-delta sequence is race-free on both dialects.
        Selecting the columns directly (not the ORM object) bypasses the identity
        map, so it always reflects the freshest committed values.
        """
        model = _VOTABLE_MODEL[votable_type]
        result = await self.session.execute(
            select(model.upvotes, model.downvotes, model.net_score)
            .where(model.id == votable_id)
            .with_for_update()
        )
        row = result.one_or_none()
        if row is None:
            return None
        return (row.upvotes, row.downvotes, row.net_score)

    async def set_match_status(self, match_id: uuid.UUID, status: MatchStatus) -> None:
        """Set ``matches.status`` (community verification is derived, not manual)."""
        await self.session.execute(update(Match).where(Match.id == match_id).values(status=status))

    async def set_link_status(self, link_id: uuid.UUID, status: LinkStatus) -> None:
        """Set ``entity_links.status`` from the derived vote outcome."""
        await self.session.execute(
            update(EntityLink).where(EntityLink.id == link_id).values(status=status)
        )
