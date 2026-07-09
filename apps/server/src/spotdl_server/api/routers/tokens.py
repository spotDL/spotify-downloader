"""``/api/v1/auth/tokens`` — personal access tokens (PATs) for the CLI.

A thin HTTP shell over :class:`~spotdl_server.services.pat.PatService`: it maps
request bodies to service calls and the returned ``ApiToken`` rows to the response
schemas. Every route requires an authenticated caller (``require_user`` — a JWT
*or* an existing PAT), so a user manages their own credentials. No business logic,
no ORM import (the ``ApiToken`` rows are serialized by ``PatResponse.model_validate``
without naming the ORM type). This router is mounted only when
``settings.auth_active()`` (never in EMBEDDED mode).

The **create** response is the sole place the full ``spdl_pat_`` secret appears;
every later listing exposes only the ``token_prefix`` + metadata. ``expires_in_days``
is converted to an absolute ``expires_at`` here using the shared clock so the
service keeps a clean absolute-instant signature. Ownership failures (revoking a
token the caller does not own) are raised by the service as ``TokenNotFound`` and
rendered as a 404 by the shared error envelope.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from spotdl_server.api.deps import get_clock, get_pat_service, require_user
from spotdl_server.api.routers import ERROR_RESPONSES
from spotdl_server.api.schemas import CreatePatRequest, PatCreatedResponse, PatResponse
from spotdl_server.auth.clock import Clock
from spotdl_server.auth.context import AuthContext
from spotdl_server.services.pat import PatService

router = APIRouter(prefix="/api/v1/auth/tokens", tags=["tokens"], responses=ERROR_RESPONSES)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PatCreatedResponse)
async def create_token(
    body: CreatePatRequest,
    ctx: AuthContext = Depends(require_user),
    service: PatService = Depends(get_pat_service),
    clock: Clock = Depends(get_clock),
) -> PatCreatedResponse:
    """Mint a PAT for the caller; the full secret is returned **only here**."""
    assert ctx.user_id is not None  # require_user guarantees an identity
    expires_at = (
        clock.now() + timedelta(days=body.expires_in_days)
        if body.expires_in_days is not None
        else None
    )
    row, full = await service.create(user_id=ctx.user_id, name=body.name, expires_at=expires_at)
    return PatCreatedResponse(
        id=row.id,
        name=row.name,
        token_prefix=row.token_prefix,
        token=full,
        created_at=row.created_at,
        expires_at=row.expires_at,
    )


@router.get("", response_model=list[PatResponse])
async def list_tokens(
    ctx: AuthContext = Depends(require_user),
    service: PatService = Depends(get_pat_service),
) -> list[PatResponse]:
    """List the caller's PATs (prefix + metadata only; never the secret)."""
    assert ctx.user_id is not None  # require_user guarantees an identity
    rows = await service.list_for_user(ctx.user_id)
    return [PatResponse.model_validate(row) for row in rows]


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    token_id: UUID,
    ctx: AuthContext = Depends(require_user),
    service: PatService = Depends(get_pat_service),
) -> Response:
    """Revoke one of the caller's PATs (404 if it is not theirs / does not exist)."""
    assert ctx.user_id is not None  # require_user guarantees an identity
    await service.revoke(user_id=ctx.user_id, token_id=token_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
