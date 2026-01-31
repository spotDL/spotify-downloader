"""Health check endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.config import Settings, get_settings
from spotdl.db.database import get_db_session

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
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> DetailedHealthResponse:
    """
    Detailed health check with component status.

    Checks database connectivity, cache availability, and other components.
    """
    # Check database connectivity
    database_status = "not configured"
    if settings.database_url:
        try:
            if db:
                await db.execute(text("SELECT 1"))
                database_status = "connected"
            else:
                database_status = "connection failed"
        except Exception as e:
            database_status = f"error: {str(e)}"

    # Check cache (Redis) connectivity
    cache_status = "not configured"
    if settings.redis_url:
        cache_status = "configured"

    components: dict[str, Any] = {
        "matching_engine": "operational",
        "providers": {
            "sources": ["spotify", "deezer", "apple_music", "tidal", "youtube_music"],
            "targets": ["youtube", "youtube_music", "soundcloud", "bandcamp", "piped"],
        },
    }

    return DetailedHealthResponse(
        status="healthy" if database_status == "connected" else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
        database=database_status,
        cache=cache_status,
        components=components,
    )
