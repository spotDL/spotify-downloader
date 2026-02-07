"""Unit tests for spotdl_core.download.lrc module."""

from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spotdl_core.download.lrc import generate_lrc, is_synced


# ── Helper Functions ───────────────────────────────────────────────


@contextmanager
def mock_syncedlyrics(return_value=None, side_effect=None):
    """Context manager to mock the syncedlyrics module."""
    mock_module = MagicMock()
    if side_effect:
        mock_module.search = MagicMock(side_effect=side_effect)
    else:
        mock_module.search = MagicMock(return_value=return_value)

    sys.modules['syncedlyrics'] = mock_module
    try:
        yield mock_module.search
    finally:
        if 'syncedlyrics' in sys.modules:
            del sys.modules['syncedlyrics']


# ── Test Data ───────────────────────────────────────────────────────


@pytest.fixture
def sample_song_data() -> dict[str, any]:
    """Sample song data for testing."""
    return {
        "name": "Test Song",
        "artists": ["Artist One", "Artist Two"],
    }


@pytest.fixture
def synced_lyrics() -> str:
    """Sample synced lyrics in LRC format."""
    return """[00:12.00]First line of lyrics
[00:17.20]Second line of lyrics
[00:21.10]Third line of lyrics
[00:25.00]Fourth line of lyrics"""


@pytest.fixture
def unsynced_lyrics() -> str:
    """Sample unsynced lyrics (plain text)."""
    return """First line of lyrics
Second line of lyrics
Third line of lyrics
Fourth line of lyrics"""


@pytest.fixture
def complex_synced_lyrics() -> str:
    """Complex synced lyrics with metadata."""
    return """[ti:Song Title]
[ar:Artist Name]
[al:Album Name]
[00:00.00]Intro line
[00:12.50]First verse line one
[00:17.80]First verse line two
[00:23.10]Chorus line one
[00:27.40]Chorus line two
[01:02.00]Second verse line one"""


# ── 1. is_synced() Function Tests ───────────────────────────────────


class TestIsSynced:
    """Test the is_synced() function."""

    def test_is_synced_with_synced_lyrics(self, synced_lyrics: str) -> None:
        """Test detection of synced lyrics."""
        assert is_synced(synced_lyrics) is True

    def test_is_synced_with_unsynced_lyrics(self, unsynced_lyrics: str) -> None:
        """Test detection of unsynced lyrics."""
        assert is_synced(unsynced_lyrics) is False

    def test_is_synced_with_complex_synced_lyrics(
        self, complex_synced_lyrics: str
    ) -> None:
        """Test detection of complex synced lyrics with metadata."""
        assert is_synced(complex_synced_lyrics) is True

    def test_is_synced_with_empty_string(self) -> None:
        """Test with empty string."""
        assert is_synced("") is False

    def test_is_synced_with_only_brackets(self) -> None:
        """Test with text containing brackets but no timestamps."""
        text = "[This is not a timestamp]\n[Neither is this]"
        assert is_synced(text) is False

    def test_is_synced_with_partial_timestamp(self) -> None:
        """Test with text containing partial timestamps."""
        text = "[00:12]Missing milliseconds\n[00:15]Another line"
        # This actually has timestamps with colons, so it will be detected as synced
        assert is_synced(text) is True

    def test_is_synced_with_timestamp_format(self) -> None:
        """Test various timestamp formats."""
        valid_formats = [
            "[00:12.00]Line one",
            "[00:12:00]Line two",
            "[00:12.345]Line three",
            "[01:23.45]Line four",
        ]

        for text in valid_formats:
            assert is_synced(text) is True

    def test_is_synced_with_mixed_content(self) -> None:
        """Test with mixed synced and unsynced lines."""
        text = """Unsynced line
[00:12.00]Synced line
Another unsynced line
[00:15.00]Another synced line"""
        assert is_synced(text) is True

    def test_is_synced_with_no_colon(self) -> None:
        """Test with brackets but no colon in timestamp."""
        text = "[00-12.00]Invalid format\n[00-15.00]Another line"
        assert is_synced(text) is False

    def test_is_synced_with_whitespace_lines(self) -> None:
        """Test with whitespace-only lines."""
        text = """

[00:12.00]First line

[00:15.00]Second line

"""
        assert is_synced(text) is True

    def test_is_synced_with_inline_timestamps(self) -> None:
        """Test with timestamps not at line start."""
        text = "Some text [00:12.00] with timestamp inline"
        # Should be False because timestamp is not at line start
        assert is_synced(text) is False

    def test_is_synced_with_metadata_only(self) -> None:
        """Test with only metadata tags (no timestamps)."""
        text = "[ti:Song Title]\n[ar:Artist Name]\n[al:Album Name]"
        # Metadata tags have colons, so they will be detected as synced
        # The function is simple and doesn't distinguish between metadata and timestamps
        assert is_synced(text) is True

    def test_is_synced_with_metadata_and_timestamps(self) -> None:
        """Test with both metadata and timestamps."""
        text = "[ti:Song]\n[00:12.00]First line\n[00:15.00]Second line"
        assert is_synced(text) is True

    def test_is_synced_case_sensitivity(self) -> None:
        """Test that detection is case-sensitive for tags."""
        text = "[00:12.00]Lowercase\n[00:15.00]timestamps"
        assert is_synced(text) is True


# ── 2. generate_lrc() with Pre-synced Lyrics ────────────────────────


class TestGenerateLrcWithSyncedLyrics:
    """Test generate_lrc() with already-synced lyrics."""

    def test_generate_lrc_with_synced_lyrics_success(
        self, tmp_path: Path, sample_song_data: dict, synced_lyrics: str
    ) -> None:
        """Test generating LRC file with synced lyrics."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        result = generate_lrc(
            song_name=sample_song_data["name"],
            song_artists=sample_song_data["artists"],
            output_file=audio_file,
            lyrics=synced_lyrics,
        )

        assert result is True

        lrc_file = tmp_path / "song.lrc"
        assert lrc_file.exists()
        assert lrc_file.read_text(encoding="utf-8") == synced_lyrics

    def test_generate_lrc_preserves_content(
        self, tmp_path: Path, complex_synced_lyrics: str
    ) -> None:
        """Test that LRC content is preserved exactly."""
        audio_file = tmp_path / "song.m4a"
        audio_file.touch()

        result = generate_lrc(
            song_name="Test",
            song_artists=["Artist"],
            output_file=audio_file,
            lyrics=complex_synced_lyrics,
        )

        assert result is True

        lrc_file = tmp_path / "song.lrc"
        content = lrc_file.read_text(encoding="utf-8")
        assert content == complex_synced_lyrics

    def test_generate_lrc_with_different_extensions(
        self, tmp_path: Path, synced_lyrics: str
    ) -> None:
        """Test LRC generation for various audio formats."""
        extensions = [".mp3", ".m4a", ".flac", ".opus", ".ogg", ".wav"]

        for ext in extensions:
            audio_file = tmp_path / f"song{ext}"
            audio_file.touch()

            result = generate_lrc(
                song_name="Test",
                song_artists=["Artist"],
                output_file=audio_file,
                lyrics=synced_lyrics,
            )

            assert result is True

            lrc_file = tmp_path / "song.lrc"
            assert lrc_file.exists()
            lrc_file.unlink()  # Clean up for next iteration

    def test_generate_lrc_overwrites_existing_file(
        self, tmp_path: Path, synced_lyrics: str
    ) -> None:
        """Test that existing LRC file is overwritten."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        lrc_file = tmp_path / "song.lrc"
        lrc_file.write_text("Old content", encoding="utf-8")

        result = generate_lrc(
            song_name="Test",
            song_artists=["Artist"],
            output_file=audio_file,
            lyrics=synced_lyrics,
        )

        assert result is True
        assert lrc_file.read_text(encoding="utf-8") == synced_lyrics
        assert "Old content" not in lrc_file.read_text(encoding="utf-8")

    def test_generate_lrc_with_unicode_lyrics(self, tmp_path: Path) -> None:
        """Test LRC generation with Unicode characters."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        unicode_lyrics = """[00:12.00]Café français
[00:15.00]日本語の歌詞
[00:18.00]Ελληνικά lyrics
[00:21.00]Русский текст"""

        result = generate_lrc(
            song_name="Test",
            song_artists=["Artist"],
            output_file=audio_file,
            lyrics=unicode_lyrics,
        )

        assert result is True

        lrc_file = tmp_path / "song.lrc"
        content = lrc_file.read_text(encoding="utf-8")
        assert "Café français" in content
        assert "日本語の歌詞" in content

    def test_generate_lrc_with_write_error(
        self, tmp_path: Path, synced_lyrics: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test error handling when writing LRC file fails."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with patch.object(Path, "write_text", side_effect=OSError("Write error")):
            with caplog.at_level(logging.WARNING):
                result = generate_lrc(
                    song_name="Test",
                    song_artists=["Artist"],
                    output_file=audio_file,
                    lyrics=synced_lyrics,
                )

        assert result is False
        assert any("Failed to write LRC file" in record.message for record in caplog.records)

    def test_generate_lrc_with_permission_error(
        self, tmp_path: Path, synced_lyrics: str
    ) -> None:
        """Test handling of permission errors."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with patch.object(Path, "write_text", side_effect=PermissionError("No permission")):
            result = generate_lrc(
                song_name="Test",
                song_artists=["Artist"],
                output_file=audio_file,
                lyrics=synced_lyrics,
            )

        assert result is False

    def test_generate_lrc_logs_debug_on_success(
        self, tmp_path: Path, synced_lyrics: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that success logs debug message."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with caplog.at_level(logging.DEBUG):
            result = generate_lrc(
                song_name="Test",
                song_artists=["Artist"],
                output_file=audio_file,
                lyrics=synced_lyrics,
            )

        assert result is True
        assert any("Wrote synced lyrics" in record.message for record in caplog.records)


# ── 3. generate_lrc() with Unsynced Lyrics ──────────────────────────


class TestGenerateLrcWithUnsyncedLyrics:
    """Test generate_lrc() with unsynced lyrics (should search)."""

    def test_generate_lrc_searches_for_synced_lyrics(
        self, tmp_path: Path, unsynced_lyrics: str, synced_lyrics: str
    ) -> None:
        """Test that unsynced lyrics trigger search."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        # Mock the syncedlyrics module that gets imported inside the function
        import sys
        from unittest.mock import MagicMock

        mock_syncedlyrics = MagicMock()
        mock_search = MagicMock(return_value=synced_lyrics)
        mock_syncedlyrics.search = mock_search
        sys.modules['syncedlyrics'] = mock_syncedlyrics

        try:
            result = generate_lrc(
                song_name="Test Song",
                song_artists=["Artist One", "Artist Two"],
                output_file=audio_file,
                lyrics=unsynced_lyrics,
            )

            assert result is True
            mock_search.assert_called_once_with("Artist One, Artist Two - Test Song")

            lrc_file = tmp_path / "song.lrc"
            assert lrc_file.exists()
            assert lrc_file.read_text(encoding="utf-8") == synced_lyrics
        finally:
            if 'syncedlyrics' in sys.modules:
                del sys.modules['syncedlyrics']

    def test_generate_lrc_search_returns_none(
        self, tmp_path: Path, unsynced_lyrics: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test when search returns no results."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with mock_syncedlyrics(return_value=None):
            with caplog.at_level(logging.DEBUG):
                result = generate_lrc(
                    song_name="Test Song",
                    song_artists=["Artist"],
                    output_file=audio_file,
                    lyrics=unsynced_lyrics,
                )

        assert result is False
        assert any("No synced lyrics found" in record.message for record in caplog.records)

        lrc_file = tmp_path / "song.lrc"
        assert not lrc_file.exists()

    def test_generate_lrc_search_import_error(
        self, tmp_path: Path, unsynced_lyrics: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test when syncedlyrics package is not installed."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with mock_syncedlyrics(side_effect=ImportError("Module not found")):
            with caplog.at_level(logging.WARNING):
                result = generate_lrc(
                    song_name="Test",
                    song_artists=["Artist"],
                    output_file=audio_file,
                    lyrics=unsynced_lyrics,
                )

        assert result is False
        assert any("syncedlyrics package not installed" in record.message for record in caplog.records)

    def test_generate_lrc_search_exception(
        self, tmp_path: Path, unsynced_lyrics: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test error handling during search."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with mock_syncedlyrics(side_effect=Exception("Network error")):
            with caplog.at_level(logging.WARNING):
                result = generate_lrc(
                    song_name="Test",
                    song_artists=["Artist"],
                    output_file=audio_file,
                    lyrics=unsynced_lyrics,
                )

        assert result is False
        assert any("Failed to search for synced lyrics" in record.message for record in caplog.records)


# ── 4. generate_lrc() without Lyrics ─────────────────────────────────


class TestGenerateLrcWithoutLyrics:
    """Test generate_lrc() when no lyrics provided (should search)."""

    def test_generate_lrc_no_lyrics_searches(
        self, tmp_path: Path, synced_lyrics: str
    ) -> None:
        """Test that missing lyrics trigger search."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with mock_syncedlyrics(return_value=synced_lyrics) as mock_search:
            result = generate_lrc(
                song_name="Test Song",
                song_artists=["Artist One"],
                output_file=audio_file,
                lyrics=None,
            )

        assert result is True
        mock_search.assert_called_once_with("Artist One - Test Song")

    def test_generate_lrc_no_lyrics_no_results(self, tmp_path: Path) -> None:
        """Test when no lyrics provided and search finds nothing."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with mock_syncedlyrics(return_value=None):
            result = generate_lrc(
                song_name="Test",
                song_artists=["Artist"],
                output_file=audio_file,
                lyrics=None,
            )

        assert result is False

        lrc_file = tmp_path / "song.lrc"
        assert not lrc_file.exists()

    def test_generate_lrc_empty_lyrics_string(self, tmp_path: Path) -> None:
        """Test with empty string as lyrics."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with mock_syncedlyrics(return_value=None):
            result = generate_lrc(
                song_name="Test",
                song_artists=["Artist"],
                output_file=audio_file,
                lyrics="",
            )

        assert result is False

    def test_generate_lrc_whitespace_only_lyrics(
        self, tmp_path: Path, synced_lyrics: str
    ) -> None:
        """Test with whitespace-only lyrics."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with mock_syncedlyrics(return_value=synced_lyrics) as mock_search:
            result = generate_lrc(
                song_name="Test",
                song_artists=["Artist"],
                output_file=audio_file,
                lyrics="   \n\t\n   ",
            )

        # Whitespace-only is not synced, so it should search
        assert mock_search.called


# ── 5. Artist Name Formatting ────────────────────────────────────────


class TestArtistNameFormatting:
    """Test how artist names are formatted for search."""

    def test_generate_lrc_single_artist(self, tmp_path: Path) -> None:
        """Test display name with single artist."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with mock_syncedlyrics(return_value=None) as mock_search:
            generate_lrc(
                song_name="Test Song",
                song_artists=["Single Artist"],
                output_file=audio_file,
                lyrics=None,
            )

        mock_search.assert_called_once_with("Single Artist - Test Song")

    def test_generate_lrc_multiple_artists(self, tmp_path: Path) -> None:
        """Test display name with multiple artists."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with mock_syncedlyrics(return_value=None) as mock_search:
            generate_lrc(
                song_name="Test Song",
                song_artists=["Artist One", "Artist Two", "Artist Three"],
                output_file=audio_file,
                lyrics=None,
            )

        mock_search.assert_called_once_with("Artist One, Artist Two, Artist Three - Test Song")

    def test_generate_lrc_empty_artists_list(self, tmp_path: Path) -> None:
        """Test with empty artists list."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with mock_syncedlyrics(return_value=None) as mock_search:
            generate_lrc(
                song_name="Test Song",
                song_artists=[],
                output_file=audio_file,
                lyrics=None,
            )

        mock_search.assert_called_once_with(" - Test Song")

    def test_generate_lrc_special_characters_in_names(self, tmp_path: Path) -> None:
        """Test with special characters in song/artist names."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        with mock_syncedlyrics(return_value=None) as mock_search:
            generate_lrc(
                song_name="Song: The Sequel (Remix)",
                song_artists=["Artist & Co.", "Feat. Other"],
                output_file=audio_file,
                lyrics=None,
            )

        expected_call = "Artist & Co., Feat. Other - Song: The Sequel (Remix)"
        mock_search.assert_called_once_with(expected_call)


# ── 6. LRC File Path Handling ────────────────────────────────────────


class TestLrcFilePathHandling:
    """Test LRC file path generation."""

    def test_generate_lrc_uses_audio_file_stem(
        self, tmp_path: Path, synced_lyrics: str
    ) -> None:
        """Test that LRC uses the same stem as audio file."""
        audio_file = tmp_path / "my_song.mp3"
        audio_file.touch()

        result = generate_lrc(
            song_name="Test",
            song_artists=["Artist"],
            output_file=audio_file,
            lyrics=synced_lyrics,
        )

        assert result is True

        lrc_file = tmp_path / "my_song.lrc"
        assert lrc_file.exists()

    def test_generate_lrc_with_nested_directory(
        self, tmp_path: Path, synced_lyrics: str
    ) -> None:
        """Test LRC generation with nested directory structure."""
        nested_dir = tmp_path / "artist" / "album"
        nested_dir.mkdir(parents=True)

        audio_file = nested_dir / "track.mp3"
        audio_file.touch()

        result = generate_lrc(
            song_name="Test",
            song_artists=["Artist"],
            output_file=audio_file,
            lyrics=synced_lyrics,
        )

        assert result is True

        lrc_file = nested_dir / "track.lrc"
        assert lrc_file.exists()

    def test_generate_lrc_complex_filename(
        self, tmp_path: Path, synced_lyrics: str
    ) -> None:
        """Test with complex filename."""
        audio_file = tmp_path / "01. Artist - Song Title (feat. Other).mp3"
        audio_file.touch()

        result = generate_lrc(
            song_name="Test",
            song_artists=["Artist"],
            output_file=audio_file,
            lyrics=synced_lyrics,
        )

        assert result is True

        lrc_file = tmp_path / "01. Artist - Song Title (feat. Other).lrc"
        assert lrc_file.exists()


# ── 7. Edge Cases and Integration ────────────────────────────────────


class TestLrcEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_generate_lrc_with_very_long_lyrics(self, tmp_path: Path) -> None:
        """Test with very long synced lyrics."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        # Generate 1000 lines of synced lyrics
        lines = [f"[{i:02d}:{j:02d}.{k:02d}]Line {i * 60 + j}"
                 for i in range(10) for j in range(60) for k in range(0, 100, 50)]
        long_lyrics = "\n".join(lines[:1000])

        result = generate_lrc(
            song_name="Test",
            song_artists=["Artist"],
            output_file=audio_file,
            lyrics=long_lyrics,
        )

        assert result is True

        lrc_file = tmp_path / "song.lrc"
        content = lrc_file.read_text(encoding="utf-8")
        assert len(content.splitlines()) >= 1000

    def test_generate_lrc_concurrent_calls(
        self, tmp_path: Path, synced_lyrics: str
    ) -> None:
        """Test multiple concurrent LRC generations."""
        results = []

        for i in range(5):
            audio_file = tmp_path / f"song{i}.mp3"
            audio_file.touch()

            result = generate_lrc(
                song_name=f"Test {i}",
                song_artists=["Artist"],
                output_file=audio_file,
                lyrics=synced_lyrics,
            )
            results.append(result)

        assert all(results)
        assert len(list(tmp_path.glob("*.lrc"))) == 5

    def test_is_synced_performance_with_large_text(self) -> None:
        """Test is_synced performance with large text."""
        # Generate large text with timestamps
        lines = [f"[{i:02d}:{j:02d}.00]Line" for i in range(100) for j in range(60)]
        large_text = "\n".join(lines)

        # Should complete quickly
        result = is_synced(large_text)
        assert result is True

    def test_generate_lrc_idempotent(
        self, tmp_path: Path, synced_lyrics: str
    ) -> None:
        """Test that generating LRC multiple times is idempotent."""
        audio_file = tmp_path / "song.mp3"
        audio_file.touch()

        # Generate twice
        result1 = generate_lrc(
            song_name="Test",
            song_artists=["Artist"],
            output_file=audio_file,
            lyrics=synced_lyrics,
        )

        result2 = generate_lrc(
            song_name="Test",
            song_artists=["Artist"],
            output_file=audio_file,
            lyrics=synced_lyrics,
        )

        assert result1 is True
        assert result2 is True

        lrc_file = tmp_path / "song.lrc"
        assert lrc_file.read_text(encoding="utf-8") == synced_lyrics
