"""User settings API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.api.v1.auth import get_current_user
from spotdl.core.metadata_embed_config import (
    FIELD_CATEGORIES,
    METADATA_FIELDS,
    METADATA_SOURCES,
    get_default_embed_preferences,
    get_fields_by_category,
    validate_embed_preferences,
)
from spotdl.db.database import get_db_session
from spotdl.db.models.user import User
from spotdl.db.repositories.user_settings import UserSettingsRepository

router = APIRouter(prefix="/settings")


class ProviderPreference(BaseModel):
    """A single provider preference."""

    id: str
    enabled: bool


class FieldPreferenceModel(BaseModel):
    """User preference for a single metadata field."""

    order: list[str]  # Source priority order
    enabled: bool = True  # Whether to include this field


class MetadataEmbedPreferencesModel(BaseModel):
    """User preferences for metadata embedding."""

    default_order: list[str]  # Default source order for fields without overrides
    fields: dict[str, FieldPreferenceModel]  # Per-field preferences


class UserSettingsResponse(BaseModel):
    """Response model for user settings."""

    # Download settings
    audio_format: str = "mp3"
    audio_quality: str = "best"
    bitrate: str | None = None
    output_template: str = "{artist} - {title}"
    output_directory: str | None = None
    max_concurrent_downloads: int = 3
    overwrite: str = "skip"
    max_filename_length: int = 255
    restrict: str | None = None

    # Metadata settings
    embed_metadata: bool = True
    embed_lyrics: bool = True
    embed_cover: bool = True
    id3_separator: str = "/"

    # SponsorBlock
    sponsor_block: bool = False

    # LRC / Lyrics files
    generate_lrc: bool = False

    # M3U playlist generation
    m3u: str | None = None

    # Archive (deduplication)
    archive: str | None = None

    # Content filtering
    skip_explicit: bool = False
    scan_for_songs: bool = False

    # Playlist options
    playlist_numbering: bool = False
    fetch_albums: bool = False

    # Proxy
    proxy: str | None = None

    # Custom arguments
    ffmpeg_args: str | None = None
    yt_dlp_args: str | None = None

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

    # Appearance settings
    compact_sidebar: bool = True
    enable_animations: bool = True
    reduce_motion: bool = False

    # Provider preferences
    audio_source_preferences: list[ProviderPreference] | None = None
    metadata_source_preferences: list[ProviderPreference] | None = None
    lyrics_source_preferences: list[ProviderPreference] | None = None

    # Metadata embed preferences (per-field source priority)
    metadata_embed_preferences: MetadataEmbedPreferencesModel | None = None

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    """Request model for updating user settings."""

    # Download settings
    audio_format: str | None = Field(None, pattern="^(mp3|m4a|flac|opus|ogg|wav)$")
    audio_quality: str | None = Field(None, pattern="^(best|320k|256k|192k|128k)$")
    bitrate: str | None = Field(None, max_length=20)
    output_template: str | None = Field(None, max_length=255)
    output_directory: str | None = Field(None, max_length=500)
    max_concurrent_downloads: int | None = Field(None, ge=1, le=10)
    overwrite: str | None = Field(None, pattern="^(skip|force|metadata)$")
    max_filename_length: int | None = Field(None, ge=50, le=500)
    restrict: str | None = Field(None, pattern="^(strict|loose)$")

    # Metadata settings
    embed_metadata: bool | None = None
    embed_lyrics: bool | None = None
    embed_cover: bool | None = None
    id3_separator: str | None = Field(None, max_length=5)

    # SponsorBlock
    sponsor_block: bool | None = None

    # LRC / Lyrics files
    generate_lrc: bool | None = None

    # M3U playlist generation
    m3u: str | None = Field(None, max_length=255)

    # Archive (deduplication)
    archive: str | None = Field(None, max_length=500)

    # Content filtering
    skip_explicit: bool | None = None
    scan_for_songs: bool | None = None

    # Playlist options
    playlist_numbering: bool | None = None
    fetch_albums: bool | None = None

    # Proxy
    proxy: str | None = Field(None, max_length=500)

    # Custom arguments
    ffmpeg_args: str | None = Field(None, max_length=500)
    yt_dlp_args: str | None = Field(None, max_length=500)

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

    # Appearance settings
    compact_sidebar: bool | None = None
    enable_animations: bool | None = None
    reduce_motion: bool | None = None

    # Provider preferences
    audio_source_preferences: list[ProviderPreference] | None = None
    metadata_source_preferences: list[ProviderPreference] | None = None
    lyrics_source_preferences: list[ProviderPreference] | None = None

    # Metadata embed preferences (per-field source priority)
    metadata_embed_preferences: MetadataEmbedPreferencesModel | None = None


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


# ============================================================================
# Metadata Embed Preferences Endpoints
# ============================================================================


class MetadataSourceResponse(BaseModel):
    """Response model for a metadata source."""

    id: str
    name: str
    description: str


class MetadataFieldResponse(BaseModel):
    """Response model for a metadata field."""

    id: str
    name: str
    description: str
    category: str
    default_order: list[str]
    embed_tag: str | None


class MetadataFieldCategoryResponse(BaseModel):
    """Response model for a field category."""

    id: str
    name: str
    fields: list[MetadataFieldResponse]


class MetadataEmbedConfigResponse(BaseModel):
    """Response with all available sources and fields."""

    sources: list[MetadataSourceResponse]
    fields: list[MetadataFieldResponse]
    categories: list[MetadataFieldCategoryResponse]


@router.get("/metadata-embed/config")
async def get_metadata_embed_config() -> MetadataEmbedConfigResponse:
    """
    Get available metadata sources and fields for embed preferences.

    Returns all available sources (Spotify, MusicBrainz, Discogs, etc.) and
    all metadata fields organized by category. Use this to build the
    preferences UI with draggable source lists per field.
    """
    # Get fields grouped by category
    fields_by_cat = get_fields_by_category()

    categories = [
        MetadataFieldCategoryResponse(
            id=cat_id,
            name=FIELD_CATEGORIES.get(cat_id, cat_id),
            fields=[
                MetadataFieldResponse(
                    id=f["id"],
                    name=f["name"],
                    description=f["description"],
                    category=f["category"],
                    default_order=f["default_order"],
                    embed_tag=f["embed_tag"],
                )
                for f in fields
            ],
        )
        for cat_id, fields in fields_by_cat.items()
    ]

    return MetadataEmbedConfigResponse(
        sources=[
            MetadataSourceResponse(
                id=s["id"],
                name=s["name"],
                description=s["description"],
            )
            for s in METADATA_SOURCES
        ],
        fields=[
            MetadataFieldResponse(
                id=f["id"],
                name=f["name"],
                description=f["description"],
                category=f["category"],
                default_order=f["default_order"],
                embed_tag=f["embed_tag"],
            )
            for f in METADATA_FIELDS
        ],
        categories=categories,
    )


@router.get("/metadata-embed/preferences")
async def get_metadata_embed_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MetadataEmbedPreferencesModel:
    """
    Get user's metadata embed preferences.

    Returns the user's configured per-field source priorities.
    If user has no preferences, returns defaults.
    """
    repo = UserSettingsRepository(session)
    settings, _ = await repo.get_or_create(current_user.id)

    # Validate and normalize preferences
    validated = validate_embed_preferences(settings.metadata_embed_preferences)

    return MetadataEmbedPreferencesModel(
        default_order=validated["default_order"],
        fields={
            field_id: FieldPreferenceModel(
                order=pref["order"],
                enabled=pref["enabled"],
            )
            for field_id, pref in validated["fields"].items()
        },
    )


@router.put("/metadata-embed/preferences")
async def update_metadata_embed_preferences(
    data: MetadataEmbedPreferencesModel,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MetadataEmbedPreferencesModel:
    """
    Update user's metadata embed preferences.

    Validates the preferences and saves them. Invalid source IDs are
    filtered out, missing fields get defaults.
    """
    repo = UserSettingsRepository(session)
    settings, _ = await repo.get_or_create(current_user.id)

    # Convert to dict for validation
    prefs_dict = {
        "default_order": data.default_order,
        "fields": {
            field_id: {"order": pref.order, "enabled": pref.enabled}
            for field_id, pref in data.fields.items()
        },
    }

    # Validate and normalize
    validated = validate_embed_preferences(prefs_dict)

    # Save to database
    settings = await repo.update(settings, metadata_embed_preferences=validated)

    return MetadataEmbedPreferencesModel(
        default_order=validated["default_order"],
        fields={
            field_id: FieldPreferenceModel(
                order=pref["order"],
                enabled=pref["enabled"],
            )
            for field_id, pref in validated["fields"].items()
        },
    )


class FieldPreferenceUpdate(BaseModel):
    """Request to update a single field's preference."""

    order: list[str] | None = None  # If None, resets to default
    enabled: bool | None = None


@router.patch("/metadata-embed/preferences/field/{field_id}")
async def update_field_preference(
    field_id: str,
    data: FieldPreferenceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FieldPreferenceModel:
    """
    Update preference for a single metadata field.

    Use this for drag-and-drop reordering of sources for a specific field.
    Pass order=null to reset to default order for this field.
    """
    from spotdl.core.metadata_embed_config import METADATA_FIELD_BY_ID

    # Validate field exists
    if field_id not in METADATA_FIELD_BY_ID:
        raise HTTPException(status_code=404, detail=f"Unknown field: {field_id}")

    repo = UserSettingsRepository(session)
    settings, _ = await repo.get_or_create(current_user.id)

    # Get current preferences
    current = validate_embed_preferences(settings.metadata_embed_preferences)

    # Update the specific field
    if data.order is not None:
        current["fields"][field_id]["order"] = data.order
    else:
        # Reset to default order
        current["fields"][field_id]["order"] = METADATA_FIELD_BY_ID[field_id]["default_order"].copy()

    if data.enabled is not None:
        current["fields"][field_id]["enabled"] = data.enabled

    # Re-validate to filter invalid sources
    validated = validate_embed_preferences(current)

    # Save
    settings = await repo.update(settings, metadata_embed_preferences=validated)

    field_pref = validated["fields"][field_id]
    return FieldPreferenceModel(
        order=field_pref["order"],
        enabled=field_pref["enabled"],
    )


@router.post("/metadata-embed/preferences/reset")
async def reset_metadata_embed_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MetadataEmbedPreferencesModel:
    """
    Reset all metadata embed preferences to defaults.
    """
    repo = UserSettingsRepository(session)
    settings, _ = await repo.get_or_create(current_user.id)

    # Get defaults
    defaults = get_default_embed_preferences()

    # Save
    settings = await repo.update(settings, metadata_embed_preferences=defaults)

    return MetadataEmbedPreferencesModel(
        default_order=defaults["default_order"],
        fields={
            field_id: FieldPreferenceModel(
                order=pref["order"],
                enabled=pref["enabled"],
            )
            for field_id, pref in defaults["fields"].items()
        },
    )
