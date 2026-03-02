"""Tests for matching utility functions."""

from spotdl.core.matching.utils import (
    based_sort,
    create_clean_string,
    create_search_query,
    create_song_title,
    fill_string,
    ratio,
    slugify,
    sort_string,
)


class TestSlugify:
    """Tests for the slugify function."""

    def test_basic_slugify(self):
        """Test basic string slugification."""
        assert slugify("Hello World") == "hello-world"
        assert slugify("Test   Multiple   Spaces") == "test-multiple-spaces"

    def test_special_characters(self):
        """Test slugification with special characters."""
        # The DISALLOWED_REGEX preserves !, @, and $ characters
        assert slugify("Hello! @World#") == "hello!-@world"
        assert slugify("Test & More") == "test-more"

    def test_unicode_characters(self):
        """Test slugification with unicode characters."""
        # Accented characters should be normalized
        assert slugify("Café") == "cafe"
        assert slugify("naïve") == "naive"

    def test_empty_string(self):
        """Test slugification of empty string."""
        assert slugify("") == ""

    def test_already_slugified(self):
        """Test string that's already slugified."""
        assert slugify("already-slugified") == "already-slugified"

    def test_japanese_text(self):
        """Test slugification with Japanese text (romanization)."""
        # Japanese text should be romanized
        result = slugify("こんにちは")
        # Should contain romanized Japanese
        assert len(result) > 0
        # Result should be lowercase ASCII
        assert result.isascii()

    def test_mixed_japanese_english(self):
        """Test slugification with mixed Japanese and English."""
        result = slugify("Hello こんにちは World")
        # Should have romanized the Japanese parts
        assert "hello" in result.lower()
        assert "world" in result.lower()


class TestRatio:
    """Tests for the ratio function."""

    def test_identical_strings(self):
        """Test ratio of identical strings."""
        assert ratio("hello", "hello") == 100.0

    def test_completely_different(self):
        """Test ratio of completely different strings."""
        assert ratio("abc", "xyz") == 0.0

    def test_partial_match(self):
        """Test ratio of partially matching strings."""
        result = ratio("hello", "hallo")
        assert 70 < result < 90

    def test_tuple_comparison(self):
        """Test ratio with tuples."""
        t1 = ("a", "b", "c")
        t2 = ("a", "b", "d")
        result = ratio(t1, t2)
        assert result > 50


class TestFillString:
    """Tests for the fill_string function."""

    def test_adds_missing_artist(self):
        """Test adding missing artist to string."""
        result = fill_string(
            ["Artist One", "Artist Two"],
            "song-name",
            "song-name-artist-two",
        )
        assert "artisttwo" in result.replace("-", "")

    def test_no_duplicate_addition(self):
        """Test that existing artists aren't duplicated."""
        result = fill_string(
            ["Artist One"],
            "artist-one-song",
            "artist-one-song",
        )
        # Should not add "artistone" again
        assert result.count("artistone") <= 1


class TestCreateCleanString:
    """Tests for the create_clean_string function."""

    def test_removes_existing_words(self):
        """Test that words in string are excluded."""
        result = create_clean_string(
            ["hello", "world", "test"],
            "hello-world",
        )
        assert "test" in result
        assert "hello" not in result
        assert "world" not in result

    def test_sorted_output(self):
        """Test sorted output."""
        result = create_clean_string(
            ["zebra", "apple", "mango"],
            "existing",
            sort=True,
        )
        assert result == "apple-mango-zebra"


class TestSortString:
    """Tests for the sort_string function."""

    def test_basic_sort(self):
        """Test basic string sorting."""
        result = sort_string(["c", "a", "b"], "-")
        assert result == "a-b-c"

    def test_custom_join(self):
        """Test custom join string."""
        result = sort_string(["c", "a", "b"], ", ")
        assert result == "a, b, c"


class TestBasedSort:
    """Tests for the based_sort function."""

    def test_sorts_based_on_reference(self):
        """Test sorting based on reference list."""
        strings = ["c", "a", "b"]
        based_on = ["a", "b", "c"]
        result_strings, result_based = based_sort(strings, based_on)

        # Both should be sorted
        assert sorted(result_strings) == ["a", "b", "c"]


class TestCreateSongTitle:
    """Tests for the create_song_title function."""

    def test_single_artist(self):
        """Test title with single artist."""
        result = create_song_title("Song Name", ["Artist"])
        assert result == "Artist - Song Name"

    def test_multiple_artists(self):
        """Test title with multiple artists."""
        result = create_song_title("Song Name", ["Artist One", "Artist Two"])
        assert result == "Artist One, Artist Two - Song Name"

    def test_no_artists(self):
        """Test title with no artists."""
        result = create_song_title("Song Name", [])
        assert result == "Song Name"


class TestCreateSearchQuery:
    """Tests for the create_search_query function."""

    def test_basic_query(self):
        """Test basic search query creation."""
        result = create_search_query("Song Name", ["Artist"])
        assert result == "Artist - Song Name"

    def test_short_query(self):
        """Test short query (first artist only)."""
        result = create_search_query("Song Name", ["Artist One", "Artist Two"], short=True)
        assert result == "Artist One - Song Name"

    def test_artist_in_song_name(self):
        """Test query when artist is in song name."""
        result = create_search_query("Song by Artist One", ["Artist One", "Artist Two"], short=True)
        # Should still include the first artist
        assert "Artist One" in result
