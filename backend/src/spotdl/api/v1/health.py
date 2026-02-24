"""Health check endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.config import Settings, get_settings
from spotdl.core.providers_config import (
    AUDIO_SOURCE_PROVIDERS,
    LYRICS_PROVIDERS,
    METADATA_PROVIDERS,
)
from spotdl.db.database import get_db_session

router = APIRouter()

SOURCE_SERVICE_URLS = {
    "spotify": "https://api.spotify.com",
    "youtube_music": "https://music.youtube.com",
    "deezer": "https://api.deezer.com",
    "apple_music": "https://api.music.apple.com",
    "tidal": "https://listen.tidal.com",
    "soundcloud": "https://soundcloud.com",
    "bandcamp": "https://bandcamp.com",
}

SOURCE_PROVIDERS = [
    {"id": "spotify", "name": "Spotify"},
    {"id": "youtube_music", "name": "YouTube Music"},
    {"id": "deezer", "name": "Deezer"},
    {"id": "apple_music", "name": "Apple Music"},
    {"id": "tidal", "name": "Tidal"},
    {"id": "soundcloud", "name": "SoundCloud"},
    {"id": "bandcamp", "name": "Bandcamp"},
]

TARGET_SERVICE_URLS = {
    "youtube": "https://www.youtube.com",
    "youtube_music": "https://music.youtube.com",
    "soundcloud": "https://soundcloud.com",
    "bandcamp": "https://bandcamp.com",
    # Piped uses community/public instances and does not have a single canonical endpoint.
    "piped": None,
}

METADATA_SERVICE_URLS = {
    "spotify": "https://api.spotify.com",
    "musicbrainz": "https://musicbrainz.org",
    "discogs": "https://www.discogs.com",
}

LYRICS_SERVICE_URLS = {
    "synced": None,
    "genius": "https://genius.com",
    "musixmatch": "https://www.musixmatch.com",
    "azlyrics": "https://www.azlyrics.com",
}


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


class ServiceStatusItem(BaseModel):
    """Individual service status."""

    name: str
    display_name: str
    state: str  # "connected", "connecting", "disconnected", "error"
    latency: int | None = None
    error: str | None = None


class ServiceStatusResponse(BaseModel):
    """Service status response for all platforms and metadata sources."""

    sources: list[ServiceStatusItem]
    targets: list[ServiceStatusItem]
    metadata: list[ServiceStatusItem]
    overall_state: str


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
            "sources": [p["id"] for p in SOURCE_PROVIDERS],
            "targets": ["youtube", "youtube_music", "soundcloud", "bandcamp", "piped"],
            "metadata": [p["id"] for p in METADATA_PROVIDERS],
            "lyrics": [p["id"] for p in LYRICS_PROVIDERS],
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


@router.get("/health/services", response_model=ServiceStatusResponse)
async def service_status(
    settings: Settings = Depends(get_settings),
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> ServiceStatusResponse:
    """
    Get connectivity status for all external services.

    Checks source platforms, target platforms, and metadata providers.
    Returns latency measurements where available.
    """
    import asyncio
    import time
    import httpx

    async def check_service(name: str, display_name: str, check_url: str | None = None) -> ServiceStatusItem:
        """Check a single service's availability."""
        if not check_url:
            # Service doesn't have a health check URL - assume operational
            return ServiceStatusItem(
                name=name,
                display_name=display_name,
                state="connected",
                latency=None,
            )

        try:
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.head(check_url)
                latency = int((time.monotonic() - start) * 1000)

                if response.status_code < 500:
                    return ServiceStatusItem(
                        name=name,
                        display_name=display_name,
                        state="connected",
                        latency=latency,
                    )
                else:
                    return ServiceStatusItem(
                        name=name,
                        display_name=display_name,
                        state="error",
                        error=f"HTTP {response.status_code}",
                    )
        except httpx.TimeoutException:
            return ServiceStatusItem(
                name=name,
                display_name=display_name,
                state="error",
                error="Timeout",
            )
        except Exception as e:
            return ServiceStatusItem(
                name=name,
                display_name=display_name,
                state="error",
                error=str(e)[:50],
            )

    # Define services to check from canonical provider configuration.
    source_services = [
        (provider["id"], provider["name"], SOURCE_SERVICE_URLS.get(provider["id"]))
        for provider in SOURCE_PROVIDERS
    ]

    target_services = [
        ("youtube", "YouTube", TARGET_SERVICE_URLS["youtube"]),
        ("youtube_music", "YouTube Music", TARGET_SERVICE_URLS["youtube_music"]),
        ("soundcloud", "SoundCloud", TARGET_SERVICE_URLS["soundcloud"]),
        ("bandcamp", "Bandcamp", TARGET_SERVICE_URLS["bandcamp"]),
        ("piped", "Piped", TARGET_SERVICE_URLS["piped"]),
    ]

    metadata_services = [
        (provider["id"], provider["name"], METADATA_SERVICE_URLS.get(provider["id"]))
        for provider in METADATA_PROVIDERS
    ] + [
        (
            provider["id"],
            f"{provider['name']} (Lyrics)",
            LYRICS_SERVICE_URLS.get(provider["id"]),
        )
        for provider in LYRICS_PROVIDERS
    ]

    # Check all services concurrently
    all_checks = []
    for name, display_name, url in source_services + target_services + metadata_services:
        all_checks.append(check_service(name, display_name, url))

    results = await asyncio.gather(*all_checks, return_exceptions=True)

    # Process results
    source_results = []
    target_results = []
    metadata_results = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Handle unexpected exceptions
            if i < len(source_services):
                name, display_name, _ = source_services[i]
            elif i < len(source_services) + len(target_services):
                name, display_name, _ = target_services[i - len(source_services)]
            else:
                name, display_name, _ = metadata_services[i - len(source_services) - len(target_services)]

            result = ServiceStatusItem(
                name=name,
                display_name=display_name,
                state="error",
                error="Check failed",
            )

        if i < len(source_services):
            source_results.append(result)
        elif i < len(source_services) + len(target_services):
            target_results.append(result)
        else:
            metadata_results.append(result)

    # Determine overall state
    all_results = source_results + target_results + metadata_results
    connected_count = sum(1 for r in all_results if r.state == "connected")
    total_count = len(all_results)

    if connected_count == total_count:
        overall_state = "connected"
    elif connected_count > total_count / 2:
        overall_state = "degraded"
    elif connected_count > 0:
        overall_state = "partial"
    else:
        overall_state = "disconnected"

    return ServiceStatusResponse(
        sources=source_results,
        targets=target_results,
        metadata=metadata_results,
        overall_state=overall_state,
    )
