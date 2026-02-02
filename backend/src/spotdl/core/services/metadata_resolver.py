"""Metadata resolver service.

Resolves metadata fields from multiple sources based on user preferences,
providing per-field source selection for viewing and embedding.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from spotdl.core.metadata_embed_config import (
    METADATA_FIELD_BY_ID,
    METADATA_FIELD_IDS,
    MetadataEmbedPreferences,
    get_default_embed_preferences,
    validate_embed_preferences,
)

if TYPE_CHECKING:
    from spotdl.db.models.metadata_snapshot import MetadataSnapshot
    from spotdl.db.models.song import Song

logger = logging.getLogger(__name__)


@dataclass
class ResolvedField:
    """A resolved metadata field with its value and source."""

    field_id: str
    value: Any
    source: str | None  # None if no source had this field
    enabled: bool = True  # Whether user wants this field


@dataclass
class ResolvedMetadata:
    """Complete resolved metadata for a song."""

    song_id: str
    fields: dict[str, ResolvedField] = field(default_factory=dict)

    def get(self, field_id: str) -> Any:
        """Get the resolved value for a field."""
        if field_id in self.fields:
            return self.fields[field_id].value
        return None

    def get_source(self, field_id: str) -> str | None:
        """Get the source that provided a field's value."""
        if field_id in self.fields:
            return self.fields[field_id].source
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with values only."""
        return {
            field_id: resolved.value
            for field_id, resolved in self.fields.items()
            if resolved.value is not None and resolved.enabled
        }

    def to_dict_with_sources(self) -> dict[str, dict[str, Any]]:
        """Convert to dictionary with values and sources."""
        return {
            field_id: {
                "value": resolved.value,
                "source": resolved.source,
                "enabled": resolved.enabled,
            }
            for field_id, resolved in self.fields.items()
        }

    def get_embed_dict(self) -> dict[str, Any]:
        """Get dictionary of values for embedding (enabled fields with embed tags only)."""
        from spotdl.core.metadata_embed_config import METADATA_FIELD_BY_ID

        result = {}
        for field_id, resolved in self.fields.items():
            if not resolved.enabled or resolved.value is None:
                continue

            field_info = METADATA_FIELD_BY_ID.get(field_id)
            if field_info and field_info["embed_tag"]:
                result[field_info["embed_tag"]] = resolved.value

        return result


class MetadataResolver:
    """
    Resolves metadata from multiple sources based on user preferences.

    For each metadata field, checks sources in the user's preferred order
    and uses the first source that has a non-empty value for that field.
    """

    def __init__(
        self,
        preferences: MetadataEmbedPreferences | dict | None = None,
    ) -> None:
        """
        Initialize the resolver.

        Args:
            preferences: User's metadata embed preferences (validated or raw)
        """
        if preferences is None or isinstance(preferences, dict):
            self._preferences = validate_embed_preferences(preferences)
        else:
            self._preferences = preferences

    @property
    def preferences(self) -> MetadataEmbedPreferences:
        """Get the validated preferences."""
        return self._preferences

    def resolve(
        self,
        song_id: str,
        snapshots: list[MetadataSnapshot],
        primary_song: Song | None = None,
    ) -> ResolvedMetadata:
        """
        Resolve metadata from snapshots using configured preferences.

        Args:
            song_id: The song's UUID as string
            snapshots: List of MetadataSnapshot objects from different sources
            primary_song: Optional Song model to use as primary/fallback source

        Returns:
            ResolvedMetadata with fields resolved according to preferences
        """
        # Build lookup: source -> snapshot_data
        snapshots_by_source: dict[str, dict[str, Any]] = {}

        for snapshot in snapshots:
            source = snapshot.source.lower()
            snapshots_by_source[source] = snapshot.snapshot_data or {}

        # Add primary song data as a source if provided
        if primary_song is not None:
            primary_data = self._song_to_snapshot_data(primary_song)
            source = primary_song.platform.lower()
            # Only add if we don't already have a snapshot from this source
            # or merge with existing
            if source in snapshots_by_source:
                # Merge: song model data fills in gaps
                for key, value in primary_data.items():
                    if key not in snapshots_by_source[source] or not snapshots_by_source[source][key]:
                        snapshots_by_source[source][key] = value
            else:
                snapshots_by_source[source] = primary_data

        # Resolve each field
        result = ResolvedMetadata(song_id=song_id)

        for field_id in METADATA_FIELD_IDS:
            field_pref = self._preferences["fields"].get(field_id)

            if field_pref is None:
                # No preference for this field, use default order
                order = self._preferences["default_order"]
                enabled = True
            else:
                order = field_pref["order"]
                enabled = field_pref["enabled"]

            # Find first source with a value for this field
            value = None
            source = None

            for source_id in order:
                if source_id in snapshots_by_source:
                    snapshot_data = snapshots_by_source[source_id]
                    field_value = self._get_field_value(snapshot_data, field_id)

                    if field_value is not None and field_value != "" and field_value != []:
                        value = field_value
                        source = source_id
                        break

            # If still no value, try any remaining source
            if value is None:
                for source_id, snapshot_data in snapshots_by_source.items():
                    if source_id not in order:
                        field_value = self._get_field_value(snapshot_data, field_id)
                        if field_value is not None and field_value != "" and field_value != []:
                            value = field_value
                            source = source_id
                            break

            result.fields[field_id] = ResolvedField(
                field_id=field_id,
                value=value,
                source=source,
                enabled=enabled,
            )

        return result

    def _get_field_value(self, data: dict[str, Any], field_id: str) -> Any:
        """
        Extract a field value from snapshot data.

        Handles field name variations and nested structures.
        """
        # Direct match
        if field_id in data:
            return data[field_id]

        # Common field name variations
        aliases = {
            "name": ["title", "track_name", "song_name"],
            "artists": ["artist_names", "artist_list"],
            "album_name": ["album", "album_title"],
            "album_artist": ["albumartist", "album_artists"],
            "year": ["release_year"],
            "release_date": ["date", "released"],
            "genres": ["genre", "genre_list", "styles"],
            "label": ["record_label", "labels"],
            "bpm": ["tempo"],
            "cover_url": ["artwork_url", "image_url", "thumbnail_url", "cover"],
            "copyright_text": ["copyright"],
            "explicit": ["is_explicit", "parental_advisory"],
        }

        if field_id in aliases:
            for alias in aliases[field_id]:
                if alias in data:
                    return data[alias]

        return None

    def _song_to_snapshot_data(self, song: Song) -> dict[str, Any]:
        """Convert a Song model to snapshot-like data dict."""
        data: dict[str, Any] = {
            "name": song.name,
            "artists": song.artists,
            "album_name": song.album_name,
            "isrc": song.isrc,
            "genres": song.genres,
            "explicit": song.explicit,
            "popularity": song.popularity,
            "label": song.label,
            "copyright_text": song.copyright_text,
            "musicbrainz_id": song.musicbrainz_id,
            "discogs_id": song.discogs_id,
        }

        # Add from metadata_json if available
        metadata = song.metadata_json or {}
        data["year"] = metadata.get("year") or (song.release_date.year if song.release_date else None)
        data["release_date"] = str(song.release_date) if song.release_date else None
        data["cover_url"] = metadata.get("cover_url")
        data["track_number"] = metadata.get("track_number")
        data["disc_number"] = metadata.get("disc_number")

        # Audio features
        if song.bpm:
            data["bpm"] = float(song.bpm)
        if song.key is not None:
            data["key"] = song.key
        if song.time_signature:
            data["time_signature"] = song.time_signature
        if song.energy:
            data["energy"] = float(song.energy)
        if song.danceability:
            data["danceability"] = float(song.danceability)
        if song.valence:
            data["valence"] = float(song.valence)
        if song.loudness:
            data["loudness"] = float(song.loudness)

        return {k: v for k, v in data.items() if v is not None}

    def resolve_from_song(
        self,
        song: Song,
        snapshots: list[MetadataSnapshot] | None = None,
    ) -> ResolvedMetadata:
        """
        Convenience method to resolve metadata for a Song model.

        Args:
            song: Song model
            snapshots: Optional list of snapshots (will use song's platform as fallback)

        Returns:
            ResolvedMetadata
        """
        return self.resolve(
            song_id=str(song.id),
            snapshots=snapshots or [],
            primary_song=song,
        )


def get_metadata_resolver(
    preferences: MetadataEmbedPreferences | dict | None = None,
) -> MetadataResolver:
    """
    Factory function to create a MetadataResolver.

    Args:
        preferences: User's metadata embed preferences

    Returns:
        Configured MetadataResolver instance
    """
    return MetadataResolver(preferences=preferences)
