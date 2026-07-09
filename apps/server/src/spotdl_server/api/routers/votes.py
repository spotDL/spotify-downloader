"""Voting endpoints — ``POST /{matches,lyrics,links}/{id}/vote``.

A thin HTTP shell over :class:`~spotdl_server.services.voting.VoteService`: each
route pins the path to its :class:`~spotdl_server.db.enums.VotableType`, requires
an authenticated caller (``require_user`` — a JWT *or* a PAT), and delegates the
whole state machine + status recompute to the service. No business logic and no
ORM import (the outcome is a plain dataclass the schema maps). An unknown or
absent votable id surfaces as the service's ``NotFoundError`` → 404 ``not_found``
via the shared error envelope. This router is mounted only when
``settings.auth_active()`` (never in EMBEDDED mode).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from spotdl_server.api.deps import get_vote_service, require_user
from spotdl_server.api.routers import ERROR_RESPONSES
from spotdl_server.api.schemas import VoteRequest, VoteResponse
from spotdl_server.auth.context import AuthContext
from spotdl_server.db.enums import VotableType
from spotdl_server.services.voting import VoteService

router = APIRouter(prefix="/api/v1", tags=["votes"], responses=ERROR_RESPONSES)


async def _cast(
    *,
    votable_type: VotableType,
    votable_id: UUID,
    body: VoteRequest,
    ctx: AuthContext,
    service: VoteService,
) -> VoteResponse:
    """Shared delegation: map the path's votable + request verb to the service."""
    assert ctx.user_id is not None  # require_user guarantees an identity
    outcome = await service.vote(
        user_id=ctx.user_id,
        votable_type=votable_type,
        votable_id=votable_id,
        action=body.value,
    )
    return VoteResponse.from_outcome(outcome)


@router.post("/matches/{match_id}/vote", response_model=VoteResponse)
async def vote_match(
    match_id: UUID,
    body: VoteRequest,
    ctx: AuthContext = Depends(require_user),
    service: VoteService = Depends(get_vote_service),
) -> VoteResponse:
    """Up/down/retract a vote on a match; returns the fresh tallies + status."""
    return await _cast(
        votable_type=VotableType.MATCH,
        votable_id=match_id,
        body=body,
        ctx=ctx,
        service=service,
    )


@router.post("/lyrics/{lyrics_id}/vote", response_model=VoteResponse)
async def vote_lyrics(
    lyrics_id: UUID,
    body: VoteRequest,
    ctx: AuthContext = Depends(require_user),
    service: VoteService = Depends(get_vote_service),
) -> VoteResponse:
    """Up/down/retract a vote on a lyrics variant (lyrics have no status)."""
    return await _cast(
        votable_type=VotableType.LYRICS,
        votable_id=lyrics_id,
        body=body,
        ctx=ctx,
        service=service,
    )


@router.post("/links/{link_id}/vote", response_model=VoteResponse)
async def vote_link(
    link_id: UUID,
    body: VoteRequest,
    ctx: AuthContext = Depends(require_user),
    service: VoteService = Depends(get_vote_service),
) -> VoteResponse:
    """Up/down/retract a vote on a cross-provider entity link."""
    return await _cast(
        votable_type=VotableType.ENTITY_LINK,
        votable_id=link_id,
        body=body,
        ctx=ctx,
        service=service,
    )
