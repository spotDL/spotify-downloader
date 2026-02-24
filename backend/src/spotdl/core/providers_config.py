"""Provider configuration for audio sources, metadata, and lyrics."""

from __future__ import annotations

from typing import TypedDict


class ProviderInfo(TypedDict):
    """Information about a provider."""

    id: str
    name: str
    icon: str
    default_enabled: bool


class ProviderPreference(TypedDict):
    """User preference for a provider."""

    id: str
    enabled: bool


# Audio source providers for downloading
AUDIO_SOURCE_PROVIDERS: list[ProviderInfo] = [
    {
        "id": "youtube_music",
        "name": "YouTube Music",
        "icon": "youtube-music",
        "default_enabled": True,
    },
    {
        "id": "youtube",
        "name": "YouTube",
        "icon": "youtube",
        "default_enabled": True,
    },
    {
        "id": "soundcloud",
        "name": "SoundCloud",
        "icon": "soundcloud",
        "default_enabled": True,
    },
    {
        "id": "bandcamp",
        "name": "Bandcamp",
        "icon": "bandcamp",
        "default_enabled": True,
    },
    {
        "id": "piped",
        "name": "Piped",
        "icon": "piped",
        "default_enabled": True,
    },
]

# Metadata providers for enriching song information
METADATA_PROVIDERS: list[ProviderInfo] = [
    {
        "id": "spotify",
        "name": "Spotify",
        "icon": "spotify",
        "default_enabled": True,
    },
    {
        "id": "musicbrainz",
        "name": "MusicBrainz",
        "icon": "musicbrainz",
        "default_enabled": True,
    },
    {
        "id": "discogs",
        "name": "Discogs",
        "icon": "discogs",
        "default_enabled": True,
    },
    {
        "id": "deezer",
        "name": "Deezer",
        "icon": "deezer",
        "default_enabled": True,
    },
]

# Lyrics providers
LYRICS_PROVIDERS: list[ProviderInfo] = [
    {
        "id": "synced",
        "name": "Synced Lyrics",
        "icon": "music-note",
        "default_enabled": True,
    },
    {
        "id": "genius",
        "name": "Genius",
        "icon": "genius",
        "default_enabled": True,
    },
    {
        "id": "musixmatch",
        "name": "Musixmatch",
        "icon": "musixmatch",
        "default_enabled": True,
    },
    {
        "id": "azlyrics",
        "name": "AZLyrics",
        "icon": "azlyrics",
        "default_enabled": False,
    },
]


def get_default_preferences(category: str) -> list[ProviderPreference]:
    """
    Get default provider preferences for a category.

    Args:
        category: One of 'audio', 'metadata', or 'lyrics'

    Returns:
        List of provider preferences with id and enabled status
    """
    providers_map = {
        "audio": AUDIO_SOURCE_PROVIDERS,
        "metadata": METADATA_PROVIDERS,
        "lyrics": LYRICS_PROVIDERS,
    }

    providers = providers_map.get(category, [])
    return [{"id": p["id"], "enabled": p["default_enabled"]} for p in providers]


def get_all_providers() -> dict[str, list[ProviderInfo]]:
    """Get all available providers grouped by category."""
    return {
        "audio_sources": AUDIO_SOURCE_PROVIDERS,
        "metadata_sources": METADATA_PROVIDERS,
        "lyrics_sources": LYRICS_PROVIDERS,
    }


def validate_preferences(
    preferences: list[ProviderPreference] | None,
    category: str,
) -> list[ProviderPreference]:
    """
    Validate and normalize provider preferences.

    Ensures all valid providers are present and removes invalid ones.

    Args:
        preferences: User's provider preferences
        category: Provider category ('audio', 'metadata', 'lyrics')

    Returns:
        Normalized list of provider preferences
    """
    if preferences is None:
        return get_default_preferences(category)

    providers_map = {
        "audio": AUDIO_SOURCE_PROVIDERS,
        "metadata": METADATA_PROVIDERS,
        "lyrics": LYRICS_PROVIDERS,
    }

    valid_providers = providers_map.get(category, [])
    valid_ids = {p["id"] for p in valid_providers}

    # Build normalized list maintaining user order for existing prefs
    result: list[ProviderPreference] = []
    seen_ids: set[str] = set()

    # First, add existing preferences in their order
    for pref in preferences:
        if pref["id"] in valid_ids and pref["id"] not in seen_ids:
            result.append(pref)
            seen_ids.add(pref["id"])

    # Then, add any missing providers at the end with defaults
    for provider in valid_providers:
        if provider["id"] not in seen_ids:
            result.append({
                "id": provider["id"],
                "enabled": provider["default_enabled"],
            })

    return result
