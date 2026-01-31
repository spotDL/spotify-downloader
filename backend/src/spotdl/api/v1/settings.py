"""User settings API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from spotdl.api.v1.auth import get_current_user
from spotdl.db.database import get_db_session
from spotdl.db.models.user import User
from spotdl.db.repositories.user_settings import UserSettingsRepository
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/settings")


class UserSettingsResponse(BaseModel):
    """Response model for user settings."""

    # Download settings
    audio_format: str = "mp3"
    audio_quality: str = "best"
    output_template: str = "{artist} - {title}"
    output_directory: str | None = None
    max_concurrent_downloads: int = 3
    overwrite_existing: bool = False

    # Metadata settings
    embed_metadata: bool = True
    embed_lyrics: bool = True
    embed_cover_art: bool = True

    # Spotify credentials
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    spotify_user_auth: bool = False

    # Server settings
    api_url: str = "http://localhost:8000"
    api_timeout: float = 30.0
    offline_mode: bool = False

    # Matching thresholds
    name_match_threshold: float = 60.0
    artist_match_threshold: float = 70.0
    time_match_threshold: float = 25.0

    # Advanced settings
    log_level: str = "INFO"
    cookie_file: str | None = None

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    """Request model for updating user settings."""

    # Download settings
    audio_format: str | None = Field(None, pattern="^(mp3|m4a|flac|opus|ogg|wav)$")
    audio_quality: str | None = Field(None, pattern="^(best|320k|256k|192k|128k)$")
    output_template: str | None = Field(None, max_length=255)
    output_directory: str | None = Field(None, max_length=500)
    max_concurrent_downloads: int | None = Field(None, ge=1, le=10)
    overwrite_existing: bool | None = None

    # Metadata settings
    embed_metadata: bool | None = None
    embed_lyrics: bool | None = None
    embed_cover_art: bool | None = None

    # Spotify credentials
    spotify_client_id: str | None = Field(None, max_length=255)
    spotify_client_secret: str | None = Field(None, max_length=255)
    spotify_user_auth: bool | None = None

    # Server settings
    api_url: str | None = Field(None, max_length=500)
    api_timeout: float | None = Field(None, ge=1.0, le=300.0)
    offline_mode: bool | None = None

    # Matching thresholds
    name_match_threshold: float | None = Field(None, ge=0.0, le=100.0)
    artist_match_threshold: float | None = Field(None, ge=0.0, le=100.0)
    time_match_threshold: float | None = Field(None, ge=0.0, le=100.0)

    # Advanced settings
    log_level: str | None = Field(None, pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    cookie_file: str | None = Field(None, max_length=500)


@router.get("/me", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserSettingsResponse:
    """Get current user's settings."""
    repo = UserSettingsRepository(session)
    settings, _ = await repo.get_or_create(current_user.id)
    return UserSettingsResponse.model_validate(settings)


@router.put("/me", response_model=UserSettingsResponse)
async def update_user_settings(
    data: UserSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserSettingsResponse:
    """Update current user's settings."""
    repo = UserSettingsRepository(session)
    settings, _ = await repo.get_or_create(current_user.id)

    # Only update fields that were provided
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        settings = await repo.update(settings, **update_data)

    return UserSettingsResponse.model_validate(settings)


@router.delete("/me", response_model=UserSettingsResponse)
async def reset_user_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserSettingsResponse:
    """Reset current user's settings to defaults."""
    repo = UserSettingsRepository(session)
    settings = await repo.reset_to_defaults(current_user.id)
    return UserSettingsResponse.model_validate(settings)


@router.post("/export", response_model=UserSettingsResponse)
async def export_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserSettingsResponse:
    """Export user settings as JSON (for backup/CLI sync)."""
    repo = UserSettingsRepository(session)
    settings, _ = await repo.get_or_create(current_user.id)
    return UserSettingsResponse.model_validate(settings)


@router.post("/import", response_model=UserSettingsResponse)
async def import_settings(
    data: UserSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserSettingsResponse:
    """Import settings from JSON (for CLI sync)."""
    repo = UserSettingsRepository(session)
    settings, created = await repo.get_or_create(current_user.id)

    # Update all provided fields
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        settings = await repo.update(settings, **update_data)

    return UserSettingsResponse.model_validate(settings)
