"""Tests for Result type."""

import pytest

from spotdl.core.types.result import Result, TargetPlatform


class TestTargetPlatform:
    """Tests for TargetPlatform enum."""

    def test_target_platform_enum_values(self) -> None:
        """Test TargetPlatform has expected values."""
        assert hasattr(TargetPlatform, "YOUTUBE")
        assert hasattr(TargetPlatform, "YOUTUBE_MUSIC")
        assert hasattr(TargetPlatform, "SOUNDCLOUD")
        assert hasattr(TargetPlatform, "BANDCAMP")
        assert hasattr(TargetPlatform, "PIPED")

    def test_target_platform_values_are_strings(self) -> None:
        """Test TargetPlatform enum values are strings."""
        assert TargetPlatform.YOUTUBE.value == "youtube"
        assert TargetPlatform.YOUTUBE_MUSIC.value == "youtube_music"
        assert TargetPlatform.SOUNDCLOUD.value == "soundcloud"
        assert TargetPlatform.BANDCAMP.value == "bandcamp"
        assert TargetPlatform.PIPED.value == "piped"

    def test_target_platform_from_string(self) -> None:
        """Test creating TargetPlatform from string."""
        assert TargetPlatform("youtube") == TargetPlatform.YOUTUBE
        assert TargetPlatform("youtube_music") == TargetPlatform.YOUTUBE_MUSIC


class TestResult:
    """Tests for Result dataclass."""

    def test_result_creation_minimal(self) -> None:
        """Test creating Result with minimal required fields."""
        result = Result(
            name="Test Song",
            artists=["Artist 1"],
            artist="Artist 1",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="test123",
            url="https://www.youtube.com/watch?v=test123",
        )

        assert result.name == "Test Song"
        assert result.artists == ("Artist 1",)  # Converted to tuple
        assert result.artist == "Artist 1"
        assert result.duration == 180
        assert result.platform == TargetPlatform.YOUTUBE
        assert result.platform_id == "test123"
        assert result.url == "https://www.youtube.com/watch?v=test123"

    def test_result_creation_with_optional_fields(self) -> None:
        """Test creating Result with optional fields."""
        result = Result(
            name="Test Song",
            artists=["Artist 1", "Artist 2"],
            artist="Artist 1",
            duration=180,
            platform=TargetPlatform.YOUTUBE_MUSIC,
            platform_id="test456",
            url="https://music.youtube.com/watch?v=test456",
            album_name="Test Album",
            cover_url="https://example.com/cover.jpg",
            verified=True,
            views=1000000,
            explicit=False,
        )

        assert result.album_name == "Test Album"
        assert result.cover_url == "https://example.com/cover.jpg"
        assert result.verified is True
        assert result.views == 1000000
        assert result.explicit is False

    def test_result_with_multiple_artists(self) -> None:
        """Test Result with multiple artists."""
        result = Result(
            name="Collaboration",
            artists=["Artist 1", "Artist 2", "Artist 3"],
            artist="Artist 1",
            duration=200,
            platform=TargetPlatform.SOUNDCLOUD,
            platform_id="collab123",
            url="https://soundcloud.com/artist/collab123",
        )

        assert isinstance(result.artists, tuple)
        assert len(result.artists) == 3
        assert "Artist 1" in result.artists
        assert "Artist 2" in result.artists
        assert "Artist 3" in result.artists

    def test_result_different_platforms(self) -> None:
        """Test Result can be created for different platforms."""
        platforms = [
            TargetPlatform.YOUTUBE,
            TargetPlatform.YOUTUBE_MUSIC,
            TargetPlatform.SOUNDCLOUD,
            TargetPlatform.BANDCAMP,
            TargetPlatform.PIPED,
        ]

        for platform in platforms:
            result = Result(
                name="Test",
                artists=["Artist"],
                artist="Artist",
                duration=180,
                platform=platform,
                platform_id="test",
                url="https://example.com/test",
            )
            assert result.platform == platform

    def test_result_artists_converted_to_tuple(self) -> None:
        """Test Result converts artists list to tuple."""
        result = Result(
            name="Test Song",
            artists=["Artist 1", "Artist 2"],
            artist="Artist 1",
            duration=180,
            platform=TargetPlatform.YOUTUBE_MUSIC,
            platform_id="test",
            url="https://music.youtube.com/watch?v=test",
        )

        assert isinstance(result.artists, tuple)
        assert result.artists == ("Artist 1", "Artist 2")

    def test_result_isrc_search_flag(self) -> None:
        """Test Result with isrc_search flag."""
        result = Result(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE_MUSIC,
            platform_id="test",
            url="https://music.youtube.com/watch?v=test",
            isrc_search=True,
        )

        assert result.isrc_search is True

    def test_result_equality(self) -> None:
        """Test Result equality comparison."""
        result1 = Result(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="test123",
            url="https://www.youtube.com/watch?v=test123",
        )

        result2 = Result(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="test123",
            url="https://www.youtube.com/watch?v=test123",
        )

        assert result1 == result2

    def test_result_with_year(self) -> None:
        """Test Result with year field."""
        result = Result(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="test",
            url="https://www.youtube.com/watch?v=test",
            year=2024,
        )

        assert result.year == 2024
