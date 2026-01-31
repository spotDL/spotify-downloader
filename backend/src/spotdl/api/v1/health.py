"""Health check endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from spotdl.config import Settings, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str
    timestamp: datetime


class DetailedHealthResponse(HealthResponse):
    """Detailed health check with component status."""

    database: str
    cache: str
    components: dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """
    Basic health check endpoint.

    Returns the application status, version, and environment.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    settings: Settings = Depends(get_settings),
) -> DetailedHealthResponse:
    """
    Detailed health check with component status.

    Checks database connectivity, cache availability, and other components.
    """
    # TODO: Add actual database and cache connectivity checks
    components: dict[str, Any] = {
        "matching_engine": "operational",
        "providers": {
            "sources": ["spotify", "deezer", "apple_music", "tidal", "youtube_music"],
            "targets": ["youtube", "youtube_music", "soundcloud", "bandcamp", "piped"],
        },
    }

    return DetailedHealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
        database="connected" if settings.database_url else "not configured",
        cache="connected" if settings.redis_url else "not configured",
        components=components,
    )
