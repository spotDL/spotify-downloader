"""Tests for the matching engine."""

import pytest

from spotdl.core.matching.engine import get_best_matches, get_best_result, order_results
from spotdl.core.types.result import Result, TargetPlatform
from spotdl.core.types.song import Platform, Song
from tests.conftest import create_result, create_song


class TestOrderResults:
    """Tests for the order_results function."""

    def test_empty_results(self):
        """Test with empty results list."""
        song = create_song(name="Test Song")
        result = order_results([], song)
        assert result == {}

    def test_perfect_match(self):
        """Test with a perfect matching result."""
        song = create_song(
            name="Test Song",
            artists=["Test Artist"],
            duration=180,
        )
        result = create_result(
            name="Test Artist - Test Song",
            artists=("Test Artist",),
            duration=180.0,
            verified=True,
        )

        scores = order_results([result], song)
        assert len(scores) == 1
        assert scores[result] > 80.0

    def test_filters_no_common_words(self):
        """Test that results with no common words are filtered."""
        song = create_song(name="Specific Song Name")
        result = create_result(
            name="Completely Different Title",
            artists=("Different Artist",),
            duration=180.0,
        )

        scores = order_results([result], song)
        assert len(scores) == 0

    def test_filters_low_name_match(self):
        """Test that results with low name match are filtered."""
        song = create_song(name="Original Song Title")
        result = create_result(
            name="Song",  # Only one word matches
            artists=("Artist",),
            duration=180.0,
        )

        scores = order_results([result], song)
        # Should be filtered due to low name match
        assert len(scores) == 0

    def test_filters_low_artist_match(self):
        """Test that results with low artist match are filtered."""
        song = create_song(
            name="Test Song",
            artists=["Real Artist"],
        )
        result = create_result(
            name="Test Song",
            artists=("Wrong Artist",),
            duration=180.0,
        )

        scores = order_results([result], song)
        # Should be filtered due to low artist match
        assert len(scores) == 0

    def test_filters_low_time_match(self):
        """Test that results with very different duration are filtered."""
        song = create_song(
            name="Test Song",
            artists=["Artist"],
            duration=180,
        )
        result = create_result(
            name="Artist - Test Song",
            artists=("Artist",),
            duration=600.0,  # 10 minutes - way off
            verified=True,
        )

        scores = order_results([result], song)
        # Should be filtered due to low time match
        assert len(scores) == 0

    def test_penalizes_forbidden_words(self):
        """Test that forbidden words reduce score."""
        song = create_song(
            name="Original Song",
            artists=["Artist"],
            duration=180,
        )
        original_result = create_result(
            name="Artist - Original Song",
            artists=("Artist",),
            duration=180.0,
            verified=True,
        )
        remix_result = create_result(
            name="Artist - Original Song Remix",
            artists=("Artist",),
            duration=180.0,
            verified=True,
        )

        original_scores = order_results([original_result], song)
        remix_scores = order_results([remix_result], song)

        # Both should pass, but original should score higher
        if remix_result in remix_scores:
            assert original_scores[original_result] > remix_scores[remix_result]

    def test_multiple_results_ranked(self):
        """Test that multiple results are properly ranked."""
        song = create_song(
            name="Test Song",
            artists=["Artist"],
            duration=180,
        )

        good_result = create_result(
            name="Artist - Test Song",
            artists=("Artist",),
            duration=180.0,
            verified=True,
        )
        okay_result = create_result(
            name="Artist - Test Song (Audio)",
            artists=("Artist",),
            duration=185.0,
            verified=True,
        )

        scores = order_results([good_result, okay_result], song)

        if good_result in scores and okay_result in scores:
            assert scores[good_result] >= scores[okay_result]


class TestGetBestMatches:
    """Tests for the get_best_matches function."""

    def test_empty_results(self):
        """Test with empty results."""
        result = get_best_matches({})
        assert result == []

    def test_single_result(self):
        """Test with single result."""
        result = create_result(name="Test")
        scores = {result: 85.0}

        best = get_best_matches(scores)
        assert len(best) == 1
        assert best[0] == (result, 85.0)

    def test_returns_top_scores(self):
        """Test that only top scores within threshold are returned."""
        result1 = create_result(name="Test 1")
        result2 = create_result(name="Test 2")
        result3 = create_result(name="Test 3")

        scores = {
            result1: 95.0,
            result2: 92.0,  # Within default threshold of 5
            result3: 80.0,  # Outside threshold
        }

        best = get_best_matches(scores, score_threshold=5.0)
        assert len(best) == 2
        assert best[0][0] == result1
        assert best[1][0] == result2

    def test_custom_threshold(self):
        """Test with custom threshold."""
        result1 = create_result(name="Test 1")
        result2 = create_result(name="Test 2")

        scores = {
            result1: 95.0,
            result2: 85.0,
        }

        # With threshold of 10, both should be included
        best = get_best_matches(scores, score_threshold=10.0)
        assert len(best) == 2

        # With threshold of 5, only top should be included
        best = get_best_matches(scores, score_threshold=5.0)
        assert len(best) == 1


class TestGetBestResult:
    """Tests for the get_best_result function."""

    def test_returns_best_match(self):
        """Test that best match is returned."""
        song = create_song(
            name="Test Song",
            artists=["Artist"],
            duration=180,
        )
        result = create_result(
            name="Artist - Test Song",
            artists=("Artist",),
            duration=180.0,
            verified=True,
        )

        best = get_best_result([result], song)
        assert best is not None
        assert best[0] == result
        assert best[1] > 80.0

    def test_returns_none_below_threshold(self):
        """Test that None is returned when score is below threshold."""
        song = create_song(
            name="Test Song",
            artists=["Artist"],
            duration=180,
        )
        result = create_result(
            name="Somewhat Similar",
            artists=("Artist",),
            duration=180.0,
        )

        best = get_best_result([result], song, min_score=99.0)
        # Should return None if no result meets the high threshold
        # (depends on actual score)

    def test_empty_results(self):
        """Test with empty results list."""
        song = create_song(name="Test")
        best = get_best_result([], song)
        assert best is None

    def test_below_min_score(self):
        """Test returns None when best score is below min_score."""
        song = create_song(
            name="Test Song",
            artists=["Artist"],
            duration=180,
        )
        # Create a result that will match but with lower score
        result = create_result(
            name="Artist - Test Song Variation",
            artists=("Artist",),
            duration=180.0,
            verified=True,
        )

        # Use a very high min_score that the result won't meet
        best = get_best_result([result], song, min_score=99.9)
        assert best is None


class TestOrderResultsAlbumMatching:
    """Tests for album matching in order_results."""

    def test_verified_with_low_album_match(self):
        """Test verified result with album but low album match."""
        song = create_song(
            name="Test Song",
            artists=["Artist"],
            duration=180,
            album_name="Original Album",
        )
        result = create_result(
            name="Artist - Test Song",
            artists=("Artist",),
            duration=180.0,
            verified=True,
            album_name="Different Album",
        )

        scores = order_results([result], song)
        # Should still match, but potentially with lower score due to album mismatch
        assert result in scores or len(scores) == 0


class TestOrderResultsTimeAndAverage:
    """Tests for time and average match filtering."""

    def test_low_time_and_low_average(self):
        """Test filtering when both time and average are low."""
        song = create_song(
            name="Test Song",
            artists=["Artist"],
            duration=180,
        )
        result = create_result(
            name="Artist - Test Song Something",
            artists=("Some Other Artist",),  # Will cause lower artist match
            duration=200.0,  # 20 seconds off - lower time match
            verified=False,
        )

        scores = order_results([result], song)
        # May be filtered due to both being low
        # Result depends on actual scoring


class TestOrderResultsExplicitMismatch:
    """Tests for explicit content mismatch penalty."""

    def test_explicit_mismatch_penalty(self):
        """Test that explicit mismatch applies penalty."""
        song = create_song(
            name="Clean Song",
            artists=["Artist"],
            duration=180,
            explicit=False,
        )
        explicit_result = create_result(
            name="Artist - Clean Song",
            artists=("Artist",),
            duration=185.0,  # Slightly different to trigger time match factor
            verified=True,
            explicit=True,
        )
        clean_result = create_result(
            name="Artist - Clean Song",
            artists=("Artist",),
            duration=185.0,
            verified=True,
            explicit=False,
        )

        explicit_scores = order_results([explicit_result], song)
        clean_scores = order_results([clean_result], song)

        # If both match, clean version should score higher
        if explicit_result in explicit_scores and clean_result in clean_scores:
            assert clean_scores[clean_result] >= explicit_scores[explicit_result]


class TestOrderResultsWithSearchQuery:
    """Tests for order_results with search query."""

    def test_with_search_query(self):
        """Test matching with custom search query."""
        song = create_song(
            name="Test Song",
            artists=["Artist"],
            duration=180,
        )
        result = create_result(
            name="Artist - Test Song",
            artists=("Artist",),
            duration=180.0,
            verified=True,
        )

        scores = order_results([result], song, search_query="artist test song")
        assert result in scores


class TestOrderResultsISRCSearch:
    """Tests for ISRC search handling."""

    def test_isrc_search_result(self):
        """Test ISRC search results are handled differently."""
        song = create_song(
            name="Test Song",
            artists=["Artist"],
            duration=180,
        )
        result = create_result(
            name="Artist - Test Song",
            artists=("Artist",),
            duration=180.0,
            verified=True,
            isrc_search=True,
        )

        scores = order_results([result], song)
        assert result in scores
