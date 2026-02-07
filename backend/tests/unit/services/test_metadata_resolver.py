"""Tests for MetadataResolver service."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock
import uuid

import pytest

from spotdl.core.services.metadata_resolver import (
    MetadataResolver,
    ResolvedField,
    ResolvedMetadata,
    get_metadata_resolver,
)
from spotdl.core.metadata_embed_config import (
    MetadataEmbedPreferences,
    get_default_embed_preferences,
)


@pytest.fixture
def sample_song_id() -> str:
    """Create a sample song ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_snapshot_spotify() -> MagicMock:
    """Create a mock Spotify metadata snapshot."""
    snapshot = MagicMock()
    snapshot.source = "spotify"
    snapshot.snapshot_data = {
        "name": "Spotify Title",
        "artists": ["Spotify Artist 1", "Spotify Artist 2"],
        "album_name": "Spotify Album",
        "year": 2023,
        "genres": ["Pop", "Rock"],
        "explicit": True,
        "cover_url": "https://spotify.com/cover.jpg",
        "bpm": 120.0,
        "key": 5,
        "energy": 0.8,
    }
    return snapshot


@pytest.fixture
def mock_snapshot_musicbrainz() -> MagicMock:
    """Create a mock MusicBrainz metadata snapshot."""
    snapshot = MagicMock()
    snapshot.source = "musicbrainz"
    snapshot.snapshot_data = {
        "name": "MusicBrainz Title",
        "artists": ["MusicBrainz Artist"],
        "album_name": "MusicBrainz Album",
        "isrc": "USRC17607839",
        "genres": ["Alternative Rock", "Indie"],
        "year": 2022,
        "musicbrainz_id": "mb123456",
        "label": "MusicBrainz Label",
    }
    return snapshot


@pytest.fixture
def mock_snapshot_discogs() -> MagicMock:
    """Create a mock Discogs metadata snapshot."""
    snapshot = MagicMock()
    snapshot.source = "discogs"
    snapshot.snapshot_data = {
        "name": "Discogs Title",
        "artists": ["Discogs Artist"],
        "genres": ["Electronic", "Dance"],
        "label": "Discogs Label",
        "copyright_text": "© 2023 Discogs Records",
        "discogs_id": "dg789",
    }
    return snapshot


@pytest.fixture
def mock_song() -> MagicMock:
    """Create a mock Song model."""
    song = MagicMock()
    song.id = uuid.uuid4()
    song.platform = "spotify"
    song.name = "Song Title"
    song.artists = ["Primary Artist"]
    song.album_name = "Album Name"
    song.isrc = "USRC12345678"
    song.genres = ["Pop"]
    song.explicit = False
    song.popularity = 75
    song.label = "Song Label"
    song.copyright_text = "© 2023 Song Copyright"
    song.musicbrainz_id = "mb-song-123"
    song.discogs_id = "dg-song-456"
    song.release_date = date(2023, 5, 15)
    song.bpm = 128.0
    song.key = 7
    song.time_signature = 4
    song.energy = 0.75
    song.danceability = 0.65
    song.valence = 0.55
    song.loudness = -5.5
    song.metadata_json = {
        "year": 2023,
        "cover_url": "https://example.com/cover.jpg",
        "track_number": 5,
        "disc_number": 1,
    }
    return song


class TestResolvedField:
    """Tests for ResolvedField dataclass."""

    def test_init_with_defaults(self) -> None:
        """Test ResolvedField initialization with default values."""
        field = ResolvedField(
            field_id="name",
            value="Test Song",
            source="spotify",
        )
        assert field.field_id == "name"
        assert field.value == "Test Song"
        assert field.source == "spotify"
        assert field.enabled is True

    def test_init_with_disabled(self) -> None:
        """Test ResolvedField initialization with disabled flag."""
        field = ResolvedField(
            field_id="explicit",
            value=True,
            source="spotify",
            enabled=False,
        )
        assert field.enabled is False


class TestResolvedMetadata:
    """Tests for ResolvedMetadata dataclass."""

    def test_get_existing_field(self, sample_song_id: str) -> None:
        """Test getting value of an existing field."""
        resolved = ResolvedMetadata(song_id=sample_song_id)
        resolved.fields["name"] = ResolvedField("name", "Test Song", "spotify")

        assert resolved.get("name") == "Test Song"

    def test_get_missing_field(self, sample_song_id: str) -> None:
        """Test getting value of a missing field returns None."""
        resolved = ResolvedMetadata(song_id=sample_song_id)
        assert resolved.get("nonexistent") is None

    def test_get_source_existing(self, sample_song_id: str) -> None:
        """Test getting source of an existing field."""
        resolved = ResolvedMetadata(song_id=sample_song_id)
        resolved.fields["isrc"] = ResolvedField("isrc", "USRC123", "musicbrainz")

        assert resolved.get_source("isrc") == "musicbrainz"

    def test_get_source_missing(self, sample_song_id: str) -> None:
        """Test getting source of a missing field returns None."""
        resolved = ResolvedMetadata(song_id=sample_song_id)
        assert resolved.get_source("nonexistent") is None

    def test_to_dict_only_enabled_with_values(self, sample_song_id: str) -> None:
        """Test to_dict includes only enabled fields with non-None values."""
        resolved = ResolvedMetadata(song_id=sample_song_id)
        resolved.fields["name"] = ResolvedField("name", "Song", "spotify", enabled=True)
        resolved.fields["isrc"] = ResolvedField("isrc", None, None, enabled=True)
        resolved.fields["year"] = ResolvedField("year", 2023, "musicbrainz", enabled=False)

        result = resolved.to_dict()

        assert result == {"name": "Song"}
        assert "isrc" not in result  # None value excluded
        assert "year" not in result  # Disabled field excluded

    def test_to_dict_with_sources(self, sample_song_id: str) -> None:
        """Test to_dict_with_sources includes metadata for all fields."""
        resolved = ResolvedMetadata(song_id=sample_song_id)
        resolved.fields["name"] = ResolvedField("name", "Song", "spotify", enabled=True)
        resolved.fields["isrc"] = ResolvedField("isrc", None, None, enabled=False)

        result = resolved.to_dict_with_sources()

        assert result == {
            "name": {"value": "Song", "source": "spotify", "enabled": True},
            "isrc": {"value": None, "source": None, "enabled": False},
        }

    def test_get_embed_dict_only_embeddable(self, sample_song_id: str) -> None:
        """Test get_embed_dict includes only enabled embeddable fields."""
        resolved = ResolvedMetadata(song_id=sample_song_id)
        # name has embed_tag "title"
        resolved.fields["name"] = ResolvedField("name", "Song", "spotify", enabled=True)
        # explicit has no embed_tag
        resolved.fields["explicit"] = ResolvedField("explicit", True, "spotify", enabled=True)
        # year has embed_tag "date"
        resolved.fields["year"] = ResolvedField("year", 2023, "musicbrainz", enabled=False)

        result = resolved.get_embed_dict()

        assert result == {"title": "Song"}
        assert "explicit" not in result  # No embed_tag
        assert "date" not in result  # Disabled


class TestMetadataResolverInit:
    """Tests for MetadataResolver initialization."""

    def test_init_with_none_preferences(self) -> None:
        """Test initialization with None preferences uses defaults."""
        resolver = MetadataResolver(preferences=None)
        assert resolver.preferences is not None
        assert "default_order" in resolver.preferences
        assert "fields" in resolver.preferences

    def test_init_with_dict_preferences(self) -> None:
        """Test initialization with dict preferences validates them."""
        prefs = {
            "default_order": ["spotify", "musicbrainz"],
            "fields": {},
        }
        resolver = MetadataResolver(preferences=prefs)
        assert resolver.preferences["default_order"] == ["spotify", "musicbrainz"]

    def test_init_with_typed_preferences(self) -> None:
        """Test initialization with MetadataEmbedPreferences object."""
        prefs = get_default_embed_preferences()
        resolver = MetadataResolver(preferences=prefs)
        assert resolver.preferences == prefs


class TestMetadataResolverResolve:
    """Tests for MetadataResolver.resolve method."""

    def test_resolve_single_source(
        self, sample_song_id: str, mock_snapshot_spotify: MagicMock
    ) -> None:
        """Test resolving metadata from a single source."""
        resolver = MetadataResolver()
        result = resolver.resolve(sample_song_id, [mock_snapshot_spotify])

        assert result.song_id == sample_song_id
        assert result.get("name") == "Spotify Title"
        assert result.get("artists") == ["Spotify Artist 1", "Spotify Artist 2"]
        assert result.get_source("name") == "spotify"

    def test_resolve_multiple_sources_priority(
        self,
        sample_song_id: str,
        mock_snapshot_spotify: MagicMock,
        mock_snapshot_musicbrainz: MagicMock,
    ) -> None:
        """Test resolving with multiple sources respects priority order."""
        # Default order for "name" is ["spotify", "deezer", "apple_music", "musicbrainz"]
        resolver = MetadataResolver()
        result = resolver.resolve(
            sample_song_id,
            [mock_snapshot_musicbrainz, mock_snapshot_spotify],
        )

        # Should prefer Spotify (higher priority) for name
        assert result.get("name") == "Spotify Title"
        assert result.get_source("name") == "spotify"

        # Should prefer MusicBrainz for ISRC (not in Spotify snapshot)
        assert result.get("isrc") == "USRC17607839"
        assert result.get_source("isrc") == "musicbrainz"

    def test_resolve_fallback_to_any_source(
        self, sample_song_id: str, mock_snapshot_discogs: MagicMock
    ) -> None:
        """Test fallback to any available source when preferred sources unavailable."""
        # Discogs is not in default order for most fields
        resolver = MetadataResolver()
        result = resolver.resolve(sample_song_id, [mock_snapshot_discogs])

        # Should still use Discogs even though it's not in priority list
        assert result.get("name") == "Discogs Title"
        assert result.get_source("name") == "discogs"

    def test_resolve_custom_field_order(
        self,
        sample_song_id: str,
        mock_snapshot_spotify: MagicMock,
        mock_snapshot_musicbrainz: MagicMock,
    ) -> None:
        """Test custom field order overrides default."""
        prefs: MetadataEmbedPreferences = {
            "default_order": ["spotify"],
            "fields": {
                "name": {
                    "order": ["musicbrainz", "spotify"],
                    "enabled": True,
                }
            },
        }
        resolver = MetadataResolver(preferences=prefs)
        result = resolver.resolve(
            sample_song_id,
            [mock_snapshot_spotify, mock_snapshot_musicbrainz],
        )

        # Should prefer MusicBrainz for name due to custom order
        assert result.get("name") == "MusicBrainz Title"
        assert result.get_source("name") == "musicbrainz"

    def test_resolve_disabled_field(
        self, sample_song_id: str, mock_snapshot_spotify: MagicMock
    ) -> None:
        """Test disabled fields are marked but still resolved."""
        prefs: MetadataEmbedPreferences = {
            "default_order": ["spotify"],
            "fields": {
                "explicit": {
                    "order": ["spotify"],
                    "enabled": False,
                }
            },
        }
        resolver = MetadataResolver(preferences=prefs)
        result = resolver.resolve(sample_song_id, [mock_snapshot_spotify])

        # Field should be resolved but marked as disabled
        assert result.fields["explicit"].value is True
        assert result.fields["explicit"].enabled is False

        # Should not appear in to_dict()
        data = result.to_dict()
        assert "explicit" not in data

    def test_resolve_empty_values_skipped(
        self, sample_song_id: str
    ) -> None:
        """Test that empty strings and empty lists are skipped."""
        snapshot = MagicMock()
        snapshot.source = "test"
        snapshot.snapshot_data = {
            "name": "",  # Empty string
            "artists": [],  # Empty list
            "album_name": "Valid Album",
        }

        resolver = MetadataResolver()
        result = resolver.resolve(sample_song_id, [snapshot])

        # Empty values should result in None
        assert result.get("name") is None
        assert result.get("artists") is None
        assert result.get_source("name") is None

        # Valid values should work
        assert result.get("album_name") == "Valid Album"

    def test_resolve_with_primary_song(
        self, sample_song_id: str, mock_song: MagicMock
    ) -> None:
        """Test resolving with primary song as fallback source."""
        resolver = MetadataResolver()
        result = resolver.resolve(sample_song_id, [], primary_song=mock_song)

        # Should use song data as source
        assert result.get("name") == "Song Title"
        assert result.get("isrc") == "USRC12345678"
        assert result.get_source("name") == "spotify"  # Song's platform

    def test_resolve_primary_song_merges_with_snapshots(
        self,
        sample_song_id: str,
        mock_song: MagicMock,
        mock_snapshot_spotify: MagicMock,
    ) -> None:
        """Test primary song data merges with existing snapshot."""
        # Mock song has same platform as snapshot
        mock_song.platform = "spotify"

        resolver = MetadataResolver()
        result = resolver.resolve(
            sample_song_id,
            [mock_snapshot_spotify],
            primary_song=mock_song,
        )

        # Snapshot data should be preferred
        assert result.get("name") == "Spotify Title"

        # Song data should fill gaps (ISRC not in snapshot)
        assert result.get("isrc") == "USRC12345678"

    def test_resolve_no_sources_returns_none_values(
        self, sample_song_id: str
    ) -> None:
        """Test resolving with no sources returns None for all fields."""
        resolver = MetadataResolver()
        result = resolver.resolve(sample_song_id, [])

        assert result.get("name") is None
        assert result.get("artists") is None
        assert result.get_source("name") is None


class TestMetadataResolverGetFieldValue:
    """Tests for MetadataResolver._get_field_value method."""

    def test_get_field_value_direct_match(self) -> None:
        """Test getting field value with direct key match."""
        resolver = MetadataResolver()
        data = {"name": "Test Song", "artists": ["Artist 1"]}

        assert resolver._get_field_value(data, "name") == "Test Song"
        assert resolver._get_field_value(data, "artists") == ["Artist 1"]

    def test_get_field_value_alias_match(self) -> None:
        """Test getting field value using alias."""
        resolver = MetadataResolver()
        data = {"title": "Test Song"}  # "title" is alias for "name"

        assert resolver._get_field_value(data, "name") == "Test Song"

    def test_get_field_value_multiple_aliases(self) -> None:
        """Test field value with multiple possible aliases."""
        resolver = MetadataResolver()
        # Test different aliases for album_name
        data1 = {"album": "Album Name"}
        data2 = {"album_title": "Album Title"}

        assert resolver._get_field_value(data1, "album_name") == "Album Name"
        assert resolver._get_field_value(data2, "album_name") == "Album Title"

    def test_get_field_value_prefers_direct_over_alias(self) -> None:
        """Test direct match is preferred over alias."""
        resolver = MetadataResolver()
        data = {
            "name": "Direct Name",
            "title": "Alias Name",
        }

        # Should prefer "name" over "title" alias
        assert resolver._get_field_value(data, "name") == "Direct Name"

    def test_get_field_value_missing_field(self) -> None:
        """Test getting missing field returns None."""
        resolver = MetadataResolver()
        data = {"name": "Test"}

        assert resolver._get_field_value(data, "nonexistent") is None

    def test_get_field_value_all_aliases(self) -> None:
        """Test various field aliases."""
        resolver = MetadataResolver()

        # Test year alias
        assert resolver._get_field_value({"release_year": 2023}, "year") == 2023

        # Test genres alias
        assert resolver._get_field_value({"genre": "Rock"}, "genres") == "Rock"

        # Test cover_url aliases
        assert resolver._get_field_value({"artwork_url": "url"}, "cover_url") == "url"
        assert resolver._get_field_value({"image_url": "url2"}, "cover_url") == "url2"

        # Test bpm alias
        assert resolver._get_field_value({"tempo": 120}, "bpm") == 120


class TestMetadataResolverSongToSnapshotData:
    """Tests for MetadataResolver._song_to_snapshot_data method."""

    def test_song_to_snapshot_basic_fields(self, mock_song: MagicMock) -> None:
        """Test conversion of basic song fields to snapshot data."""
        resolver = MetadataResolver()
        data = resolver._song_to_snapshot_data(mock_song)

        assert data["name"] == "Song Title"
        assert data["artists"] == ["Primary Artist"]
        assert data["album_name"] == "Album Name"
        assert data["isrc"] == "USRC12345678"
        assert data["genres"] == ["Pop"]
        assert data["explicit"] is False

    def test_song_to_snapshot_audio_features(self, mock_song: MagicMock) -> None:
        """Test conversion of audio features."""
        resolver = MetadataResolver()
        data = resolver._song_to_snapshot_data(mock_song)

        assert data["bpm"] == 128.0
        assert data["key"] == 7
        assert data["time_signature"] == 4
        assert data["energy"] == 0.75
        assert data["danceability"] == 0.65

    def test_song_to_snapshot_metadata_json_fields(
        self, mock_song: MagicMock
    ) -> None:
        """Test fields extracted from metadata_json."""
        resolver = MetadataResolver()
        data = resolver._song_to_snapshot_data(mock_song)

        assert data["year"] == 2023
        assert data["cover_url"] == "https://example.com/cover.jpg"
        assert data["track_number"] == 5
        assert data["disc_number"] == 1

    def test_song_to_snapshot_release_date_conversion(
        self, mock_song: MagicMock
    ) -> None:
        """Test release_date is converted to string."""
        resolver = MetadataResolver()
        data = resolver._song_to_snapshot_data(mock_song)

        assert data["release_date"] == "2023-05-15"

    def test_song_to_snapshot_excludes_none_values(
        self, mock_song: MagicMock
    ) -> None:
        """Test None values are excluded from snapshot data."""
        mock_song.label = None
        mock_song.copyright_text = None
        mock_song.bpm = None

        resolver = MetadataResolver()
        data = resolver._song_to_snapshot_data(mock_song)

        assert "label" not in data
        assert "copyright_text" not in data
        assert "bpm" not in data

    def test_song_to_snapshot_no_release_date(self, mock_song: MagicMock) -> None:
        """Test handling song without release_date."""
        mock_song.release_date = None
        mock_song.metadata_json = {}

        resolver = MetadataResolver()
        data = resolver._song_to_snapshot_data(mock_song)

        assert "year" not in data
        assert "release_date" not in data

    def test_song_to_snapshot_year_from_release_date(
        self, mock_song: MagicMock
    ) -> None:
        """Test year is extracted from release_date if not in metadata_json."""
        mock_song.metadata_json = {}  # No year in metadata_json

        resolver = MetadataResolver()
        data = resolver._song_to_snapshot_data(mock_song)

        assert data["year"] == 2023  # From release_date


class TestMetadataResolverResolveFromSong:
    """Tests for MetadataResolver.resolve_from_song method."""

    def test_resolve_from_song_without_snapshots(
        self, mock_song: MagicMock
    ) -> None:
        """Test resolving from song without additional snapshots."""
        resolver = MetadataResolver()
        result = resolver.resolve_from_song(mock_song)

        assert result.song_id == str(mock_song.id)
        assert result.get("name") == "Song Title"
        assert result.get("artists") == ["Primary Artist"]

    def test_resolve_from_song_with_snapshots(
        self, mock_song: MagicMock, mock_snapshot_musicbrainz: MagicMock
    ) -> None:
        """Test resolving from song with additional snapshots."""
        resolver = MetadataResolver()
        result = resolver.resolve_from_song(mock_song, [mock_snapshot_musicbrainz])

        # Should use song data for fields not in snapshot
        assert result.get("explicit") is False

        # Should use snapshot when available and preferred
        assert result.get("musicbrainz_id") == "mb123456"


class TestGetMetadataResolver:
    """Tests for get_metadata_resolver factory function."""

    def test_returns_instance(self) -> None:
        """Test factory function returns MetadataResolver instance."""
        resolver = get_metadata_resolver()
        assert isinstance(resolver, MetadataResolver)

    def test_with_custom_preferences(self) -> None:
        """Test factory function with custom preferences."""
        prefs = get_default_embed_preferences()
        resolver = get_metadata_resolver(preferences=prefs)
        assert resolver.preferences == prefs

    def test_with_dict_preferences(self) -> None:
        """Test factory function with dict preferences."""
        prefs = {"default_order": ["spotify"]}
        resolver = get_metadata_resolver(preferences=prefs)
        assert resolver.preferences["default_order"] == ["spotify"]


class TestMetadataResolverComplexScenarios:
    """Tests for complex metadata resolution scenarios."""

    def test_three_way_merge(
        self,
        sample_song_id: str,
        mock_snapshot_spotify: MagicMock,
        mock_snapshot_musicbrainz: MagicMock,
        mock_snapshot_discogs: MagicMock,
    ) -> None:
        """Test merging metadata from three different sources."""
        resolver = MetadataResolver()
        result = resolver.resolve(
            sample_song_id,
            [mock_snapshot_spotify, mock_snapshot_musicbrainz, mock_snapshot_discogs],
        )

        # Spotify should win for name (highest priority)
        assert result.get("name") == "Spotify Title"
        assert result.get_source("name") == "spotify"

        # MusicBrainz should provide ISRC (not in others)
        assert result.get("isrc") == "USRC17607839"
        assert result.get_source("isrc") == "musicbrainz"

        # Discogs should provide copyright (not in others)
        assert result.get("copyright_text") == "© 2023 Discogs Records"
        assert result.get_source("copyright_text") == "discogs"

        # Audio features only in Spotify
        assert result.get("bpm") == 120.0
        assert result.get("energy") == 0.8

    def test_genre_preference_resolution(
        self,
        sample_song_id: str,
        mock_snapshot_spotify: MagicMock,
        mock_snapshot_musicbrainz: MagicMock,
        mock_snapshot_discogs: MagicMock,
    ) -> None:
        """Test genre field prefers MusicBrainz by default."""
        # Default order for genres: ["musicbrainz", "discogs", "spotify"]
        resolver = MetadataResolver()
        result = resolver.resolve(
            sample_song_id,
            [mock_snapshot_spotify, mock_snapshot_musicbrainz, mock_snapshot_discogs],
        )

        # Should prefer MusicBrainz genres
        assert result.get("genres") == ["Alternative Rock", "Indie"]
        assert result.get_source("genres") == "musicbrainz"

    def test_label_preference_resolution(
        self,
        sample_song_id: str,
        mock_snapshot_musicbrainz: MagicMock,
        mock_snapshot_discogs: MagicMock,
    ) -> None:
        """Test label field prefers Discogs by default."""
        # Default order for label: ["discogs", "musicbrainz", "spotify"]
        resolver = MetadataResolver()
        result = resolver.resolve(
            sample_song_id,
            [mock_snapshot_musicbrainz, mock_snapshot_discogs],
        )

        # Should prefer Discogs label
        assert result.get("label") == "Discogs Label"
        assert result.get_source("label") == "discogs"

    def test_partial_data_from_multiple_sources(
        self, sample_song_id: str
    ) -> None:
        """Test resolving when each source has partial data."""
        snapshot1 = MagicMock()
        snapshot1.source = "source1"
        snapshot1.snapshot_data = {
            "name": "Title 1",
            "artists": ["Artist 1"],
        }

        snapshot2 = MagicMock()
        snapshot2.source = "source2"
        snapshot2.snapshot_data = {
            "album_name": "Album 2",
            "year": 2023,
        }

        snapshot3 = MagicMock()
        snapshot3.source = "source3"
        snapshot3.snapshot_data = {
            "genres": ["Genre 3"],
            "isrc": "ISRC3",
        }

        resolver = MetadataResolver()
        result = resolver.resolve(sample_song_id, [snapshot1, snapshot2, snapshot3])

        # Each source should provide fields the others don't have
        assert result.get("name") == "Title 1"
        assert result.get("album_name") == "Album 2"
        assert result.get("genres") == ["Genre 3"]
        assert result.get("isrc") == "ISRC3"

    def test_conflicting_years_priority(
        self, sample_song_id: str
    ) -> None:
        """Test year field resolution with conflicting values."""
        snapshot_spotify = MagicMock()
        snapshot_spotify.source = "spotify"
        snapshot_spotify.snapshot_data = {"year": 2023}

        snapshot_mb = MagicMock()
        snapshot_mb.source = "musicbrainz"
        snapshot_mb.snapshot_data = {"year": 2022}

        # Default order for year: ["spotify", "musicbrainz", "discogs"]
        resolver = MetadataResolver()
        result = resolver.resolve(sample_song_id, [snapshot_spotify, snapshot_mb])

        # Should prefer Spotify
        assert result.get("year") == 2023
        assert result.get_source("year") == "spotify"

    def test_all_fields_disabled(
        self, sample_song_id: str, mock_snapshot_spotify: MagicMock
    ) -> None:
        """Test behavior when all fields are disabled."""
        prefs: MetadataEmbedPreferences = {
            "default_order": ["spotify"],
            "fields": {
                "name": {"order": ["spotify"], "enabled": False},
                "artists": {"order": ["spotify"], "enabled": False},
            },
        }

        resolver = MetadataResolver(preferences=prefs)
        result = resolver.resolve(sample_song_id, [mock_snapshot_spotify])

        # Fields should be resolved but marked disabled
        assert result.fields["name"].value == "Spotify Title"
        assert result.fields["name"].enabled is False

        # to_dict should be empty (or only have enabled fields)
        data = result.to_dict()
        assert "name" not in data
        assert "artists" not in data
