"""Tests for matching module (from spotdl_core)."""

import pytest

from spotdl_cli.core.types import (
    DownloadResult,
    Platform,
    Song,
    TargetPlatform,
)

# Import matching from spotdl_core shared library
from spotdl_core.matching import (
    FORBIDDEN_WORDS,
    MIN_ARTIST_MATCH,
    MIN_NAME_MATCH,
    MIN_TIME_MATCH,
    calc_album_match,
    calc_artists_match,
    calc_main_artist_match,
    calc_name_match,
    calc_time_match,
    check_common_word,
    check_forbidden_words,
    get_best_matches,
    get_best_result,
    order_results,
)
from spotdl_core.matching.utils import (
    create_search_query,
    create_song_title,
    slugify,
)


class TestConstants:
    """Tests for matching constants."""

    def test_forbidden_words_exist(self) -> None:
        """Test that forbidden words are defined."""
        assert len(FORBIDDEN_WORDS) > 0
        assert "remix" in FORBIDDEN_WORDS
        assert "live" in FORBIDDEN_WORDS
        assert "acoustic" in FORBIDDEN_WORDS

    def test_thresholds(self) -> None:
        """Test that thresholds are reasonable."""
        assert MIN_NAME_MATCH == 60.0
        assert MIN_ARTIST_MATCH == 70.0
        assert MIN_TIME_MATCH == 25.0


class TestUtils:
    """Tests for matching utilities."""

    def test_slugify_basic(self) -> None:
        """Test basic slugification."""
        assert slugify("Hello World") == "hello-world"
        assert slugify("Test_String") == "test-string"
        assert slugify("Multiple   Spaces") == "multiple-spaces"

    def test_slugify_special_chars(self) -> None:
        """Test slugification with special characters."""
        assert "hello" in slugify("Hello! World?")
        assert slugify("Test & Another") == "test-another"

    def test_create_song_title(self) -> None:
        """Test song title creation."""
        assert create_song_title("Song", ["Artist"]) == "Artist - Song"
        assert create_song_title("Song", ["A1", "A2"]) == "A1, A2 - Song"
        assert create_song_title("Song", []) == "Song"

    def test_create_search_query(self) -> None:
        """Test search query creation."""
        query = create_search_query("Song", ["Artist1", "Artist2"])
        assert "Artist1" in query
        assert "Song" in query

    def test_create_search_query_short(self) -> None:
        """Test short search query creation."""
        query = create_search_query("Song", ["Artist1", "Artist2"], short=True)
        assert "Artist1" in query
        assert "Song" in query


class TestCheckFunctions:
    """Tests for check functions."""

    @pytest.fixture
    def sample_song(self) -> Song:
        """Create a sample song."""
        return Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://spotify.com/track/test123",
        )

    @pytest.fixture
    def sample_result(self) -> DownloadResult:
        """Create a sample result."""
        return DownloadResult(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=182,
            platform=TargetPlatform.YOUTUBE,
            platform_id="yt123",
            url="https://youtube.com/watch?v=yt123",
        )

    def test_check_common_word_found(
        self, sample_song: Song, sample_result: DownloadResult
    ) -> None:
        """Test common word detection when found."""
        assert check_common_word(sample_song, sample_result) is True

    def test_check_common_word_not_found(self, sample_song: Song) -> None:
        """Test common word detection when not found."""
        result = DownloadResult(
            name="Completely Different Title",
            artists=["Different Artist"],
            artist="Different Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="diff",
            url="https://youtube.com/watch?v=diff",
        )
        assert check_common_word(sample_song, result) is False

    def test_check_forbidden_words_none(
        self, sample_song: Song, sample_result: DownloadResult
    ) -> None:
        """Test no forbidden words found."""
        has_forbidden, words = check_forbidden_words(sample_song, sample_result)
        assert has_forbidden is False
        assert words == []

    def test_check_forbidden_words_found(self, sample_song: Song) -> None:
        """Test forbidden words found."""
        result = DownloadResult(
            name="Test Song (Remix)",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="remix",
            url="https://youtube.com/watch?v=remix",
        )
        has_forbidden, words = check_forbidden_words(sample_song, result)
        assert has_forbidden is True
        assert "remix" in words

    def test_check_forbidden_words_in_both(self) -> None:
        """Test forbidden words in both song and result (should not penalize)."""
        song = Song(
            name="Test Song (Remix)",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test",
            url="https://spotify.com/track/test",
        )
        result = DownloadResult(
            name="Test Song (Remix)",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="remix",
            url="https://youtube.com/watch?v=remix",
        )
        has_forbidden, words = check_forbidden_words(song, result)
        assert has_forbidden is False
        assert "remix" not in words


class TestScoringFunctions:
    """Tests for scoring functions."""

    @pytest.fixture
    def exact_match_song(self) -> Song:
        """Create a song for exact matching."""
        return Song(
            name="Bohemian Rhapsody",
            artists=["Queen"],
            artist="Queen",
            duration=354,
            platform=Platform.SPOTIFY,
            platform_id="bohemian",
            url="https://spotify.com/track/bohemian",
            album_name="A Night at the Opera",
        )

    @pytest.fixture
    def exact_match_result(self) -> DownloadResult:
        """Create a result that matches exactly."""
        return DownloadResult(
            name="Bohemian Rhapsody",
            artists=["Queen"],
            artist="Queen",
            duration=354,
            platform=TargetPlatform.YOUTUBE,
            platform_id="br_yt",
            url="https://youtube.com/watch?v=br_yt",
            album_name="A Night at the Opera",
            verified=True,
        )

    def test_calc_name_match_exact(
        self, exact_match_song: Song, exact_match_result: DownloadResult
    ) -> None:
        """Test exact name match."""
        score = calc_name_match(exact_match_song, exact_match_result)
        assert score == 100.0

    def test_calc_name_match_similar(self) -> None:
        """Test similar name match."""
        song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test",
            url="https://spotify.com/track/test",
        )
        result = DownloadResult(
            name="Test Song (Official Video)",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="yt",
            url="https://youtube.com/watch?v=yt",
        )
        score = calc_name_match(song, result)
        assert score > 60.0  # Should still be above threshold

    def test_calc_time_match_exact(
        self, exact_match_song: Song, exact_match_result: DownloadResult
    ) -> None:
        """Test exact duration match."""
        score = calc_time_match(exact_match_song, exact_match_result)
        assert score == 100.0

    def test_calc_time_match_close(self) -> None:
        """Test close duration match."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test",
            url="https://spotify.com/track/test",
        )
        result = DownloadResult(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=185,  # 5 second difference
            platform=TargetPlatform.YOUTUBE,
            platform_id="yt",
            url="https://youtube.com/watch?v=yt",
        )
        score = calc_time_match(song, result)
        assert score > 60.0  # Should be fairly high

    def test_calc_time_match_different(self) -> None:
        """Test different duration match."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test",
            url="https://spotify.com/track/test",
        )
        result = DownloadResult(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=300,  # 2 minute difference
            platform=TargetPlatform.YOUTUBE,
            platform_id="yt",
            url="https://youtube.com/watch?v=yt",
        )
        score = calc_time_match(song, result)
        assert score < 30.0  # Should be low

    def test_calc_album_match_exact(
        self, exact_match_song: Song, exact_match_result: DownloadResult
    ) -> None:
        """Test exact album match."""
        score = calc_album_match(exact_match_song, exact_match_result)
        assert score == 100.0

    def test_calc_album_match_no_album(self) -> None:
        """Test album match with no album."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test",
            url="https://spotify.com/track/test",
        )
        result = DownloadResult(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="yt",
            url="https://youtube.com/watch?v=yt",
        )
        score = calc_album_match(song, result)
        assert score == 0.0

    def test_calc_main_artist_match_exact(
        self, exact_match_song: Song, exact_match_result: DownloadResult
    ) -> None:
        """Test exact artist match."""
        score = calc_main_artist_match(exact_match_song, exact_match_result)
        assert score == 100.0

    def test_calc_artists_match_single_artist(
        self, exact_match_song: Song, exact_match_result: DownloadResult
    ) -> None:
        """Test artists match with single artist."""
        score = calc_artists_match(exact_match_song, exact_match_result)
        assert score == 0.0  # Single artist, no secondary match


class TestOrderResults:
    """Tests for order_results function."""

    @pytest.fixture
    def song(self) -> Song:
        """Create a test song."""
        return Song(
            name="Blinding Lights",
            artists=["The Weeknd"],
            artist="The Weeknd",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="blinding",
            url="https://spotify.com/track/blinding",
            album_name="After Hours",
        )

    def test_order_results_best_match(self, song: Song) -> None:
        """Test ordering with best match first."""
        results = [
            DownloadResult(
                name="Blinding Lights",
                artists=["The Weeknd"],
                artist="The Weeknd",
                duration=200,
                platform=TargetPlatform.YOUTUBE,
                platform_id="best",
                url="https://youtube.com/watch?v=best",
                verified=True,
            ),
            DownloadResult(
                name="Blinding Lights (Remix)",
                artists=["The Weeknd"],
                artist="The Weeknd",
                duration=220,
                platform=TargetPlatform.YOUTUBE,
                platform_id="remix",
                url="https://youtube.com/watch?v=remix",
            ),
        ]

        scored = order_results(results, song)

        assert len(scored) >= 1
        # Best match should have highest score
        best = max(scored.items(), key=lambda x: x[1])
        assert best[0].platform_id == "best"

    def test_order_results_filters_unrelated(self, song: Song) -> None:
        """Test that unrelated results are filtered out."""
        results = [
            DownloadResult(
                name="Completely Different Song",
                artists=["Random Artist"],
                artist="Random Artist",
                duration=300,
                platform=TargetPlatform.YOUTUBE,
                platform_id="diff",
                url="https://youtube.com/watch?v=diff",
            ),
        ]

        scored = order_results(results, song)
        assert len(scored) == 0  # Should be filtered


class TestGetBestMatches:
    """Tests for get_best_matches function."""

    def test_get_best_matches_empty(self) -> None:
        """Test with empty results."""
        matches = get_best_matches({})
        assert matches == []

    def test_get_best_matches_single(self) -> None:
        """Test with single result."""
        result = DownloadResult(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="test",
            url="https://youtube.com/watch?v=test",
        )

        matches = get_best_matches({result: 90.0})
        assert len(matches) == 1
        assert matches[0][1] == 90.0

    def test_get_best_matches_within_threshold(self) -> None:
        """Test that results within threshold are returned."""
        result1 = DownloadResult(
            name="Test1",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="test1",
            url="https://youtube.com/watch?v=test1",
        )
        result2 = DownloadResult(
            name="Test2",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="test2",
            url="https://youtube.com/watch?v=test2",
        )

        # Both within 5.0 threshold of best (90.0)
        matches = get_best_matches({result1: 90.0, result2: 87.0}, score_threshold=5.0)
        assert len(matches) == 2

    def test_get_best_matches_outside_threshold(self) -> None:
        """Test that results outside threshold are excluded."""
        result1 = DownloadResult(
            name="Test1",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="test1",
            url="https://youtube.com/watch?v=test1",
        )
        result2 = DownloadResult(
            name="Test2",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="test2",
            url="https://youtube.com/watch?v=test2",
        )

        # result2 is outside 5.0 threshold of best (90.0)
        matches = get_best_matches({result1: 90.0, result2: 70.0}, score_threshold=5.0)
        assert len(matches) == 1
        assert matches[0][0].platform_id == "test1"


class TestGetBestResult:
    """Tests for get_best_result function."""

    @pytest.fixture
    def song(self) -> Song:
        """Create a test song."""
        return Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test",
            url="https://spotify.com/track/test",
        )

    def test_get_best_result_found(self, song: Song) -> None:
        """Test finding best result."""
        results = [
            DownloadResult(
                name="Test Song",
                artists=["Test Artist"],
                artist="Test Artist",
                duration=180,
                platform=TargetPlatform.YOUTUBE,
                platform_id="best",
                url="https://youtube.com/watch?v=best",
                verified=True,
            ),
        ]

        result = get_best_result(results, song, min_score=70.0)
        assert result is not None
        assert result[0].platform_id == "best"

    def test_get_best_result_below_threshold(self, song: Song) -> None:
        """Test that low scores are rejected."""
        results = [
            DownloadResult(
                name="Different Song",
                artists=["Different Artist"],
                artist="Different Artist",
                duration=300,
                platform=TargetPlatform.YOUTUBE,
                platform_id="diff",
                url="https://youtube.com/watch?v=diff",
            ),
        ]

        result = get_best_result(results, song, min_score=80.0)
        assert result is None

    def test_get_best_result_empty(self, song: Song) -> None:
        """Test with no results."""
        result = get_best_result([], song)
        assert result is None
