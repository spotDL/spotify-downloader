"""Providers API endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from spotdl.core.providers_config import (
    AUDIO_SOURCE_PROVIDERS,
    LYRICS_PROVIDERS,
    METADATA_PROVIDERS,
    ProviderInfo,
    get_default_preferences,
)

router = APIRouter(prefix="/providers")


class ProviderInfoResponse(BaseModel):
    """Provider information response."""

    id: str
    name: str
    icon: str
    default_enabled: bool


class ProvidersResponse(BaseModel):
    """Response model for all providers."""

    audio_sources: list[ProviderInfoResponse]
    metadata_sources: list[ProviderInfoResponse]
    lyrics_sources: list[ProviderInfoResponse]


class ProviderPreferenceResponse(BaseModel):
    """Provider preference response."""

    id: str
    enabled: bool


class DefaultPreferencesResponse(BaseModel):
    """Response model for default preferences."""

    audio: list[ProviderPreferenceResponse]
    metadata: list[ProviderPreferenceResponse]
    lyrics: list[ProviderPreferenceResponse]


@router.get("", response_model=ProvidersResponse)
async def list_providers() -> ProvidersResponse:
    """
    List all available providers grouped by category.

    Returns provider information including ID, display name, icon key,
    and whether the provider is enabled by default.
    """
    return ProvidersResponse(
        audio_sources=[ProviderInfoResponse(**p) for p in AUDIO_SOURCE_PROVIDERS],
        metadata_sources=[ProviderInfoResponse(**p) for p in METADATA_PROVIDERS],
        lyrics_sources=[ProviderInfoResponse(**p) for p in LYRICS_PROVIDERS],
    )


@router.get("/defaults", response_model=DefaultPreferencesResponse)
async def get_default_provider_preferences() -> DefaultPreferencesResponse:
    """
    Get default provider preferences for all categories.

    Returns the default order and enabled status for each provider
    in each category.
    """
    return DefaultPreferencesResponse(
        audio=[
            ProviderPreferenceResponse(**p) for p in get_default_preferences("audio")
        ],
        metadata=[
            ProviderPreferenceResponse(**p) for p in get_default_preferences("metadata")
        ],
        lyrics=[
            ProviderPreferenceResponse(**p) for p in get_default_preferences("lyrics")
        ],
    )
