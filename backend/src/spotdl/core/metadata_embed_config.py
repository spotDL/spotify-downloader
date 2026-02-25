"""Configuration for metadata embedding preferences.

Defines available metadata sources, fields, and default priorities for
per-field source selection when viewing or embedding metadata.
"""

from __future__ import annotations

from typing import Any, TypedDict


class MetadataSourceInfo(TypedDict):
    """Information about a metadata source."""

    id: str
    name: str
    description: str


class MetadataFieldInfo(TypedDict):
    """Information about a metadata field."""

    id: str
    name: str
    description: str
    category: str
    default_order: list[str]  # Default source priority for this field
    embed_tag: str | None  # ID3/MP4 tag name for embedding (None if not embeddable)


class FieldPreference(TypedDict):
    """User preference for a single field."""

    order: list[str]  # Source priority order
    enabled: bool  # Whether to include this field


class MetadataEmbedPreferences(TypedDict):
    """Complete metadata embed preferences structure."""

    default_order: list[str]  # Default source order for fields without overrides
    fields: dict[str, FieldPreference]  # Per-field preferences


# Available metadata sources
METADATA_SOURCES: list[MetadataSourceInfo] = [
    {
        "id": "spotify",
        "name": "Spotify",
        "description": "Primary source with rich metadata, cover art, and audio features",
    },
    {
        "id": "musicbrainz",
        "name": "MusicBrainz",
        "description": "Open music database with accurate ISRC, genres, and release info",
    },
    {
        "id": "discogs",
        "name": "Discogs",
        "description": "Comprehensive database with detailed genre/style and label info",
    },
    {
        "id": "deezer",
        "name": "Deezer",
        "description": "Alternative streaming source with BPM and gain data",
    },
    {
        "id": "apple_music",
        "name": "Apple Music",
        "description": "Apple's music service with lyrics and composer credits",
    },
]

METADATA_SOURCE_IDS = {s["id"] for s in METADATA_SOURCES}

# Field categories for UI organization
FIELD_CATEGORIES = {
    "core": "Core Information",
    "classification": "Classification",
    "identifiers": "Identifiers",
    "publishing": "Publishing",
    "media": "Media",
    "audio_features": "Audio Features",
    "credits": "Credits",
}

# Available metadata fields with their properties
METADATA_FIELDS: list[MetadataFieldInfo] = [
    # Core Information
    {
        "id": "name",
        "name": "Title",
        "description": "Song title/name",
        "category": "core",
        "default_order": ["spotify", "deezer", "apple_music", "musicbrainz"],
        "embed_tag": "title",
    },
    {
        "id": "artists",
        "name": "Artists",
        "description": "Artist name(s)",
        "category": "core",
        "default_order": ["spotify", "deezer", "apple_music", "musicbrainz"],
        "embed_tag": "artist",
    },
    {
        "id": "album_name",
        "name": "Album",
        "description": "Album name",
        "category": "core",
        "default_order": ["spotify", "deezer", "apple_music", "musicbrainz"],
        "embed_tag": "album",
    },
    {
        "id": "album_artist",
        "name": "Album Artist",
        "description": "Album artist (may differ from track artist)",
        "category": "core",
        "default_order": ["spotify", "musicbrainz", "discogs"],
        "embed_tag": "albumartist",
    },
    {
        "id": "track_number",
        "name": "Track Number",
        "description": "Track position in album",
        "category": "core",
        "default_order": ["spotify", "deezer", "musicbrainz"],
        "embed_tag": "tracknumber",
    },
    {
        "id": "disc_number",
        "name": "Disc Number",
        "description": "Disc number for multi-disc albums",
        "category": "core",
        "default_order": ["spotify", "deezer", "musicbrainz"],
        "embed_tag": "discnumber",
    },
    # Classification
    {
        "id": "genres",
        "name": "Genres",
        "description": "Music genres",
        "category": "classification",
        "default_order": ["musicbrainz", "discogs", "spotify"],
        "embed_tag": "genre",
    },
    {
        "id": "year",
        "name": "Year",
        "description": "Release year",
        "category": "classification",
        "default_order": ["spotify", "musicbrainz", "discogs"],
        "embed_tag": "date",
    },
    {
        "id": "release_date",
        "name": "Release Date",
        "description": "Full release date",
        "category": "classification",
        "default_order": ["spotify", "musicbrainz", "discogs"],
        "embed_tag": "date",
    },
    {
        "id": "explicit",
        "name": "Explicit",
        "description": "Explicit content flag",
        "category": "classification",
        "default_order": ["spotify", "deezer", "apple_music"],
        "embed_tag": None,  # No standard tag
    },
    # Identifiers
    {
        "id": "isrc",
        "name": "ISRC",
        "description": "International Standard Recording Code",
        "category": "identifiers",
        "default_order": ["musicbrainz", "spotify", "deezer"],
        "embed_tag": "isrc",
    },
    {
        "id": "musicbrainz_id",
        "name": "MusicBrainz ID",
        "description": "MusicBrainz recording ID",
        "category": "identifiers",
        "default_order": ["musicbrainz"],
        "embed_tag": "musicbrainz_trackid",
    },
    {
        "id": "discogs_id",
        "name": "Discogs ID",
        "description": "Discogs release ID",
        "category": "identifiers",
        "default_order": ["discogs"],
        "embed_tag": None,
    },
    # Publishing
    {
        "id": "label",
        "name": "Label",
        "description": "Record label",
        "category": "publishing",
        "default_order": ["discogs", "musicbrainz", "spotify"],
        "embed_tag": "label",
    },
    {
        "id": "copyright_text",
        "name": "Copyright",
        "description": "Copyright information",
        "category": "publishing",
        "default_order": ["spotify", "discogs"],
        "embed_tag": "copyright",
    },
    {
        "id": "publisher",
        "name": "Publisher",
        "description": "Music publisher",
        "category": "publishing",
        "default_order": ["discogs", "musicbrainz"],
        "embed_tag": "publisher",
    },
    # Media
    {
        "id": "cover_url",
        "name": "Cover Art",
        "description": "Album cover image",
        "category": "media",
        "default_order": ["spotify", "deezer", "discogs", "apple_music"],
        "embed_tag": "artwork",
    },
    {
        "id": "lyrics",
        "name": "Lyrics",
        "description": "Song lyrics (synced or plain)",
        "category": "media",
        "default_order": ["synced", "genius", "musixmatch", "azlyrics"],
        "embed_tag": "lyrics",
    },
    # Audio Features
    {
        "id": "bpm",
        "name": "BPM",
        "description": "Beats per minute / tempo",
        "category": "audio_features",
        "default_order": ["spotify", "deezer"],
        "embed_tag": "bpm",
    },
    {
        "id": "key",
        "name": "Key",
        "description": "Musical key",
        "category": "audio_features",
        "default_order": ["spotify"],
        "embed_tag": "initialkey",
    },
    {
        "id": "time_signature",
        "name": "Time Signature",
        "description": "Time signature (e.g., 4/4)",
        "category": "audio_features",
        "default_order": ["spotify"],
        "embed_tag": None,
    },
    {
        "id": "loudness",
        "name": "Loudness",
        "description": "Track loudness in dB",
        "category": "audio_features",
        "default_order": ["spotify", "deezer"],
        "embed_tag": None,
    },
    {
        "id": "energy",
        "name": "Energy",
        "description": "Energy level (0-1)",
        "category": "audio_features",
        "default_order": ["spotify"],
        "embed_tag": None,
    },
    {
        "id": "danceability",
        "name": "Danceability",
        "description": "Danceability score (0-1)",
        "category": "audio_features",
        "default_order": ["spotify"],
        "embed_tag": None,
    },
    {
        "id": "valence",
        "name": "Valence",
        "description": "Musical positivity (0-1)",
        "category": "audio_features",
        "default_order": ["spotify"],
        "embed_tag": None,
    },
    # Credits
    {
        "id": "composer",
        "name": "Composer",
        "description": "Song composer(s)",
        "category": "credits",
        "default_order": ["musicbrainz", "apple_music", "discogs"],
        "embed_tag": "composer",
    },
    {
        "id": "producer",
        "name": "Producer",
        "description": "Track producer(s)",
        "category": "credits",
        "default_order": ["musicbrainz", "discogs"],
        "embed_tag": None,
    },
    {
        "id": "writer",
        "name": "Writer",
        "description": "Songwriter(s)",
        "category": "credits",
        "default_order": ["musicbrainz", "apple_music"],
        "embed_tag": "writer",
    },
]

# Build lookup dictionaries
METADATA_FIELD_BY_ID: dict[str, MetadataFieldInfo] = {f["id"]: f for f in METADATA_FIELDS}
METADATA_FIELD_IDS = set(METADATA_FIELD_BY_ID.keys())

# Default source order (used when field has no override)
DEFAULT_SOURCE_ORDER = ["spotify", "musicbrainz", "discogs", "deezer", "apple_music"]


def get_default_embed_preferences() -> MetadataEmbedPreferences:
    """
    Get default metadata embed preferences.

    Returns preferences where each field uses its recommended default order.
    """
    fields: dict[str, FieldPreference] = {}

    for field in METADATA_FIELDS:
        fields[field["id"]] = FieldPreference(
            order=field["default_order"].copy(),
            enabled=True,
        )

    return MetadataEmbedPreferences(
        default_order=DEFAULT_SOURCE_ORDER.copy(),
        fields=fields,
    )


def validate_embed_preferences(
    preferences: dict[str, Any] | None,
) -> MetadataEmbedPreferences:
    """
    Validate and normalize metadata embed preferences.

    Ensures all fields are present and have valid source IDs.
    Missing fields get defaults, invalid sources are filtered out.

    Args:
        preferences: User's embed preferences (may be None or partial)

    Returns:
        Complete, validated MetadataEmbedPreferences
    """
    defaults = get_default_embed_preferences()

    if preferences is None:
        return defaults

    # Validate default_order
    default_order = preferences.get("default_order", [])
    if not default_order or not isinstance(default_order, list):
        default_order = defaults["default_order"]
    else:
        # Filter to valid sources only
        default_order = [s for s in default_order if s in METADATA_SOURCE_IDS]
        if not default_order:
            default_order = defaults["default_order"]

    # Validate fields
    user_fields = preferences.get("fields", {})
    validated_fields: dict[str, FieldPreference] = {}

    for field_id in METADATA_FIELD_IDS:
        if field_id in user_fields and isinstance(user_fields[field_id], dict):
            user_field = user_fields[field_id]

            # Validate order
            order = user_field.get("order", [])
            if not order or not isinstance(order, list):
                order = defaults["fields"][field_id]["order"]
            else:
                # Filter to valid sources
                order = [s for s in order if s in METADATA_SOURCE_IDS]
                if not order:
                    order = defaults["fields"][field_id]["order"]

            # Validate enabled
            enabled = user_field.get("enabled", True)
            if not isinstance(enabled, bool):
                enabled = True

            validated_fields[field_id] = FieldPreference(
                order=order,
                enabled=enabled,
            )
        else:
            # Use default for this field
            validated_fields[field_id] = defaults["fields"][field_id]

    return MetadataEmbedPreferences(
        default_order=default_order,
        fields=validated_fields,
    )


def get_fields_by_category() -> dict[str, list[MetadataFieldInfo]]:
    """
    Get metadata fields grouped by category.

    Useful for UI organization (showing fields in logical groups).
    """
    result: dict[str, list[MetadataFieldInfo]] = {}

    for field in METADATA_FIELDS:
        category = field["category"]
        if category not in result:
            result[category] = []
        result[category].append(field)

    return result


def get_embeddable_fields() -> list[MetadataFieldInfo]:
    """Get fields that can be embedded in audio files."""
    return [f for f in METADATA_FIELDS if f["embed_tag"] is not None]
