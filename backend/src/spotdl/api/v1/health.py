"""Health and service status endpoints for unified entity architecture."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text

from spotdl.config import Settings, get_settings
from spotdl.core.capabilities import Capability
from spotdl.core.provider_registry import ProviderHealth, get_provider_registry
from spotdl.db.database import get_db_session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

PROVIDER_SERVICE_URLS: dict[str, str | None] = {
    "spotify": "https://api.spotify.com",
    "youtube_music": "https://music.youtube.com",
    "youtube": "https://www.youtube.com",
    "piped": None,  # community/public instances
    "deezer": "https://api.deezer.com",
    "apple_music": "https://music.apple.com",
    "tidal": "https://listen.tidal.com",
    "soundcloud": "https://soundcloud.com",
    "bandcamp": "https://bandcamp.com",
    "musicbrainz": "https://musicbrainz.org",
    "discogs": "https://www.discogs.com",
    "genius": "https://genius.com",
    "musixmatch": "https://www.musixmatch.com",
    "synced": None,
}


class HealthResponse(BaseModel):
    """Basic health payload."""

    status: str
    version: str
    environment: str
    timestamp: datetime


class DetailedHealthResponse(HealthResponse):
    """Detailed component-level health payload."""

    database: str
    cache: str
    components: dict[str, Any]


class ServiceStatusItem(BaseModel):
    """Provider connectivity and latency status."""

    name: str
    display_name: str
    state: str  # connected, connecting, disconnected, error
    latency: int | None = None
    error: str | None = None


class ServiceStatusResponse(BaseModel):
    """Capability-grouped provider status."""

    sources: list[ServiceStatusItem]
    targets: list[ServiceStatusItem]
    metadata: list[ServiceStatusItem]
    capabilities: dict[str, list[ServiceStatusItem]] = Field(default_factory=dict)
    overall_state: str


def _provider_groups(matrix: list[ProviderHealth]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {
        "resolve": [],
        "match": [],
        "download": [],
        "enrich": [],
        "lyrics": [],
        "sources": [],
        "targets": [],
        "metadata": [],
        "lyrics_only": [],
    }

    for provider in matrix:
        caps = set(provider.capabilities)
        provider_id = provider.provider_id

        if Capability.RESOLVE.value in caps:
            groups["resolve"].append(provider_id)
            groups["sources"].append(provider_id)
        if Capability.MATCH.value in caps:
            groups["match"].append(provider_id)
            groups["targets"].append(provider_id)
        if Capability.DOWNLOAD.value in caps:
            groups["download"].append(provider_id)
            groups["targets"].append(provider_id)
        if Capability.ENRICH.value in caps:
            groups["enrich"].append(provider_id)
            groups["metadata"].append(provider_id)
        if Capability.LYRICS.value in caps:
            groups["lyrics"].append(provider_id)
            groups["metadata"].append(provider_id)
            groups["lyrics_only"].append(provider_id)

    for key, values in groups.items():
        groups[key] = sorted(dict.fromkeys(values))
    return groups


def _status_from_counts(connected_count: int, total_count: int) -> str:
    if total_count == 0:
        return "disconnected"
    if connected_count == total_count:
        return "connected"
    if connected_count > total_count / 2:
        return "degraded"
    if connected_count > 0:
        return "partial"
    return "disconnected"


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Basic API health."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    settings: Settings = Depends(get_settings),
    db: Annotated[AsyncSession | None, Depends(get_db_session)] = None,
) -> DetailedHealthResponse:
    """Component-level health including unified pipeline and provider capabilities."""
    database_status = "not configured"
    if settings.database_url:
        try:
            if db:
                await db.execute(text("SELECT 1"))
                database_status = "connected"
            else:
                database_status = "connection failed"
        except Exception as exc:
            database_status = f"error: {exc}"

    cache_status = "configured" if settings.redis_url else "not configured"

    registry = get_provider_registry()
    matrix = registry.health_matrix()
    groups = _provider_groups(matrix)
    provider_ids = [item.provider_id for item in matrix]
    capability_map = {
        "resolve": groups["resolve"],
        "match": groups["match"],
        "download": groups["download"],
        "enrich": groups["enrich"],
        "lyrics": groups["lyrics"],
    }

    components: dict[str, Any] = {
        "matching_engine": "operational (relation discovery)",
        "unified_entity_model": "operational",
        "merge_engine": "operational",
        "capability_router": "operational",
        "download_orchestrator": "operational",
        "providers": {
            "all": provider_ids,
            "sources": groups["sources"],
            "targets": groups["targets"],
            "metadata": groups["enrich"],
            "lyrics": groups["lyrics"],
            "capabilities": capability_map,
        },
        "api_surfaces": {
            "entity_first": "operational",
            "legacy_music_domain": "disabled",
        },
    }

    return DetailedHealthResponse(
        status="healthy" if database_status == "connected" else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
        database=database_status,
        cache=cache_status,
        components=components,
    )


@router.get("/health/services", response_model=ServiceStatusResponse)
async def service_status(
    settings: Settings = Depends(get_settings),
    db: Annotated[AsyncSession | None, Depends(get_db_session)] = None,
) -> ServiceStatusResponse:
    """Provider service connectivity grouped by capabilities."""
    del settings, db

    registry = get_provider_registry()
    matrix = registry.health_matrix()
    groups = _provider_groups(matrix)

    async def check_provider(provider: ProviderHealth) -> ServiceStatusItem:
        check_url = PROVIDER_SERVICE_URLS.get(provider.provider_id)
        if check_url is None:
            return ServiceStatusItem(
                name=provider.provider_id,
                display_name=provider.display_name,
                state="connected" if provider.status == "healthy" else "error",
                latency=None,
                error=None if provider.status == "healthy" else provider.status,
            )

        try:
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.head(check_url)
            latency_ms = int((time.monotonic() - start) * 1000)
            if response.status_code < 500:
                return ServiceStatusItem(
                    name=provider.provider_id,
                    display_name=provider.display_name,
                    state="connected",
                    latency=latency_ms,
                )
            return ServiceStatusItem(
                name=provider.provider_id,
                display_name=provider.display_name,
                state="error",
                error=f"HTTP {response.status_code}",
            )
        except httpx.TimeoutException:
            return ServiceStatusItem(
                name=provider.provider_id,
                display_name=provider.display_name,
                state="error",
                error="Timeout",
            )
        except Exception as exc:
            return ServiceStatusItem(
                name=provider.provider_id,
                display_name=provider.display_name,
                state="error",
                error=str(exc)[:60],
            )

    status_items = await asyncio.gather(*(check_provider(item) for item in matrix))
    status_by_id = {item.name: item for item in status_items}

    def map_group(ids: list[str]) -> list[ServiceStatusItem]:
        return [status_by_id[provider_id] for provider_id in ids if provider_id in status_by_id]

    sources = map_group(groups["sources"])
    targets = map_group(groups["targets"])
    metadata = map_group(sorted(set(groups["enrich"] + groups["lyrics"])))

    capabilities = {
        "resolve": map_group(groups["resolve"]),
        "match": map_group(groups["match"]),
        "download": map_group(groups["download"]),
        "enrich": map_group(groups["enrich"]),
        "lyrics": map_group(groups["lyrics"]),
    }

    all_unique = list(status_by_id.values())
    connected_count = sum(1 for item in all_unique if item.state == "connected")
    overall_state = _status_from_counts(connected_count, len(all_unique))

    return ServiceStatusResponse(
        sources=sources,
        targets=targets,
        metadata=metadata,
        capabilities=capabilities,
        overall_state=overall_state,
    )
