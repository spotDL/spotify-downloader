"""``GET /api/v1/search`` — free-text multi-provider search."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from spotdl_server.api.deps import get_search_service
from spotdl_server.api.routers import ERROR_RESPONSES
from spotdl_server.api.schemas import SearchResponse
from spotdl_server.services.search import SearchService

router = APIRouter(prefix="/api/v1", tags=["search"], responses=ERROR_RESPONSES)


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Free-text search query."),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return."),
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """Search every capable provider for ``q`` and return a ranked track list."""
    result = await service.search(q, limit=limit)
    return SearchResponse.from_result(result)
