"""Unit tests for spotdl_core.download.archive module."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from spotdl_core.download.archive import Archive


# ── Test Data ───────────────────────────────────────────────────────


@pytest.fixture
def sample_urls() -> list[str]:
    """Sample URLs for testing."""
    return [
        "https://open.spotify.com/track/1",
        "https://open.spotify.com/track/2",
        "https://open.spotify.com/track/3",
        "https://www.youtube.com/watch?v=test1",
        "https://www.youtube.com/watch?v=test2",
    ]


@pytest.fixture
def archive_file_content() -> str:
    """Sample archive file content."""
    return """https://open.spotify.com/track/1
https://open.spotify.com/track/2
https://www.youtube.com/watch?v=test1


https://open.spotify.com/track/3
"""


# ── 1. Archive Initialization ───────────────────────────────────────


class TestArchiveInitialization:
    """Test Archive initialization."""

    def test_init_empty(self) -> None:
        """Test initializing an empty archive."""
        archive = Archive()
        assert len(archive) == 0
        assert isinstance(archive, set)

    def test_init_with_urls(self, sample_urls: list[str]) -> None:
        """Test initializing archive with URLs."""
        archive = Archive(sample_urls)
        assert len(archive) == len(sample_urls)
        for url in sample_urls:
            assert url in archive

    def test_archive_is_set(self) -> None:
        """Test that Archive behaves as a set."""
        archive = Archive(["url1", "url2", "url1"])
        assert len(archive) == 2
        assert "url1" in archive
        assert "url2" in archive


# ── 2. Loading Archive Files ────────────────────────────────────────


class TestArchiveLoading:
    """Test loading URLs from archive files."""

    def test_load_from_existing_file(
        self, tmp_path: Path, archive_file_content: str
    ) -> None:
        """Test loading from an existing archive file."""
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text(archive_file_content, encoding="utf-8")

        archive = Archive()
        result = archive.load(archive_file)

        assert result is True
        assert len(archive) == 4  # Empty lines should be skipped
        assert "https://open.spotify.com/track/1" in archive
        assert "https://open.spotify.com/track/2" in archive
        assert "https://open.spotify.com/track/3" in archive
        assert "https://www.youtube.com/watch?v=test1" in archive

    def test_load_from_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading from a nonexistent file."""
        archive_file = tmp_path / "nonexistent.txt"

        archive = Archive()
        result = archive.load(archive_file)

        assert result is False
        assert len(archive) == 0

    def test_load_with_string_path(self, tmp_path: Path) -> None:
        """Test loading with string path instead of Path object."""
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text("https://example.com/track/1\n", encoding="utf-8")

        archive = Archive()
        result = archive.load(str(archive_file))

        assert result is True
        assert len(archive) == 1

    def test_load_with_whitespace_lines(self, tmp_path: Path) -> None:
        """Test loading file with whitespace-only lines."""
        content = """https://example.com/1

\t\t
https://example.com/2
  \t
https://example.com/3
"""
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text(content, encoding="utf-8")

        archive = Archive()
        result = archive.load(archive_file)

        assert result is True
        assert len(archive) == 3

    def test_load_strips_whitespace(self, tmp_path: Path) -> None:
        """Test that URLs are stripped of leading/trailing whitespace."""
        content = """  https://example.com/1
\thttps://example.com/2\t
   https://example.com/3
"""
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text(content, encoding="utf-8")

        archive = Archive()
        result = archive.load(archive_file)

        assert result is True
        assert "https://example.com/1" in archive
        assert "https://example.com/2" in archive
        assert "https://example.com/3" in archive

    def test_load_empty_file(self, tmp_path: Path) -> None:
        """Test loading an empty archive file."""
        archive_file = tmp_path / "empty.txt"
        archive_file.write_text("", encoding="utf-8")

        archive = Archive()
        result = archive.load(archive_file)

        assert result is True
        assert len(archive) == 0

    def test_load_file_with_only_empty_lines(self, tmp_path: Path) -> None:
        """Test loading file with only empty lines."""
        content = "\n\n   \n\t\n\n"
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text(content, encoding="utf-8")

        archive = Archive()
        result = archive.load(archive_file)

        assert result is True
        assert len(archive) == 0

    def test_load_appends_to_existing_urls(self, tmp_path: Path) -> None:
        """Test that loading appends to existing URLs."""
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text("https://example.com/new\n", encoding="utf-8")

        archive = Archive(["https://example.com/existing"])
        result = archive.load(archive_file)

        assert result is True
        assert len(archive) == 2
        assert "https://example.com/existing" in archive
        assert "https://example.com/new" in archive

    def test_load_with_duplicate_urls(self, tmp_path: Path) -> None:
        """Test loading file with duplicate URLs."""
        content = """https://example.com/1
https://example.com/2
https://example.com/1
https://example.com/3
https://example.com/2
"""
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text(content, encoding="utf-8")

        archive = Archive()
        result = archive.load(archive_file)

        assert result is True
        assert len(archive) == 3  # Duplicates removed

    def test_load_with_permission_error(self, tmp_path: Path) -> None:
        """Test loading file with permission error."""
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text("https://example.com/1\n", encoding="utf-8")

        archive = Archive()

        # Mock the file open to raise permission error
        original_open = open
        def mock_open_func(*args, **kwargs):
            if str(archive_file) in str(args[0]):
                raise PermissionError("No permission")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            result = archive.load(archive_file)

        assert result is False
        assert len(archive) == 0

    def test_load_with_os_error(self, tmp_path: Path) -> None:
        """Test loading file with generic OS error."""
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text("test", encoding="utf-8")

        archive = Archive()

        # Mock the file open to raise OS error
        original_open = open
        def mock_open_func(*args, **kwargs):
            if str(archive_file) in str(args[0]):
                raise OSError("Disk error")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            result = archive.load(archive_file)

        assert result is False

    def test_load_logs_debug_on_success(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that successful load logs debug message."""
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text("https://example.com/1\n", encoding="utf-8")

        archive = Archive()

        with caplog.at_level(logging.DEBUG):
            archive.load(archive_file)

        assert any("Loaded" in record.message for record in caplog.records)

    def test_load_logs_warning_on_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that failed load logs warning message."""
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text("test", encoding="utf-8")

        archive = Archive()

        # Mock the file open to raise OS error
        original_open = open
        def mock_open_func(*args, **kwargs):
            if str(archive_file) in str(args[0]):
                raise OSError("Error")
            return original_open(*args, **kwargs)

        with caplog.at_level(logging.WARNING):
            with patch("builtins.open", side_effect=mock_open_func):
                archive.load(archive_file)

        assert any("Failed to load archive" in record.message for record in caplog.records)


# ── 3. Saving Archive Files ─────────────────────────────────────────


class TestArchiveSaving:
    """Test saving URLs to archive files."""

    def test_save_to_new_file(self, tmp_path: Path, sample_urls: list[str]) -> None:
        """Test saving to a new archive file."""
        archive_file = tmp_path / "archive.txt"
        archive = Archive(sample_urls)

        result = archive.save(archive_file)

        assert result is True
        assert archive_file.exists()

        # Verify content is sorted
        content = archive_file.read_text(encoding="utf-8")
        lines = [line for line in content.split("\n") if line]
        assert len(lines) == len(sample_urls)
        assert lines == sorted(sample_urls)

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that save creates parent directories."""
        nested_dir = tmp_path / "music" / "archives"
        archive_file = nested_dir / "archive.txt"

        archive = Archive(["https://example.com/1"])
        result = archive.save(archive_file)

        assert result is True
        assert nested_dir.exists()
        assert archive_file.exists()

    def test_save_with_string_path(self, tmp_path: Path) -> None:
        """Test saving with string path instead of Path object."""
        archive_file = tmp_path / "archive.txt"
        archive = Archive(["https://example.com/1"])

        result = archive.save(str(archive_file))

        assert result is True
        assert archive_file.exists()

    def test_save_empty_archive(self, tmp_path: Path) -> None:
        """Test saving an empty archive."""
        archive_file = tmp_path / "archive.txt"
        archive = Archive()

        result = archive.save(archive_file)

        assert result is True
        assert archive_file.exists()
        assert archive_file.read_text(encoding="utf-8") == ""

    def test_save_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Test that save overwrites existing file."""
        archive_file = tmp_path / "archive.txt"
        archive_file.write_text("old content\n", encoding="utf-8")

        archive = Archive(["https://example.com/1", "https://example.com/2"])
        result = archive.save(archive_file)

        assert result is True
        content = archive_file.read_text(encoding="utf-8")
        assert "old content" not in content
        assert "https://example.com/1" in content

    def test_save_urls_are_sorted(self, tmp_path: Path) -> None:
        """Test that saved URLs are sorted alphabetically."""
        archive_file = tmp_path / "archive.txt"
        urls = [
            "https://example.com/z",
            "https://example.com/a",
            "https://example.com/m",
            "https://example.com/b",
        ]
        archive = Archive(urls)

        archive.save(archive_file)

        content = archive_file.read_text(encoding="utf-8")
        lines = content.split("\n")
        # Filter out empty lines
        lines = [line for line in lines if line]
        assert lines == sorted(urls)

    def test_save_with_permission_error(self, tmp_path: Path) -> None:
        """Test saving with permission error."""
        archive_file = tmp_path / "archive.txt"
        archive = Archive(["https://example.com/1"])

        with patch("builtins.open", side_effect=PermissionError("No permission")):
            result = archive.save(archive_file)

        assert result is False

    def test_save_with_os_error(self, tmp_path: Path) -> None:
        """Test saving with generic OS error."""
        archive_file = tmp_path / "archive.txt"
        archive = Archive(["https://example.com/1"])

        with patch("builtins.open", side_effect=OSError("Disk error")):
            result = archive.save(archive_file)

        assert result is False

    def test_save_logs_debug_on_success(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that successful save logs debug message."""
        archive_file = tmp_path / "archive.txt"
        archive = Archive(["https://example.com/1"])

        with caplog.at_level(logging.DEBUG):
            archive.save(archive_file)

        assert any("Saved" in record.message for record in caplog.records)

    def test_save_logs_warning_on_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that failed save logs warning message."""
        archive_file = tmp_path / "archive.txt"
        archive = Archive(["https://example.com/1"])

        with caplog.at_level(logging.WARNING):
            with patch("builtins.open", side_effect=OSError("Error")):
                archive.save(archive_file)

        assert any("Failed to save archive" in record.message for record in caplog.records)

    def test_save_with_unicode_urls(self, tmp_path: Path) -> None:
        """Test saving with Unicode characters in URLs."""
        archive_file = tmp_path / "archive.txt"
        urls = [
            "https://example.com/song/café",
            "https://example.com/artist/björk",
            "https://example.com/album/日本語",
        ]
        archive = Archive(urls)

        result = archive.save(archive_file)

        assert result is True
        content = archive_file.read_text(encoding="utf-8")
        for url in urls:
            assert url in content


# ── 4. Set Operations ────────────────────────────────────────────────


class TestArchiveSetOperations:
    """Test Archive set operations."""

    def test_add_url(self) -> None:
        """Test adding a URL to the archive."""
        archive = Archive()
        archive.add("https://example.com/1")

        assert len(archive) == 1
        assert "https://example.com/1" in archive

    def test_add_duplicate_url(self) -> None:
        """Test adding a duplicate URL."""
        archive = Archive(["https://example.com/1"])
        archive.add("https://example.com/1")

        assert len(archive) == 1

    def test_remove_url(self) -> None:
        """Test removing a URL from the archive."""
        archive = Archive(["https://example.com/1", "https://example.com/2"])
        archive.remove("https://example.com/1")

        assert len(archive) == 1
        assert "https://example.com/1" not in archive

    def test_discard_url(self) -> None:
        """Test discarding a URL from the archive."""
        archive = Archive(["https://example.com/1"])
        archive.discard("https://example.com/1")
        archive.discard("https://example.com/nonexistent")

        assert len(archive) == 0

    def test_clear_archive(self) -> None:
        """Test clearing all URLs from archive."""
        archive = Archive(["url1", "url2", "url3"])
        archive.clear()

        assert len(archive) == 0

    def test_update_with_urls(self) -> None:
        """Test updating archive with multiple URLs."""
        archive = Archive(["https://example.com/1"])
        archive.update(["https://example.com/2", "https://example.com/3"])

        assert len(archive) == 3

    def test_union_operation(self) -> None:
        """Test union operation with another set."""
        archive1 = Archive(["url1", "url2"])
        archive2 = Archive(["url2", "url3"])

        result = archive1 | archive2

        assert len(result) == 3
        assert "url1" in result
        assert "url2" in result
        assert "url3" in result

    def test_intersection_operation(self) -> None:
        """Test intersection operation with another set."""
        archive1 = Archive(["url1", "url2", "url3"])
        archive2 = Archive(["url2", "url3", "url4"])

        result = archive1 & archive2

        assert len(result) == 2
        assert "url2" in result
        assert "url3" in result

    def test_difference_operation(self) -> None:
        """Test difference operation with another set."""
        archive1 = Archive(["url1", "url2", "url3"])
        archive2 = Archive(["url2", "url3"])

        result = archive1 - archive2

        assert len(result) == 1
        assert "url1" in result

    def test_contains_check(self) -> None:
        """Test checking if URL is in archive."""
        archive = Archive(["https://example.com/1"])

        assert "https://example.com/1" in archive
        assert "https://example.com/2" not in archive

    def test_iteration(self) -> None:
        """Test iterating over archive URLs."""
        urls = ["url1", "url2", "url3"]
        archive = Archive(urls)

        result = list(archive)

        assert len(result) == 3
        for url in urls:
            assert url in result


# ── 5. Round-trip Testing ───────────────────────────────────────────


class TestArchiveRoundTrip:
    """Test loading and saving in combination."""

    def test_load_and_save_preserves_urls(
        self, tmp_path: Path, sample_urls: list[str]
    ) -> None:
        """Test that loading and saving preserves URLs."""
        archive_file = tmp_path / "archive.txt"

        # Save initial archive
        archive1 = Archive(sample_urls)
        archive1.save(archive_file)

        # Load into new archive
        archive2 = Archive()
        archive2.load(archive_file)

        # Compare
        assert archive1 == archive2

    def test_multiple_load_save_cycles(self, tmp_path: Path) -> None:
        """Test multiple load/save cycles."""
        archive_file = tmp_path / "archive.txt"

        # Initial save
        archive = Archive(["url1", "url2"])
        archive.save(archive_file)

        # Load, add, save
        archive.load(archive_file)
        archive.add("url3")
        archive.save(archive_file)

        # Load again
        archive2 = Archive()
        archive2.load(archive_file)

        assert len(archive2) == 3
        assert "url1" in archive2
        assert "url2" in archive2
        assert "url3" in archive2

    def test_load_modify_save(self, tmp_path: Path) -> None:
        """Test loading, modifying, and saving archive."""
        archive_file = tmp_path / "archive.txt"

        # Create initial archive
        archive = Archive(["url1", "url2", "url3"])
        archive.save(archive_file)

        # Load, modify, save
        archive2 = Archive()
        archive2.load(archive_file)
        archive2.remove("url2")
        archive2.add("url4")
        archive2.save(archive_file)

        # Load and verify
        archive3 = Archive()
        archive3.load(archive_file)

        assert len(archive3) == 3
        assert "url1" in archive3
        assert "url2" not in archive3
        assert "url3" in archive3
        assert "url4" in archive3
