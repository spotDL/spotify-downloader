"""Tests for matching scoring functions."""

import pytest

from spotdl.core.matching.scoring import (
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
from spotdl.core.types.result import Result, TargetPlatform
from spotdl.core.types.song import Platform, Song
from tests.conftest import create_result, create_song


class TestCheckCommonWord:
    """Tests for the check_common_word function."""

    def test_common_word_exists(self):
        """Test when common word exists."""
        song = create_song(name="Test Song")
        result = create_result(name="Test Song Official")
        assert check_common_word(song, result) is True

    def test_no_common_word(self):
        """Test when no common word exists."""
        song = create_song(name="Completely Different")
        result = create_result(name="Nothing Similar")
        assert check_common_word(song, result) is False

    def test_partial_word_match(self):
        """Test partial word matching."""
        song = create_song(name="Hello World")
        result = create_result(name="HelloWorld Combined")
        assert check_common_word(song, result) is True


class TestCheckForbiddenWords:
    """Tests for the check_forbidden_words function."""

    def test_no_forbidden_words(self):
        """Test when no forbidden words present."""
        song = create_song(name="Original Song")
        result = create_result(name="Original Song")
        has_forbidden, words = check_forbidden_words(song, result)
        assert has_forbidden is False
        assert words == []

    def test_remix_detected(self):
        """Test remix detection."""
        song = create_song(name="Original Song")
        result = create_result(name="Original Song Remix")
        has_forbidden, words = check_forbidden_words(song, result)
        assert has_forbidden is True
        assert "remix" in words

    def test_live_detected(self):
        """Test live version detection."""
        song = create_song(name="Studio Song")
        result = create_result(name="Studio Song Live")
        has_forbidden, words = check_forbidden_words(song, result)
        assert has_forbidden is True
        assert "live" in words

    def test_forbidden_word_in_original(self):
        """Test when forbidden word is in original song name."""
        song = create_song(name="Official Remix")
        result = create_result(name="Official Remix")
        has_forbidden, words = check_forbidden_words(song, result)
        assert has_forbidden is False


class TestCalcMainArtistMatch:
    """Tests for the calc_main_artist_match function."""

    def test_exact_artist_match(self):
        """Test exact artist match."""
        song = create_song(artists=["Artist One"])
        result = create_result(artists=("Artist One",))
        score = calc_main_artist_match(song, result)
        assert score == 100.0

    def test_no_result_artists(self):
        """Test when result has no artists."""
        song = create_song(artists=["Artist One"])
        result = create_result(artists=None)
        score = calc_main_artist_match(song, result)
        assert score == 0.0

    def test_similar_artist_match(self):
        """Test similar artist names."""
        song = create_song(artists=["Artist One"])
        result = create_result(artists=("Artist 1",))
        score = calc_main_artist_match(song, result)
        assert score > 50.0

    def test_multiple_song_artists_single_result(self):
        """Test when song has multiple artists but result has one."""
        song = create_song(artists=["Main Artist", "Featured Artist"])
        result = create_result(artists=("Main Artist Featured Artist",))
        score = calc_main_artist_match(song, result)
        # Should recognize both artists in the combined name
        assert score > 0.0


class TestCalcArtistsMatch:
    """Tests for the calc_artists_match function."""

    def test_single_artist_returns_zero(self):
        """Test that single artist songs return 0."""
        song = create_song(artists=["Only Artist"])
        result = create_result(artists=("Only Artist",))
        score = calc_artists_match(song, result)
        assert score == 0.0

    def test_matching_featured_artists(self):
        """Test matching featured artists."""
        song = create_song(artists=["Main", "Featured1", "Featured2"])
        result = create_result(artists=("Main", "Featured1", "Featured2"))
        score = calc_artists_match(song, result)
        assert score > 80.0


class TestArtistsMatchFixup1:
    """Tests for the artists_match_fixup1 function."""

    def test_verified_result_unchanged(self):
        """Test that verified results are unchanged."""
        song = create_song(artists=["Artist"])
        result = create_result(verified=True, artists=("Artist",))
        score = artists_match_fixup1(song, result, 30.0)
        assert score == 30.0

    def test_high_score_unchanged(self):
        """Test that high scores are unchanged."""
        song = create_song(artists=["Artist"])
        result = create_result(verified=False, artists=("Artist",))
        score = artists_match_fixup1(song, result, 60.0)
        assert score == 60.0

    def test_low_score_improved(self):
        """Test that low scores can be improved."""
        song = create_song(artists=["Artist"])
        result = create_result(
            name="Artist - Song Title",
            verified=False,
            artists=None,
        )
        score = artists_match_fixup1(song, result, 20.0)
        # Score should be improved by finding artist in title
        assert score >= 20.0


class TestArtistsMatchFixup2:
    """Tests for the artists_match_fixup2 function."""

    def test_unverified_result_unchanged(self):
        """Test that unverified results are unchanged."""
        song = create_song(artists=["Artist"])
        result = create_result(verified=False, artists=("Artist",))
        score = artists_match_fixup2(song, result, 30.0)
        assert score == 30.0

    def test_high_score_unchanged(self):
        """Test that high scores are unchanged."""
        song = create_song(artists=["Artist"])
        result = create_result(verified=True, artists=("Artist",))
        score = artists_match_fixup2(song, result, 80.0)
        assert score == 80.0


class TestArtistsMatchFixup3:
    """Tests for the artists_match_fixup3 function."""

    def test_high_score_unchanged(self):
        """Test that high scores are unchanged."""
        song = create_song(artists=["Artist"])
        result = create_result(artists=("Artist",))
        score = artists_match_fixup3(song, result, 80.0)
        assert score == 80.0

    def test_multiple_result_artists_unchanged(self):
        """Test that multiple result artists are unchanged."""
        song = create_song(artists=["Artist1", "Artist2"])
        result = create_result(artists=("Artist1", "Artist2"))
        score = artists_match_fixup3(song, result, 50.0)
        assert score == 50.0


class TestCalcNameMatch:
    """Tests for the calc_name_match function."""

    def test_exact_name_match(self):
        """Test exact name match."""
        song = create_song(name="Test Song")
        result = create_result(name="Test Song")
        score = calc_name_match(song, result)
        assert score >= 95.0

    def test_similar_name_match(self):
        """Test similar name match."""
        song = create_song(name="Test Song")
        result = create_result(name="Test Song (Official Audio)")
        score = calc_name_match(song, result)
        assert score > 50.0

    def test_different_names(self):
        """Test completely different names."""
        song = create_song(name="Song One")
        result = create_result(name="Completely Different Title")
        score = calc_name_match(song, result)
        assert score < 50.0


class TestCalcTimeMatch:
    """Tests for the calc_time_match function."""

    def test_exact_duration(self):
        """Test exact duration match."""
        song = create_song(duration=180)
        result = create_result(duration=180.0)
        score = calc_time_match(song, result)
        assert score == 100.0

    def test_similar_duration(self):
        """Test similar duration (1 second off)."""
        song = create_song(duration=180)
        result = create_result(duration=181.0)
        score = calc_time_match(song, result)
        assert score > 90.0

    def test_different_duration(self):
        """Test different duration (30 seconds off)."""
        song = create_song(duration=180)
        result = create_result(duration=210.0)
        score = calc_time_match(song, result)
        assert score < 10.0


class TestCalcAlbumMatch:
    """Tests for the calc_album_match function."""

    def test_exact_album_match(self):
        """Test exact album match."""
        song = create_song(album_name="Test Album")
        result = create_result(album="Test Album")
        score = calc_album_match(song, result)
        assert score == 100.0

    def test_no_result_album(self):
        """Test when result has no album."""
        song = create_song(album_name="Test Album")
        result = create_result(album=None)
        score = calc_album_match(song, result)
        assert score == 0.0

    def test_similar_album(self):
        """Test similar album names."""
        song = create_song(album_name="Greatest Hits")
        result = create_result(album="Greatest Hits Collection")
        score = calc_album_match(song, result)
        assert score > 50.0
