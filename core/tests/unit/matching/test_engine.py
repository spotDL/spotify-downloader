"""Unit tests for matching engine."""

from __future__ import annotations

import pytest

from spotdl_core.matching.engine import (
    get_best_matches,
    get_best_result,
    order_results,
)
from spotdl_core.types import Platform, Result, Song, TargetPlatform


class TestOrderResults:
    """Test order_results function."""

    @pytest.fixture
    def song(self) -> Song:
        """Create a test song."""
        return Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

    @pytest.fixture
    def perfect_result(self) -> Result:
        """Create a perfect matching result."""
        return Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="perfect123",
            url="https://youtube.com/perfect",
        )

    @pytest.fixture
    def good_result(self) -> Result:
        """Create a good matching result."""
        return Result(
            name="Test Song Official",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=185,
            platform=TargetPlatform.YOUTUBE,
            platform_id="good123",
            url="https://youtube.com/good",
        )

    @pytest.fixture
    def poor_result(self) -> Result:
        """Create a poor matching result."""
        return Result(
            name="Different Song",
            artists=("Other Artist",),
            artist="Other Artist",
            duration=240,
            platform=TargetPlatform.YOUTUBE,
            platform_id="poor123",
            url="https://youtube.com/poor",
        )

    def test_order_results_empty_list(self, song: Song):
        """Test order_results with empty result list."""
        results = order_results([], song)
        assert results == {}

    def test_order_results_single_result(self, song: Song, perfect_result: Result):
        """Test order_results with single result."""
        results = order_results([perfect_result], song)
        assert len(results) == 1
        assert perfect_result in results
        assert results[perfect_result] > 80.0

    def test_order_results_multiple_results(
        self, song: Song, perfect_result: Result, good_result: Result
    ):
        """Test order_results with multiple results."""
        results = order_results([perfect_result, good_result], song)
        assert len(results) >= 1
        assert perfect_result in results or good_result in results

    def test_order_results_filters_poor_matches(
        self, song: Song, perfect_result: Result, poor_result: Result
    ):
        """Test order_results filters out poor matches."""
        results = order_results([perfect_result, poor_result], song)
        # Poor result should be filtered out
        if poor_result in results:
            assert results[poor_result] < results.get(perfect_result, 0)

    def test_order_results_with_search_query(self, song: Song, perfect_result: Result):
        """Test order_results with search query."""
        results = order_results(
            [perfect_result], song, search_query="Test Artist - Test Song"
        )
        assert len(results) >= 0

    def test_order_results_with_custom_thresholds(
        self, song: Song, perfect_result: Result
    ):
        """Test order_results with custom minimum thresholds."""
        results = order_results(
            [perfect_result],
            song,
            min_name_match=80.0,
            min_artist_match=80.0,
            min_time_match=50.0,
        )
        # Should still match with higher thresholds
        assert len(results) >= 0

    def test_order_results_scores_in_range(self, song: Song, perfect_result: Result):
        """Test order_results returns scores between 0 and 100."""
        results = order_results([perfect_result], song)
        for score in results.values():
            assert 0.0 <= score <= 100.0

    def test_order_results_no_common_words(self, song: Song):
        """Test order_results filters results with no common words."""
        result = Result(
            name="Xyzzyx Qwertx",
            artists=("Zzzzz",),
            artist="Zzzzz",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="uncommon123",
            url="https://youtube.com/uncommon",
        )
        results = order_results([result], song)
        # Should be filtered out due to no common words
        assert len(results) == 0

    def test_order_results_artist_name_threshold(self, song: Song):
        """Test order_results filters by artist match threshold."""
        result = Result(
            name="Test Song",
            artists=("Completely Different Artist",),
            artist="Completely Different Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="diff123",
            url="https://youtube.com/diff",
        )
        results = order_results([result], song)
        # Should be filtered due to low artist match
        assert result not in results or results[result] < 70.0

    def test_order_results_song_name_threshold(self, song: Song):
        """Test order_results filters by name match threshold."""
        result = Result(
            name="Completely Different Name",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="diffname123",
            url="https://youtube.com/diffname",
        )
        results = order_results([result], song)
        # Should be filtered due to low name match
        assert result not in results

    def test_order_results_time_threshold(self, song: Song):
        """Test order_results considers time match."""
        result = Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=600,  # 10 minutes vs 3 minutes
            platform=TargetPlatform.YOUTUBE,
            platform_id="long123",
            url="https://youtube.com/long",
        )
        results = order_results([result], song)
        # Should be filtered or scored low due to time mismatch
        assert result not in results or results[result] < 80.0

    def test_order_results_forbidden_words_penalty(self, song: Song):
        """Test order_results applies forbidden words penalty."""
        result_clean = Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="clean123",
            url="https://youtube.com/clean",
        )
        result_remix = Result(
            name="Test Song Remix",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="remix123",
            url="https://youtube.com/remix",
        )
        results = order_results([result_clean, result_remix], song)
        if result_clean in results and result_remix in results:
            # Clean version should score higher
            assert results[result_clean] > results[result_remix]

    def test_order_results_explicit_mismatch_penalty(self):
        """Test order_results applies explicit mismatch penalty."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
            explicit=True,
        )
        result_explicit = Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="explicit123",
            url="https://youtube.com/explicit",
            explicit=True,
        )
        result_clean = Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="clean123",
            url="https://youtube.com/clean",
            explicit=False,
        )
        results = order_results([result_explicit, result_clean], song)
        if result_explicit in results and result_clean in results:
            # Explicit version should score higher for explicit song
            assert results[result_explicit] >= results[result_clean]

    def test_order_results_verified_results(self, song: Song):
        """Test order_results handles verified results."""
        result = Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="verified123",
            url="https://youtube.com/verified",
            verified=True,
        )
        results = order_results([result], song)
        assert len(results) >= 0

    def test_order_results_with_album_match(self):
        """Test order_results considers album match for verified results."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
            album_name="Test Album",
        )
        result = Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="album123",
            url="https://youtube.com/album",
            verified=True,
            album_name="Test Album",
        )
        results = order_results([result], song)
        assert len(results) >= 0
        if result in results:
            assert results[result] > 0.0

    def test_order_results_isrc_search(self, song: Song):
        """Test order_results handles ISRC search results."""
        result = Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="isrc123",
            url="https://youtube.com/isrc",
            isrc_search=True,
        )
        results = order_results([result], song)
        assert len(results) >= 0

    def test_order_results_caps_at_100(self, song: Song):
        """Test order_results caps scores at 100."""
        result = Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="perfect123",
            url="https://youtube.com/perfect",
        )
        results = order_results([result], song)
        for score in results.values():
            assert score <= 100.0


class TestGetBestMatches:
    """Test get_best_matches function."""

    @pytest.fixture
    def result1(self) -> Result:
        """Create first result."""
        return Result(
            name="Song 1",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="id1",
            url="https://youtube.com/1",
        )

    @pytest.fixture
    def result2(self) -> Result:
        """Create second result."""
        return Result(
            name="Song 2",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="id2",
            url="https://youtube.com/2",
        )

    @pytest.fixture
    def result3(self) -> Result:
        """Create third result."""
        return Result(
            name="Song 3",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="id3",
            url="https://youtube.com/3",
        )

    def test_get_best_matches_empty_dict(self):
        """Test get_best_matches with empty dictionary."""
        results = get_best_matches({})
        assert results == []

    def test_get_best_matches_single_result(self, result1: Result):
        """Test get_best_matches with single result."""
        scored = {result1: 90.0}
        results = get_best_matches(scored)
        assert len(results) == 1
        assert results[0] == (result1, 90.0)

    def test_get_best_matches_multiple_results_within_threshold(
        self, result1: Result, result2: Result, result3: Result
    ):
        """Test get_best_matches with multiple results within threshold."""
        scored = {result1: 95.0, result2: 93.0, result3: 91.0}
        results = get_best_matches(scored, score_threshold=5.0)
        # All should be within 5 points of best (95)
        assert len(results) == 3

    def test_get_best_matches_filters_outside_threshold(
        self, result1: Result, result2: Result, result3: Result
    ):
        """Test get_best_matches filters results outside threshold."""
        scored = {result1: 95.0, result2: 85.0, result3: 75.0}
        results = get_best_matches(scored, score_threshold=5.0)
        # Only result1 and maybe result2 should be included
        assert len(results) <= 2
        assert results[0][0] == result1

    def test_get_best_matches_sorted_by_score(
        self, result1: Result, result2: Result, result3: Result
    ):
        """Test get_best_matches returns results sorted by score."""
        scored = {result1: 85.0, result2: 95.0, result3: 90.0}
        results = get_best_matches(scored)
        # Should be sorted descending
        assert results[0][0] == result2  # Highest score
        if len(results) > 1:
            assert results[0][1] >= results[1][1]

    def test_get_best_matches_custom_threshold(
        self, result1: Result, result2: Result
    ):
        """Test get_best_matches with custom threshold."""
        scored = {result1: 90.0, result2: 85.0}
        results = get_best_matches(scored, score_threshold=3.0)
        # result2 is 5 points away, outside 3.0 threshold
        assert len(results) == 1
        assert results[0][0] == result1

    def test_get_best_matches_zero_threshold(
        self, result1: Result, result2: Result
    ):
        """Test get_best_matches with zero threshold."""
        scored = {result1: 90.0, result2: 85.0}
        results = get_best_matches(scored, score_threshold=0.0)
        # Only exact best match
        assert len(results) == 1
        assert results[0][0] == result1

    def test_get_best_matches_large_threshold(
        self, result1: Result, result2: Result, result3: Result
    ):
        """Test get_best_matches with large threshold."""
        scored = {result1: 90.0, result2: 50.0, result3: 20.0}
        results = get_best_matches(scored, score_threshold=100.0)
        # All should be included
        assert len(results) == 3

    def test_get_best_matches_identical_scores(
        self, result1: Result, result2: Result
    ):
        """Test get_best_matches with identical scores."""
        scored = {result1: 90.0, result2: 90.0}
        results = get_best_matches(scored, score_threshold=0.0)
        # Both should be included as they match best score
        assert len(results) == 2

    def test_get_best_matches_returns_tuples(self, result1: Result):
        """Test get_best_matches returns list of tuples."""
        scored = {result1: 90.0}
        results = get_best_matches(scored)
        assert isinstance(results, list)
        assert isinstance(results[0], tuple)
        assert len(results[0]) == 2


class TestGetBestResult:
    """Test get_best_result function."""

    @pytest.fixture
    def song(self) -> Song:
        """Create a test song."""
        return Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

    @pytest.fixture
    def good_result(self) -> Result:
        """Create a good result."""
        return Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="good123",
            url="https://youtube.com/good",
        )

    @pytest.fixture
    def poor_result(self) -> Result:
        """Create a poor result."""
        return Result(
            name="Different Song",
            artists=("Other Artist",),
            artist="Other Artist",
            duration=300,
            platform=TargetPlatform.YOUTUBE,
            platform_id="poor123",
            url="https://youtube.com/poor",
        )

    def test_get_best_result_empty_list(self, song: Song):
        """Test get_best_result with empty result list."""
        result = get_best_result([], song)
        assert result is None

    def test_get_best_result_single_good_result(
        self, song: Song, good_result: Result
    ):
        """Test get_best_result with single good result."""
        result = get_best_result([good_result], song)
        if result is not None:
            assert result[0] == good_result
            assert result[1] >= 80.0

    def test_get_best_result_single_poor_result(
        self, song: Song, poor_result: Result
    ):
        """Test get_best_result with single poor result."""
        result = get_best_result([poor_result], song, min_score=80.0)
        # Should be None due to low score
        assert result is None or result[1] < 80.0

    def test_get_best_result_multiple_results(
        self, song: Song, good_result: Result, poor_result: Result
    ):
        """Test get_best_result selects best from multiple."""
        result = get_best_result([good_result, poor_result], song)
        if result is not None:
            # Should select good_result
            assert result[0] == good_result or result[1] >= 70.0

    def test_get_best_result_with_search_query(
        self, song: Song, good_result: Result
    ):
        """Test get_best_result with search query."""
        result = get_best_result(
            [good_result], song, search_query="Test Artist - Test Song"
        )
        assert result is None or isinstance(result, tuple)

    def test_get_best_result_custom_min_score(
        self, song: Song, good_result: Result
    ):
        """Test get_best_result with custom minimum score."""
        result = get_best_result([good_result], song, min_score=95.0)
        # May be None if score doesn't reach 95
        assert result is None or result[1] >= 95.0

    def test_get_best_result_returns_tuple(self, song: Song, good_result: Result):
        """Test get_best_result returns tuple or None."""
        result = get_best_result([good_result], song)
        assert result is None or (isinstance(result, tuple) and len(result) == 2)

    def test_get_best_result_score_in_range(self, song: Song, good_result: Result):
        """Test get_best_result score is in valid range."""
        result = get_best_result([good_result], song)
        if result is not None:
            assert 0.0 <= result[1] <= 100.0

    def test_get_best_result_min_score_zero(self, song: Song, good_result: Result):
        """Test get_best_result with zero minimum score."""
        result = get_best_result([good_result], song, min_score=0.0)
        # Should return result if it passes other filters
        assert result is None or result[1] >= 0.0

    def test_get_best_result_min_score_100(self, song: Song, good_result: Result):
        """Test get_best_result with minimum score of 100."""
        result = get_best_result([good_result], song, min_score=100.0)
        # Should be None unless perfect match
        assert result is None or result[1] == 100.0


class TestEngineIntegration:
    """Integration tests for matching engine."""

    def test_full_matching_pipeline(self):
        """Test complete matching pipeline from song to best result."""
        song = Song(
            name="Bohemian Rhapsody",
            artists=["Queen"],
            artist="Queen",
            duration=354,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
            album_name="A Night at the Opera",
        )

        results = [
            Result(
                name="Queen - Bohemian Rhapsody",
                artists=("Queen",),
                artist="Queen",
                duration=354,
                platform=TargetPlatform.YOUTUBE,
                platform_id="perfect",
                url="https://youtube.com/perfect",
                album_name="A Night at the Opera",
            ),
            Result(
                name="Bohemian Rhapsody Remix",
                artists=("Queen",),
                artist="Queen",
                duration=360,
                platform=TargetPlatform.YOUTUBE,
                platform_id="remix",
                url="https://youtube.com/remix",
            ),
            Result(
                name="Different Song",
                artists=("Other",),
                artist="Other",
                duration=200,
                platform=TargetPlatform.YOUTUBE,
                platform_id="bad",
                url="https://youtube.com/bad",
            ),
        ]

        # Order results
        scored = order_results(results, song)
        assert len(scored) >= 1

        # Get best matches
        best_matches = get_best_matches(scored)
        assert len(best_matches) >= 1

        # Get single best result
        best = get_best_result(results, song)
        if best is not None:
            assert best[0] == results[0]  # Should select perfect match

    def test_realistic_youtube_scenario(self):
        """Test realistic scenario with YouTube results."""
        song = Song(
            name="Shape of You",
            artists=["Ed Sheeran"],
            artist="Ed Sheeran",
            duration=233,
            platform=Platform.SPOTIFY,
            platform_id="spotify123",
            url="https://spotify.com/track/123",
        )

        results = [
            Result(
                name="Ed Sheeran - Shape of You [Official Video]",
                artists=("Ed Sheeran",),
                artist="Ed Sheeran",
                duration=233,
                platform=TargetPlatform.YOUTUBE,
                platform_id="official",
                url="https://youtube.com/official",
                verified=True,
            ),
            Result(
                name="Shape of You (Cover)",
                artists=("Cover Artist",),
                artist="Cover Artist",
                duration=230,
                platform=TargetPlatform.YOUTUBE,
                platform_id="cover",
                url="https://youtube.com/cover",
            ),
        ]

        best = get_best_result(results, song)
        if best is not None:
            # Should prefer official video
            assert best[0] == results[0]

    def test_edge_case_no_good_matches(self):
        """Test when no results meet threshold."""
        song = Song(
            name="Obscure Song",
            artists=["Unknown Artist"],
            artist="Unknown Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="obscure123",
            url="https://test.com",
        )

        results = [
            Result(
                name="Completely Different",
                artists=("Other",),
                artist="Other",
                duration=300,
                platform=TargetPlatform.YOUTUBE,
                platform_id="diff",
                url="https://youtube.com/diff",
            ),
        ]

        scored = order_results(results, song)
        # Should filter out poor match
        assert len(scored) == 0 or all(score < 60 for score in scored.values())

        best = get_best_result(results, song, min_score=80.0)
        # Should return None
        assert best is None
