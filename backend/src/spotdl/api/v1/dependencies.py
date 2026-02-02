"""FastAPI dependencies for API endpoints."""

from __future__ import annotations

from typing import Annotated, TypedDict

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.api.v1.auth import get_current_user_optional
from spotdl.core.metadata_embed_config import (
    MetadataEmbedPreferences,
    validate_embed_preferences,
)
from spotdl.core.provider_preferences import (
    AudioPreferences,
    LyricsPreferences,
    MetadataPreferences,
    get_enabled_audio_platforms,
    get_enabled_lyrics_provider_ids,
    get_enabled_metadata_provider_ids,
)
from spotdl.core.providers_config import (
    ProviderPreference,
    get_default_preferences,
)
from spotdl.db.database import get_db_session
from spotdl.db.models.user import User
from spotdl.db.repositories.user_settings import UserSettingsRepository


class UserPreferences(TypedDict):
    """Complete user preferences for all provider types."""

    audio: list[ProviderPreference] | None
    metadata: list[ProviderPreference] | None
    lyrics: list[ProviderPreference] | None


async def get_user_preferences(
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserPreferences:
    """
    FastAPI dependency that fetches user preferences.

    If user is authenticated, fetches from user_settings table.
    If user is not authenticated, returns None for all preferences
    (which will use defaults when converted to provider instances).

    Args:
        current_user: Current authenticated user (or None if unauthenticated)
        db: Database session

    Returns:
        UserPreferences with audio, metadata, and lyrics preferences
    """
    if current_user is None:
        # Unauthenticated users get default preferences
        return UserPreferences(
            audio=None,
            metadata=None,
            lyrics=None,
        )

    # Fetch user settings from database
    settings_repo = UserSettingsRepository(db)
    settings = await settings_repo.get_by_user_id(current_user.id)

    if settings is None:
        # User exists but has no settings yet - use defaults
        return UserPreferences(
            audio=None,
            metadata=None,
            lyrics=None,
        )

    return UserPreferences(
        audio=settings.audio_source_preferences,
        metadata=settings.metadata_source_preferences,
        lyrics=settings.lyrics_source_preferences,
    )


async def get_audio_preferences(
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
) -> AudioPreferences:
    """
    Get resolved audio preferences for use in MatchService.

    Args:
        preferences: User's raw preferences

    Returns:
        AudioPreferences with resolved TargetPlatform list
    """
    platforms = get_enabled_audio_platforms(preferences["audio"])
    return AudioPreferences(
        platforms=platforms,
        platform_ids=[p.value for p in platforms],
    )


async def get_metadata_preferences(
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
) -> MetadataPreferences:
    """
    Get resolved metadata preferences for use in MetadataService.

    Args:
        preferences: User's raw preferences

    Returns:
        MetadataPreferences with enabled flags
    """
    return get_enabled_metadata_provider_ids(preferences["metadata"])


async def get_lyrics_preferences(
    preferences: Annotated[UserPreferences, Depends(get_user_preferences)],
) -> LyricsPreferences:
    """
    Get resolved lyrics preferences for use in LyricsService.

    Args:
        preferences: User's raw preferences

    Returns:
        LyricsPreferences with provider order
    """
    return get_enabled_lyrics_provider_ids(preferences["lyrics"])


async def get_embed_preferences(
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MetadataEmbedPreferences:
    """
    Get user's metadata embed preferences.

    Used for resolving which source to use for each metadata field
    when viewing or downloading songs.

    Args:
        current_user: Current authenticated user (or None)
        db: Database session

    Returns:
        Validated MetadataEmbedPreferences
    """
    if current_user is None:
        # Unauthenticated users get default embed preferences
        return validate_embed_preferences(None)

    # Fetch user settings
    settings_repo = UserSettingsRepository(db)
    settings = await settings_repo.get_by_user_id(current_user.id)

    if settings is None:
        return validate_embed_preferences(None)

    return validate_embed_preferences(settings.metadata_embed_preferences)
