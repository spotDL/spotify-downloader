"""Vote policy — the versioned status thresholds (spec §6.2, CONTRACT).

:class:`VotePolicy` is a frozen, JSON-round-trippable Pydantic model: every
threshold that decides when a votable's derived ``status`` flips is a named,
recalibratable field rather than a magic number scattered through the service.
The active policy is *injected* into
:class:`~spotdl_server.services.voting.VoteService` (default
:data:`VOTE_POLICY_V1`), so a hosted operator can pin a different
``policy_version`` — exactly the pattern the matcher uses for its scoring weights.

Status is **derived and recomputed after every vote** (there is no manual
verification in v1):

* ``matches``  → ``community_verified`` when ``total_votes >= min_votes_for_status``
  and ``net_score >= match_verify_net_score``; ``rejected`` when
  ``total_votes >= min_votes_for_status`` and ``net_score <= match_reject_net_score``;
  else ``auto``.
* ``entity_links`` → same shape with the ``link_*`` thresholds →
  ``verified`` / ``disputed`` / ``auto``.
* ``lyrics`` has **no status column** — voting only maintains its tallies; the
  read side orders by ``net_score`` to surface the community favorite.

Transitions are reversible: a rejected match whose score recovers returns to
``auto`` and then ``community_verified``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class VotePolicy(BaseModel):
    """Frozen threshold config that maps a votable's tallies to its status."""

    model_config = ConfigDict(frozen=True)

    policy_version: str = "vote-v1"
    match_verify_net_score: int = 5  # matches.status -> community_verified when net_score >= this
    match_reject_net_score: int = -5  # matches.status -> rejected when net_score <= this
    link_verify_net_score: int = 5  # entity_links.status -> verified
    link_dispute_net_score: int = -5  # entity_links.status -> disputed
    min_votes_for_status: int = 3  # total votes (up + down) required before any transition


VOTE_POLICY_V1 = VotePolicy()
"""The default, immutable v1 vote policy shared across the server."""
