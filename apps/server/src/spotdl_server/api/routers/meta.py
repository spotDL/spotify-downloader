"""``GET /api/v1/health`` and ``GET /api/v1/config`` (spec §4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from spotdl_server.api.deps import get_settings
from spotdl_server.api.schemas import ConfigResponse, HealthResponse
from spotdl_server.settings import Settings

router = APIRouter(prefix="/api/v1", tags=["meta"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — always ``ok`` once the app is serving."""
    return HealthResponse(status="ok")


@router.get("/config", response_model=ConfigResponse)
async def config(settings: Settings = Depends(get_settings)) -> ConfigResponse:
    """Deployment mode + feature flags computed from the startup-fixed mode."""
    return ConfigResponse.from_settings(settings)
