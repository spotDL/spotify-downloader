"""``POST /api/v1/resolve`` — resolve a URL / ref / free-text query to an entity."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from spotdl_server.api.deps import get_resolve_service
from spotdl_server.api.routers import ERROR_RESPONSES
from spotdl_server.api.schemas import ResolveRequest, ResolveResponse
from spotdl_server.services.resolve import ResolveService

router = APIRouter(prefix="/api/v1", tags=["resolve"], responses=ERROR_RESPONSES)


@router.post("/resolve", response_model=ResolveResponse)
async def resolve(
    body: ResolveRequest,
    service: ResolveService = Depends(get_resolve_service),
) -> ResolveResponse:
    """Resolve ``body.query`` to a canonical entity + the sources that degraded."""
    result = await service.resolve(body.query, force=body.force)
    return ResolveResponse.from_result(result)
