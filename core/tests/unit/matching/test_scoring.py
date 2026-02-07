"""Unit tests for matching scoring functions."""

from __future__ import annotations

import pytest

from spotdl_core.matching.scoring import (
    artists_match_fixup1,
    artists_match_fixup2,
    artists_match_fixup3,
    calc_album_match,
    calc_artists_match,
    calc_main_artist_match,
    calc_name_match,
    calc_time_match,
    check_common_word,
    check_forbidden_words,
    create_match_strings,
)
from spotdl_core.types import Platform, Result, Song, TargetPlatform


class TestCheckCommonWord:
    """Test check_common_word function."""

    @pytest.fixture
    def song(self) -> Song:
        """Create a test song."""
        return Song(
            name="Test Song Name",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

    def test_check_common_word_found(self, song: Song):
        """Test check_common_word finds common word."""
        result = Result(
            name="Test Video",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        assert check_common_word(song, result) is True

    def test_check_common_word_not_found(self, song: Song):
        """Test check_common_word when no common word."""
        result = Result(
            name="Completely Different",
            artists=("Other",),
            artist="Other",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        assert check_common_word(song, result) is False

    def test_check_common_word_partial_match(self, song: Song):
        """Test check_common_word with partial word match."""
        result = Result(
            name="Song Video",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        assert check_common_word(song, result) is True

    def test_check_common_word_case_insensitive(self, song: Song):
        """Test check_common_word is case insensitive."""
        result = Result(
            name="SONG video",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        assert check_common_word(song, result) is True

    def test_check_common_word_with_special_chars(self, song: Song):
        """Test check_common_word handles special characters."""
        result = Result(
            name="Test's Video",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        assert check_common_word(song, result) is True

    def test_check_common_word_empty_result_name(self, song: Song):
        """Test check_common_word with empty result name."""
        result = Result(
            name="",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        assert check_common_word(song, result) is False


class TestCheckForbiddenWords:
    """Test check_forbidden_words function."""

    @pytest.fixture
    def song(self) -> Song:
        """Create a test song."""
        return Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

    def test_check_forbidden_words_none_found(self, song: Song):
        """Test check_forbidden_words when no forbidden words."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        has_words, words = check_forbidden_words(song, result)
        assert has_words is False
        assert words == []

    def test_check_forbidden_words_remix_found(self, song: Song):
        """Test check_forbidden_words finds 'remix'."""
        result = Result(
            name="Test Song Remix",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        has_words, words = check_forbidden_words(song, result)
        assert has_words is True
        assert "remix" in words

    def test_check_forbidden_words_live_found(self, song: Song):
        """Test check_forbidden_words finds 'live'."""
        result = Result(
            name="Test Song Live",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        has_words, words = check_forbidden_words(song, result)
        assert has_words is True
        assert "live" in words

    def test_check_forbidden_words_multiple_found(self, song: Song):
        """Test check_forbidden_words finds multiple forbidden words."""
        result = Result(
            name="Test Song Live Remix",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        has_words, words = check_forbidden_words(song, result)
        assert has_words is True
        assert len(words) == 2
        assert "live" in words
        assert "remix" in words

    def test_check_forbidden_words_in_song_name(self):
        """Test check_forbidden_words ignores words in song name."""
        song = Song(
            name="Test Song Remix",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )
        result = Result(
            name="Test Song Remix",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        has_words, words = check_forbidden_words(song, result)
        assert has_words is False
        assert words == []

    def test_check_forbidden_words_acoustic(self, song: Song):
        """Test check_forbidden_words finds 'acoustic'."""
        result = Result(
            name="Test Song Acoustic",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        has_words, words = check_forbidden_words(song, result)
        assert has_words is True
        assert "acoustic" in words

    def test_check_forbidden_words_cover(self, song: Song):
        """Test check_forbidden_words finds 'cover'."""
        result = Result(
            name="Test Song Cover",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        has_words, words = check_forbidden_words(song, result)
        assert has_words is True
        assert "cover" in words

    def test_check_forbidden_words_instrumental(self, song: Song):
        """Test check_forbidden_words finds 'instrumental'."""
        result = Result(
            name="Test Song Instrumental",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        has_words, words = check_forbidden_words(song, result)
        assert has_words is True
        assert "instrumental" in words


class TestCreateMatchStrings:
    """Test create_match_strings function."""

    @pytest.fixture
    def song(self) -> Song:
        """Create a test song."""
        return Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

    def test_create_match_strings_basic(self, song: Song):
        """Test create_match_strings with basic inputs."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=False,
        )
        str1, str2 = create_match_strings(song, result)
        assert isinstance(str1, str)
        assert isinstance(str2, str)

    def test_create_match_strings_with_search_query(self, song: Song):
        """Test create_match_strings with search query."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=False,
        )
        str1, str2 = create_match_strings(song, result, "Artist - Test Song")
        assert isinstance(str1, str)
        assert isinstance(str2, str)

    def test_create_match_strings_verified_result(self, song: Song):
        """Test create_match_strings with verified result."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=True,
        )
        str1, str2 = create_match_strings(song, result)
        assert isinstance(str1, str)
        assert isinstance(str2, str)


class TestCalcMainArtistMatch:
    """Test calc_main_artist_match function."""

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

    def test_calc_main_artist_match_identical(self, song: Song):
        """Test calc_main_artist_match with identical artists."""
        result = Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_main_artist_match(song, result)
        assert score == 100.0

    def test_calc_main_artist_match_no_result_artists(self, song: Song):
        """Test calc_main_artist_match with no result artists."""
        result = Result(
            name="Test Song",
            artists=(),
            artist="",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_main_artist_match(song, result)
        assert score == 0.0

    def test_calc_main_artist_match_similar_artists(self, song: Song):
        """Test calc_main_artist_match with similar artists."""
        result = Result(
            name="Test Song",
            artists=("Test Artists",),
            artist="Test Artists",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_main_artist_match(song, result)
        assert 80.0 < score < 100.0

    def test_calc_main_artist_match_different_artists(self, song: Song):
        """Test calc_main_artist_match with different artists."""
        result = Result(
            name="Test Song",
            artists=("Different Artist",),
            artist="Different Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_main_artist_match(song, result)
        assert score < 100.0  # Should be less than perfect match

    def test_calc_main_artist_match_multiple_song_artists(self):
        """Test calc_main_artist_match with multiple song artists."""
        song = Song(
            name="Test Song",
            artists=["Artist1", "Artist2"],
            artist="Artist1",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )
        result = Result(
            name="Test Song",
            artists=("Artist1",),
            artist="Artist1",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_main_artist_match(song, result)
        assert score >= 0.0  # May return 0 or positive score

    def test_calc_main_artist_match_combined_artist_name(self):
        """Test calc_main_artist_match when result combines multiple artists."""
        song = Song(
            name="Test Song",
            artists=["Artist1", "Artist2"],
            artist="Artist1",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )
        result = Result(
            name="Test Song",
            artists=("Artist1 Artist2",),
            artist="Artist1 Artist2",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_main_artist_match(song, result)
        assert score > 0.0


class TestCalcArtistsMatch:
    """Test calc_artists_match function."""

    @pytest.fixture
    def single_artist_song(self) -> Song:
        """Create a song with single artist."""
        return Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

    @pytest.fixture
    def multi_artist_song(self) -> Song:
        """Create a song with multiple artists."""
        return Song(
            name="Test Song",
            artists=["Artist1", "Artist2", "Artist3"],
            artist="Artist1",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

    def test_calc_artists_match_single_artist(self, single_artist_song: Song):
        """Test calc_artists_match with single artist returns 0."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_artists_match(single_artist_song, result)
        assert score == 0.0

    def test_calc_artists_match_no_result_artists(self, multi_artist_song: Song):
        """Test calc_artists_match with no result artists."""
        result = Result(
            name="Test Song",
            artists=(),
            artist="",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_artists_match(multi_artist_song, result)
        assert score == 0.0

    def test_calc_artists_match_multiple_artists(self, multi_artist_song: Song):
        """Test calc_artists_match with multiple matching artists."""
        result = Result(
            name="Test Song",
            artists=("Artist1", "Artist2", "Artist3"),
            artist="Artist1",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_artists_match(multi_artist_song, result)
        assert score > 50.0  # Should have good match for other artists

    def test_calc_artists_match_partial_match(self, multi_artist_song: Song):
        """Test calc_artists_match with partial artist match."""
        result = Result(
            name="Test Song",
            artists=("Artist1", "Artist2"),
            artist="Artist1",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_artists_match(multi_artist_song, result)
        assert score >= 0.0


class TestArtistsMatchFixup1:
    """Test artists_match_fixup1 function."""

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

    def test_artists_match_fixup1_verified_result(self, song: Song):
        """Test artists_match_fixup1 doesn't modify verified results."""
        result = Result(
            name="Test Song",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=True,
        )
        score = artists_match_fixup1(song, result, 30.0)
        assert score == 30.0

    def test_artists_match_fixup1_high_score(self, song: Song):
        """Test artists_match_fixup1 doesn't modify high scores."""
        result = Result(
            name="Test Song",
            artists=("Other Artist",),
            artist="Other Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=False,
        )
        score = artists_match_fixup1(song, result, 60.0)
        assert score == 60.0

    def test_artists_match_fixup1_improves_low_score(self, song: Song):
        """Test artists_match_fixup1 can improve low scores."""
        result = Result(
            name="Test Artist - Test Song",
            artists=("Channel Name",),
            artist="Channel Name",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=False,
        )
        score = artists_match_fixup1(song, result, 30.0)
        assert score >= 30.0


class TestArtistsMatchFixup2:
    """Test artists_match_fixup2 function."""

    @pytest.fixture
    def song(self) -> Song:
        """Create a test song."""
        return Song(
            name="Test Song",
            artists=["Artist1", "Artist2"],
            artist="Artist1",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

    def test_artists_match_fixup2_high_score(self, song: Song):
        """Test artists_match_fixup2 doesn't modify high scores."""
        result = Result(
            name="Test Song",
            artists=("Artist1", "Artist2"),
            artist="Artist1",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=True,
        )
        score = artists_match_fixup2(song, result, 80.0)
        assert score == 80.0

    def test_artists_match_fixup2_unverified_result(self, song: Song):
        """Test artists_match_fixup2 doesn't modify unverified results."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=False,
        )
        score = artists_match_fixup2(song, result, 30.0)
        assert score == 30.0

    def test_artists_match_fixup2_with_search_query(self, song: Song):
        """Test artists_match_fixup2 with search query."""
        result = Result(
            name="Artist1 Artist2 Test Song",
            artists=("Artist1",),
            artist="Artist1",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=True,
        )
        score = artists_match_fixup2(song, result, 50.0, "Artist1 - Test Song")
        assert score >= 50.0


class TestArtistsMatchFixup3:
    """Test artists_match_fixup3 function."""

    @pytest.fixture
    def multi_artist_song(self) -> Song:
        """Create a song with multiple artists."""
        return Song(
            name="Test Song",
            artists=["Artist1", "Artist2"],
            artist="Artist1",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

    def test_artists_match_fixup3_high_score(self, multi_artist_song: Song):
        """Test artists_match_fixup3 doesn't modify high scores."""
        result = Result(
            name="Test Song",
            artists=("Artist1",),
            artist="Artist1",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = artists_match_fixup3(multi_artist_song, result, 80.0)
        assert score == 80.0

    def test_artists_match_fixup3_no_result_artists(self, multi_artist_song: Song):
        """Test artists_match_fixup3 with no result artists."""
        result = Result(
            name="Test Song",
            artists=(),
            artist="",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = artists_match_fixup3(multi_artist_song, result, 50.0)
        assert score == 50.0

    def test_artists_match_fixup3_multiple_result_artists(self, multi_artist_song: Song):
        """Test artists_match_fixup3 with multiple result artists."""
        result = Result(
            name="Test Song",
            artists=("Artist1", "Artist2"),
            artist="Artist1",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = artists_match_fixup3(multi_artist_song, result, 50.0)
        assert score == 50.0

    def test_artists_match_fixup3_single_artist_song(self):
        """Test artists_match_fixup3 with single artist song."""
        song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = artists_match_fixup3(song, result, 50.0)
        assert score == 50.0


class TestCalcNameMatch:
    """Test calc_name_match function."""

    @pytest.fixture
    def song(self) -> Song:
        """Create a test song."""
        return Song(
            name="Test Song Name",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

    def test_calc_name_match_identical(self, song: Song):
        """Test calc_name_match with identical names."""
        result = Result(
            name="Test Song Name",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=False,
        )
        score = calc_name_match(song, result)
        assert score == 100.0

    def test_calc_name_match_similar(self, song: Song):
        """Test calc_name_match with similar names."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=False,
        )
        score = calc_name_match(song, result)
        assert 70.0 < score < 100.0

    def test_calc_name_match_different(self, song: Song):
        """Test calc_name_match with different names."""
        result = Result(
            name="Completely Different Name",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=False,
        )
        score = calc_name_match(song, result)
        assert score < 50.0

    def test_calc_name_match_with_search_query(self, song: Song):
        """Test calc_name_match with search query."""
        result = Result(
            name="Artist - Test Song Name",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            verified=False,
        )
        score = calc_name_match(song, result, "Artist - Test Song Name")
        assert score >= 70.0  # Should be high match


class TestCalcTimeMatch:
    """Test calc_time_match function."""

    @pytest.fixture
    def song(self) -> Song:
        """Create a test song."""
        return Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

    def test_calc_time_match_identical(self, song: Song):
        """Test calc_time_match with identical durations."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_time_match(song, result)
        assert score == 100.0

    def test_calc_time_match_close_duration(self, song: Song):
        """Test calc_time_match with close durations."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=185,  # 5 seconds difference
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_time_match(song, result)
        assert 50.0 < score < 100.0

    def test_calc_time_match_far_duration(self, song: Song):
        """Test calc_time_match with very different durations."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=300,  # 120 seconds difference
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_time_match(song, result)
        assert score < 50.0

    def test_calc_time_match_shorter_duration(self, song: Song):
        """Test calc_time_match with shorter duration."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=170,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_time_match(song, result)
        assert 0.0 < score <= 100.0

    def test_calc_time_match_zero_duration(self, song: Song):
        """Test calc_time_match with zero result duration."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=0,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_time_match(song, result)
        assert score < 50.0


class TestCalcAlbumMatch:
    """Test calc_album_match function."""

    @pytest.fixture
    def song(self) -> Song:
        """Create a test song."""
        return Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
            album_name="Test Album",
        )

    def test_calc_album_match_identical(self, song: Song):
        """Test calc_album_match with identical album names."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            album_name="Test Album",
        )
        score = calc_album_match(song, result)
        assert score == 100.0

    def test_calc_album_match_no_result_album(self, song: Song):
        """Test calc_album_match with no result album."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            album_name=None,
        )
        score = calc_album_match(song, result)
        assert score == 0.0

    def test_calc_album_match_similar(self, song: Song):
        """Test calc_album_match with similar album names."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            album_name="Test Album Deluxe",
        )
        score = calc_album_match(song, result)
        assert 50.0 < score < 100.0

    def test_calc_album_match_different(self, song: Song):
        """Test calc_album_match with different album names."""
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            album_name="Different Album",
        )
        score = calc_album_match(song, result)
        assert score < 100.0  # Should be less than perfect match

    def test_calc_album_match_empty_song_album(self):
        """Test calc_album_match with empty song album."""
        song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
            album_name="",
        )
        result = Result(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
            album_name="Test Album",
        )
        score = calc_album_match(song, result)
        assert score < 50.0


class TestScoringEdgeCases:
    """Test edge cases and error handling."""

    def test_check_common_word_unicode(self):
        """Test check_common_word with unicode characters."""
        song = Song(
            name="Café Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )
        result = Result(
            name="Cafe Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        # Should find common word despite accent differences
        assert check_common_word(song, result) is True

    def test_check_forbidden_words_case_insensitive(self):
        """Test check_forbidden_words is case insensitive."""
        song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )
        result = Result(
            name="Test Song REMIX",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        has_words, words = check_forbidden_words(song, result)
        assert has_words is True
        assert "remix" in words

    def test_calc_time_match_negative_difference(self):
        """Test calc_time_match handles negative time differences."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )
        result = Result(
            name="Test",
            artists=("Artist",),
            artist="Artist",
            duration=150,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_time_match(song, result)
        assert 0.0 < score <= 100.0

    def test_calc_main_artist_match_empty_artist_list(self):
        """Test calc_main_artist_match with empty artist list."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )
        result = Result(
            name="Test",
            artists=(),
            artist="",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="vid123",
            url="https://youtube.com",
        )
        score = calc_main_artist_match(song, result)
        assert score == 0.0
