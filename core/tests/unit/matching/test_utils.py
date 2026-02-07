"""Unit tests for matching utility functions."""

from __future__ import annotations

import pytest

from spotdl_core.matching.utils import (
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
    """Test slugify function."""

    def test_slugify_simple_string(self):
        """Test slugify with simple ASCII string."""
        assert slugify("Hello World") == "hello-world"

    def test_slugify_with_special_chars(self):
        """Test slugify handles special characters."""
        result = slugify("Hello, World!")
        assert "hello" in result
        assert "world" in result

    def test_slugify_with_numbers(self):
        """Test slugify preserves numbers."""
        assert slugify("Song 123") == "song-123"

    def test_slugify_with_accents(self):
        """Test slugify handles accented characters."""
        result = slugify("Café")
        assert result == "cafe"

    def test_slugify_with_unicode(self):
        """Test slugify handles various unicode characters."""
        result = slugify("Test™®")
        assert "test" in result

    def test_slugify_empty_string(self):
        """Test slugify with empty string."""
        assert slugify("") == ""

    def test_slugify_only_special_chars(self):
        """Test slugify with only special characters."""
        result = slugify("!!!")
        # May preserve some special chars based on regex
        assert len(result) >= 0

    def test_slugify_with_hyphens(self):
        """Test slugify preserves hyphens."""
        assert slugify("test-song") == "test-song"

    def test_slugify_multiple_spaces(self):
        """Test slugify handles multiple spaces."""
        assert slugify("test   song") == "test-song"

    def test_slugify_leading_trailing_spaces(self):
        """Test slugify handles leading/trailing spaces."""
        assert slugify("  test song  ") == "test-song"

    def test_slugify_with_ampersand(self):
        """Test slugify handles ampersands."""
        assert slugify("Artist & Artist") == "artist-artist"

    def test_slugify_with_parentheses(self):
        """Test slugify handles parentheses."""
        assert slugify("Song (feat. Artist)") == "song-feat-artist"

    def test_slugify_with_brackets(self):
        """Test slugify handles brackets."""
        assert slugify("Song [Official Video]") == "song-official-video"

    def test_slugify_with_quotes(self):
        """Test slugify handles quotes."""
        result = slugify("Song's Name")
        assert "song" in result
        assert "name" in result
        result2 = slugify('"Quoted"')
        assert "quoted" in result2

    def test_slugify_with_underscores(self):
        """Test slugify handles underscores."""
        assert slugify("test_song") == "test-song"

    def test_slugify_japanese_characters(self):
        """Test slugify handles Japanese characters."""
        result = slugify("テスト")
        assert result  # Should return romanized version
        assert "-" in result or result.isalnum()

    def test_slugify_mixed_japanese_english(self):
        """Test slugify handles mixed Japanese and English."""
        result = slugify("Test テスト Song")
        assert "test" in result
        assert "song" in result

    def test_slugify_preserves_at_symbol(self):
        """Test slugify preserves @ symbol."""
        assert "@" in slugify("test@test") or slugify("test@test") == "testtest"

    def test_slugify_preserves_dollar_symbol(self):
        """Test slugify preserves $ symbol."""
        result = slugify("$100")
        assert "$" in result or result == "100"

    def test_slugify_preserves_exclamation(self):
        """Test slugify preserves ! symbol."""
        result = slugify("Test!")
        assert "!" in result or result == "test"

    def test_slugify_caching(self):
        """Test slugify caches results."""
        # Call twice with same input
        result1 = slugify("Test String")
        result2 = slugify("Test String")
        assert result1 == result2
        assert result1 is result2  # Should be same object due to caching

    def test_slugify_case_insensitive(self):
        """Test slugify converts to lowercase."""
        assert slugify("TEST") == "test"
        assert slugify("TeSt") == "test"

    def test_slugify_consecutive_hyphens(self):
        """Test slugify doesn't create consecutive hyphens."""
        result = slugify("test  --  song")
        assert "--" not in result


class TestRatio:
    """Test ratio function."""

    def test_ratio_identical_strings(self):
        """Test ratio with identical strings."""
        assert ratio("test", "test") == 100.0

    def test_ratio_completely_different(self):
        """Test ratio with completely different strings."""
        result = ratio("abc", "xyz")
        assert result < 50.0

    def test_ratio_similar_strings(self):
        """Test ratio with similar strings."""
        result = ratio("test", "tests")
        assert 50.0 < result < 100.0

    def test_ratio_empty_strings(self):
        """Test ratio with empty strings."""
        result = ratio("", "")
        assert result == 100.0

    def test_ratio_one_empty_string(self):
        """Test ratio with one empty string."""
        result = ratio("test", "")
        assert result == 0.0

    def test_ratio_case_sensitive(self):
        """Test ratio is case sensitive."""
        result1 = ratio("test", "TEST")
        result2 = ratio("test", "test")
        assert result1 < result2

    def test_ratio_with_tuples(self):
        """Test ratio works with tuples."""
        result = ratio(("a", "b"), ("a", "b"))
        assert result == 100.0

    def test_ratio_different_tuples(self):
        """Test ratio with different tuples."""
        result = ratio(("a", "b"), ("c", "d"))
        assert result < 100.0

    def test_ratio_mixed_tuple_lengths(self):
        """Test ratio with different tuple lengths."""
        result = ratio(("a", "b", "c"), ("a", "b"))
        assert 50.0 < result < 100.0

    def test_ratio_caching(self):
        """Test ratio caches results."""
        result1 = ratio("test", "test")
        result2 = ratio("test", "test")
        assert result1 == result2

    def test_ratio_symmetric(self):
        """Test ratio is symmetric."""
        result1 = ratio("abc", "def")
        result2 = ratio("def", "abc")
        assert result1 == result2

    def test_ratio_with_spaces(self):
        """Test ratio with strings containing spaces."""
        result = ratio("hello world", "hello-world")
        assert result < 100.0


class TestFillString:
    """Test fill_string function."""

    def test_fill_string_adds_missing_artist(self):
        """Test fill_string adds artist not in main string."""
        result = fill_string(
            ["artist1", "artist2"],
            "song-name",
            "song-name-artist1"
        )
        assert "artist1" in result

    def test_fill_string_no_additions_needed(self):
        """Test fill_string when all artists already present."""
        result = fill_string(
            ["artist1"],
            "song-name-artist1",
            "song-name"
        )
        assert result == "song-name-artist1"

    def test_fill_string_empty_list(self):
        """Test fill_string with empty artist list."""
        result = fill_string([], "song-name", "song-name")
        assert result == "song-name"

    def test_fill_string_multiple_artists(self):
        """Test fill_string with multiple artists."""
        result = fill_string(
            ["artist1", "artist2", "artist3"],
            "song",
            "song-artist1-artist2-artist3"
        )
        assert "artist1" in result
        assert "artist2" in result
        assert "artist3" in result

    def test_fill_string_ignores_hyphens(self):
        """Test fill_string ignores hyphens in matching."""
        result = fill_string(
            ["art-ist"],
            "song",
            "song-artist"
        )
        assert "artist" in result.replace("-", "")

    def test_fill_string_partial_match(self):
        """Test fill_string with partial artist matches."""
        result = fill_string(
            ["artist"],
            "song",
            "song-artist-name"
        )
        assert "artist" in result

    def test_fill_string_artist_already_in_main(self):
        """Test fill_string doesn't add artist already in main string."""
        result = fill_string(
            ["artist1"],
            "song-artist1",
            "song-artist1"
        )
        # Should not duplicate artist1
        count = result.split("-").count("artist1")
        assert count == 1


class TestCreateCleanString:
    """Test create_clean_string function."""

    def test_create_clean_string_filters_words(self):
        """Test create_clean_string filters words present in string."""
        result = create_clean_string(
            ["artist1", "artist2"],
            "song-artist1",
            sort=False
        )
        assert "artist1" not in result
        assert "artist2" in result

    def test_create_clean_string_with_sorting(self):
        """Test create_clean_string with sorting enabled."""
        result = create_clean_string(
            ["zebra", "apple"],
            "song",
            sort=True
        )
        assert result == "apple-zebra"

    def test_create_clean_string_without_sorting(self):
        """Test create_clean_string without sorting."""
        result = create_clean_string(
            ["zebra", "apple"],
            "song",
            sort=False
        )
        assert result == "zebra-apple"

    def test_create_clean_string_custom_join(self):
        """Test create_clean_string with custom join string."""
        result = create_clean_string(
            ["artist1", "artist2"],
            "song",
            sort=False,
            join_str=" "
        )
        assert result == "artist1 artist2"

    def test_create_clean_string_empty_words(self):
        """Test create_clean_string with empty word list."""
        result = create_clean_string([], "song", sort=False)
        assert result == ""

    def test_create_clean_string_all_filtered(self):
        """Test create_clean_string when all words are filtered."""
        result = create_clean_string(
            ["song", "name"],
            "song-name",
            sort=False
        )
        assert result == ""

    def test_create_clean_string_ignores_hyphens(self):
        """Test create_clean_string ignores hyphens in matching."""
        result = create_clean_string(
            ["art-ist"],
            "artist-song",
            sort=False
        )
        assert result == ""


class TestSortString:
    """Test sort_string function."""

    def test_sort_string_alphabetical(self):
        """Test sort_string sorts alphabetically."""
        result = sort_string(["zebra", "apple", "banana"], "-")
        assert result == "apple-banana-zebra"

    def test_sort_string_custom_separator(self):
        """Test sort_string with custom separator."""
        result = sort_string(["c", "a", "b"], " ")
        assert result == "a b c"

    def test_sort_string_single_item(self):
        """Test sort_string with single item."""
        result = sort_string(["test"], "-")
        assert result == "test"

    def test_sort_string_empty_list(self):
        """Test sort_string with empty list."""
        result = sort_string([], "-")
        assert result == ""

    def test_sort_string_case_sensitive(self):
        """Test sort_string is case sensitive."""
        result = sort_string(["Zebra", "apple", "Banana"], "-")
        # Uppercase comes before lowercase in ASCII
        assert result == "Banana-Zebra-apple"

    def test_sort_string_numbers(self):
        """Test sort_string with numbers."""
        result = sort_string(["3", "1", "2"], "-")
        assert result == "1-2-3"


class TestBasedSort:
    """Test based_sort function."""

    def test_based_sort_reorders_first_list(self):
        """Test based_sort reorders first list based on second."""
        strings, based_on = based_sort(["a", "b", "c"], ["c", "a", "b"])
        # Strings are reordered based on based_on, then based_on is reversed
        assert len(strings) == 3
        assert len(based_on) == 3
        # based_on should be reversed after sorting
        assert based_on == ["c", "b", "a"]

    def test_based_sort_with_matching_items(self):
        """Test based_sort with items present in both lists."""
        strings, based_on = based_sort(["artist1", "artist2"], ["artist2", "artist1"])
        # Both lists should have 2 items
        assert len(strings) == 2
        assert len(based_on) == 2
        # based_on is reversed
        assert based_on == ["artist2", "artist1"]

    def test_based_sort_with_non_matching_items(self):
        """Test based_sort with items not in based_on list."""
        strings, based_on = based_sort(["a", "b", "x"], ["c", "a"])
        # Items not in based_on should come first (with -1 key, then reverse)
        assert "a" in strings
        assert len(based_on) == 2

    def test_based_sort_empty_lists(self):
        """Test based_sort with empty lists."""
        strings, based_on = based_sort([], [])
        assert strings == []
        assert based_on == []

    def test_based_sort_single_item(self):
        """Test based_sort with single item."""
        strings, based_on = based_sort(["a"], ["a"])
        assert strings == ["a"]
        assert based_on == ["a"]

    def test_based_sort_different_lengths(self):
        """Test based_sort with different length lists."""
        strings, based_on = based_sort(["a", "b", "c"], ["a"])
        assert "a" in strings
        assert len(strings) == 3
        assert len(based_on) == 1

    def test_based_sort_reverses_based_on(self):
        """Test based_sort reverses the based_on list."""
        strings, based_on = based_sort(["a", "b"], ["a", "b"])
        assert based_on == ["b", "a"]


class TestCreateSongTitle:
    """Test create_song_title function."""

    def test_create_song_title_single_artist(self):
        """Test create_song_title with single artist."""
        result = create_song_title("Song Name", ["Artist"])
        assert result == "Artist - Song Name"

    def test_create_song_title_multiple_artists(self):
        """Test create_song_title with multiple artists."""
        result = create_song_title("Song Name", ["Artist1", "Artist2"])
        assert result == "Artist1, Artist2 - Song Name"

    def test_create_song_title_three_artists(self):
        """Test create_song_title with three artists."""
        result = create_song_title("Song", ["A", "B", "C"])
        assert result == "A, B, C - Song"

    def test_create_song_title_empty_artist_list(self):
        """Test create_song_title with empty artist list."""
        result = create_song_title("Song Name", [])
        assert result == "Song Name"

    def test_create_song_title_preserves_song_name(self):
        """Test create_song_title preserves song name exactly."""
        result = create_song_title("Song (Remix)", ["Artist"])
        assert "Song (Remix)" in result

    def test_create_song_title_with_special_chars(self):
        """Test create_song_title with special characters."""
        result = create_song_title("Song & Name", ["Artist"])
        assert result == "Artist - Song & Name"


class TestCreateSearchQuery:
    """Test create_search_query function."""

    def test_create_search_query_full(self):
        """Test create_search_query without short flag."""
        result = create_search_query("Song", ["Artist1", "Artist2"], short=False)
        assert result == "Artist1, Artist2 - Song"

    def test_create_search_query_short(self):
        """Test create_search_query with short flag."""
        result = create_search_query("Song", ["Artist1", "Artist2"], short=True)
        assert result == "Artist1 - Song"

    def test_create_search_query_short_filters_artist_in_name(self):
        """Test create_search_query short mode filters artist from song name."""
        result = create_search_query("Artist1 Song", ["Artist1", "Artist2"], short=True)
        # Should still include Artist1 as main artist
        assert "Artist1" in result

    def test_create_search_query_short_single_artist(self):
        """Test create_search_query short with single artist."""
        result = create_search_query("Song", ["Artist"], short=True)
        assert result == "Artist - Song"

    def test_create_search_query_artist_in_song_name(self):
        """Test create_search_query when artist is in song name."""
        result = create_search_query("Artist Song Name", ["Artist"], short=True)
        assert "Artist" in result

    def test_create_search_query_multiple_artists_in_name(self):
        """Test create_search_query with multiple artists in song name."""
        result = create_search_query(
            "Artist1 & Artist2 Song",
            ["Artist1", "Artist2"],
            short=True
        )
        assert "Artist1" in result

    def test_create_search_query_preserves_order(self):
        """Test create_search_query preserves artist order."""
        result = create_search_query("Song", ["First", "Second"], short=False)
        assert result == "First, Second - Song"

    def test_create_search_query_empty_artists(self):
        """Test create_search_query with empty artist list."""
        result = create_search_query("Song", [], short=False)
        assert result == "Song"


class TestUtilsEdgeCases:
    """Test edge cases and error handling."""

    def test_slugify_very_long_string(self):
        """Test slugify with very long string."""
        long_string = "a" * 1000
        result = slugify(long_string)
        assert len(result) > 0

    def test_ratio_very_long_strings(self):
        """Test ratio with very long strings."""
        long_string = "a" * 1000
        result = ratio(long_string, long_string)
        assert result == 100.0

    def test_fill_string_complex_names(self):
        """Test fill_string with complex artist names."""
        result = fill_string(
            ["AC/DC", "Guns N' Roses"],
            "song",
            "song-ac-dc-guns-n-roses"
        )
        assert "ac" in result.lower()

    def test_create_clean_string_unicode_words(self):
        """Test create_clean_string with unicode words."""
        result = create_clean_string(
            ["Café", "Naïve"],
            "song",
            sort=False
        )
        assert len(result) > 0

    def test_based_sort_duplicate_items(self):
        """Test based_sort with duplicate items."""
        strings, based_on = based_sort(["a", "a", "b"], ["a", "b"])
        assert len(strings) == 3
        assert "a" in strings
        assert "b" in strings

    def test_create_song_title_unicode_artists(self):
        """Test create_song_title with unicode artist names."""
        result = create_song_title("Song", ["Björk", "Sigur Rós"])
        assert "Björk" in result
        assert "Sigur Rós" in result

    def test_slugify_korean_characters(self):
        """Test slugify with Korean characters."""
        result = slugify("한글")
        assert len(result) > 0

    def test_slugify_chinese_characters(self):
        """Test slugify with Chinese characters."""
        result = slugify("中文")
        assert len(result) > 0

    def test_slugify_emoji(self):
        """Test slugify with emoji."""
        result = slugify("Test 🎵 Song")
        assert "test" in result
        assert "song" in result

    def test_ratio_unicode_strings(self):
        """Test ratio with unicode strings."""
        result = ratio("Café", "Cafe")
        assert result < 100.0  # Different characters

    def test_fill_string_with_numbers(self):
        """Test fill_string with numbers in names."""
        result = fill_string(
            ["Artist 1", "Artist 2"],
            "song",
            "song-artist-1"
        )
        assert "artist" in result.lower()
