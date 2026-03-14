"""Provider preferences helper module.

Converts user preferences to provider instances for audio, metadata, and lyrics services.
"""

from __future__ import annotations

from typing import TypedDict

from spotdl.core.providers_config import (
    ProviderPreference,
    get_default_preferences,
    validate_preferences,
)
from spotdl.core.types.result import TargetPlatform


class AudioPreferences(TypedDict):
    """Audio provider preferences."""

    platforms: list[TargetPlatform]
    platform_ids: list[str]


class MetadataPreferences(TypedDict):
    """Metadata provider preferences."""

    provider_ids: list[str]
    enable_musicbrainz: bool
    enable_discogs: bool


class LyricsPreferences(TypedDict):
    """Lyrics provider preferences."""

    provider_ids: list[str]
    provider_order: list[str]


# Mapping from preference IDs to TargetPlatform enums
AUDIO_PLATFORM_MAP: dict[str, TargetPlatform] = {
    "youtube_music": TargetPlatform.YOUTUBE_MUSIC,
    "youtube": TargetPlatform.YOUTUBE,
    "soundcloud": TargetPlatform.SOUNDCLOUD,
    "bandcamp": TargetPlatform.BANDCAMP,
    "piped": TargetPlatform.PIPED,
}

# Default platform order (matches AUDIO_SOURCE_PROVIDERS order)
DEFAULT_PLATFORM_ORDER: list[TargetPlatform] = [
    TargetPlatform.YOUTUBE_MUSIC,
    TargetPlatform.YOUTUBE,
    TargetPlatform.SOUNDCLOUD,
    TargetPlatform.BANDCAMP,
    TargetPlatform.PIPED,
]

# Metadata provider IDs
METADATA_PROVIDER_IDS = {"musicbrainz", "discogs"}

# Lyrics provider IDs
LYRICS_PROVIDER_IDS = {"synced", "genius", "musixmatch", "azlyrics"}


def get_enabled_audio_platforms(
    preferences: list[ProviderPreference] | None,
) -> list[TargetPlatform]:
    """
    Convert user audio preferences to an ordered list of TargetPlatform enums.

    Args:
        preferences: User's audio source preferences (ordered list with enabled status)

    Returns:
        Ordered list of enabled TargetPlatform enums
    """
    # Validate and normalize preferences
    validated = validate_preferences(preferences, "audio")

    platforms: list[TargetPlatform] = []

    for pref in validated:
        if pref["enabled"]:
            platform = AUDIO_PLATFORM_MAP.get(pref["id"])
            if platform is not None:
                platforms.append(platform)

    # If no platforms enabled, use defaults
    if not platforms:
        return [
            AUDIO_PLATFORM_MAP[p["id"]]
            for p in get_default_preferences("audio")
            if p["enabled"] and p["id"] in AUDIO_PLATFORM_MAP
        ]

    return platforms


def get_enabled_metadata_provider_ids(
    preferences: list[ProviderPreference] | None,
) -> MetadataPreferences:
    """
    Convert user metadata preferences to enabled provider configuration.

    Args:
        preferences: User's metadata source preferences

    Returns:
        MetadataPreferences with provider IDs and enable flags
    """
    # Validate and normalize preferences
    validated = validate_preferences(preferences, "metadata")

    enabled_ids: list[str] = []
    enable_musicbrainz = False
    enable_discogs = False

    for pref in validated:
        if pref["enabled"] and pref["id"] in METADATA_PROVIDER_IDS:
            enabled_ids.append(pref["id"])
            if pref["id"] == "musicbrainz":
                enable_musicbrainz = True
            elif pref["id"] == "discogs":
                enable_discogs = True

    # If nothing enabled, use defaults
    if not enabled_ids:
        defaults = get_default_preferences("metadata")
        for pref in defaults:
            if pref["enabled"]:
                enabled_ids.append(pref["id"])
                if pref["id"] == "musicbrainz":
                    enable_musicbrainz = True
                elif pref["id"] == "discogs":
                    enable_discogs = True

    return MetadataPreferences(
        provider_ids=enabled_ids,
        enable_musicbrainz=enable_musicbrainz,
        enable_discogs=enable_discogs,
    )


def get_enabled_lyrics_provider_ids(
    preferences: list[ProviderPreference] | None,
) -> LyricsPreferences:
    """
    Convert user lyrics preferences to an ordered list of provider IDs.

    Args:
        preferences: User's lyrics source preferences

    Returns:
        LyricsPreferences with ordered provider IDs
    """
    # Validate and normalize preferences
    validated = validate_preferences(preferences, "lyrics")

    enabled_ids: list[str] = []

    for pref in validated:
        if pref["enabled"] and pref["id"] in LYRICS_PROVIDER_IDS:
            enabled_ids.append(pref["id"])

    # If nothing enabled, use defaults
    if not enabled_ids:
        defaults = get_default_preferences("lyrics")
        enabled_ids = [p["id"] for p in defaults if p["enabled"]]

    return LyricsPreferences(
        provider_ids=enabled_ids,
        provider_order=enabled_ids,
    )


def get_audio_platform_order_from_preferences(
    preferences: list[ProviderPreference] | None,
) -> list[str]:
    """
    Get the platform order as string IDs from preferences.

    Useful for services that need platform IDs rather than enums.

    Args:
        preferences: User's audio source preferences

    Returns:
        Ordered list of enabled platform IDs
    """
    platforms = get_enabled_audio_platforms(preferences)
    return [p.value for p in platforms]
