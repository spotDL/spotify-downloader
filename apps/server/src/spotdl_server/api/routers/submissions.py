"""``POST /api/v1/tracks/{id}/matches`` — community-submitted audio matches.

A thin HTTP shell over :class:`~spotdl_server.services.submissions.SubmissionService`:
it requires an authenticated caller (``require_user`` — a JWT *or* a PAT), hands
the URL to the service, and maps the returned ``Match`` row to the Plan 5
``MatchOut`` schema via the shared ``match_view`` DTO builder (no ORM import here).
An unknown track surfaces as the service's ``NotFoundError`` → 404; a non-audio or
unparseable URL as ``NotAnAudioTarget`` / ``UnsupportedURL`` → 400; all via the
shared error envelope. This router is mounted only when ``settings.auth_active()``
(never in EMBEDDED mode), alongside the read-only ``GET /tracks/{id}/matches``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from spotdl_server.api.deps import get_submission_service, require_user
from spotdl_server.api.routers import ERROR_RESPONSES
from spotdl_server.api.schemas import MatchOut, SubmitMatchRequest
from spotdl_server.auth.context import AuthContext
from spotdl_server.services.submissions import SubmissionService
from spotdl_server.services.views import match_view

router = APIRouter(prefix="/api/v1", tags=["submissions"], responses=ERROR_RESPONSES)


@router.post(
    "/tracks/{id}/matches",
    status_code=status.HTTP_201_CREATED,
    response_model=MatchOut,
)
async def submit_match(
    id: UUID,
    body: SubmitMatchRequest,
    ctx: AuthContext = Depends(require_user),
    service: SubmissionService = Depends(get_submission_service),
) -> MatchOut:
    """Submit an audio-target URL as a community match for a track (201 ``MatchOut``)."""
    assert ctx.user_id is not None  # require_user guarantees an identity
    row = await service.submit_match(track_id=id, url=body.url, submitted_by=ctx.user_id)
    return MatchOut.from_view(match_view(row))
