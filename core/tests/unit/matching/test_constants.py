"""Unit tests for matching constants."""

from __future__ import annotations

from spotdl_core.matching.constants import (
    EXPLICIT_MISMATCH_PENALTY,
    FORBIDDEN_WORD_PENALTY,
    FORBIDDEN_WORDS,
    HIGH_MATCH_THRESHOLD,
    ISRC_MATCH_THRESHOLD,
    MIN_ARTIST_MATCH,
    MIN_NAME_MATCH,
    MIN_TIME_MATCH,
)


class TestForbiddenWords:
    """Test FORBIDDEN_WORDS constant."""

    def test_forbidden_words_is_list(self):
        """Test FORBIDDEN_WORDS is a list."""
        assert isinstance(FORBIDDEN_WORDS, list)

    def test_forbidden_words_not_empty(self):
        """Test FORBIDDEN_WORDS is not empty."""
        assert len(FORBIDDEN_WORDS) > 0

    def test_forbidden_words_all_lowercase(self):
        """Test all forbidden words are lowercase."""
        for word in FORBIDDEN_WORDS:
            assert word == word.lower()

    def test_forbidden_words_all_strings(self):
        """Test all forbidden words are strings."""
        for word in FORBIDDEN_WORDS:
            assert isinstance(word, str)

    def test_forbidden_words_no_spaces(self):
        """Test forbidden words contain no spaces."""
        for word in FORBIDDEN_WORDS:
            assert " " not in word

    def test_forbidden_words_contains_remix(self):
        """Test FORBIDDEN_WORDS contains 'remix'."""
        assert "remix" in FORBIDDEN_WORDS

    def test_forbidden_words_contains_live(self):
        """Test FORBIDDEN_WORDS contains 'live'."""
        assert "live" in FORBIDDEN_WORDS

    def test_forbidden_words_contains_acoustic(self):
        """Test FORBIDDEN_WORDS contains 'acoustic'."""
        assert "acoustic" in FORBIDDEN_WORDS

    def test_forbidden_words_contains_cover(self):
        """Test FORBIDDEN_WORDS contains 'cover'."""
        assert "cover" in FORBIDDEN_WORDS

    def test_forbidden_words_contains_instrumental(self):
        """Test FORBIDDEN_WORDS contains 'instrumental'."""
        assert "instrumental" in FORBIDDEN_WORDS

    def test_forbidden_words_contains_remaster(self):
        """Test FORBIDDEN_WORDS contains remaster variants."""
        assert "remaster" in FORBIDDEN_WORDS or "remastered" in FORBIDDEN_WORDS

    def test_forbidden_words_no_duplicates(self):
        """Test FORBIDDEN_WORDS contains no duplicates."""
        assert len(FORBIDDEN_WORDS) == len(set(FORBIDDEN_WORDS))

    def test_forbidden_words_specific_versions(self):
        """Test FORBIDDEN_WORDS contains specific version indicators."""
        expected_words = ["remix", "live", "acoustic", "cover", "instrumental"]
        for word in expected_words:
            assert word in FORBIDDEN_WORDS


class TestMinThresholds:
    """Test minimum threshold constants."""

    def test_min_name_match_is_float(self):
        """Test MIN_NAME_MATCH is a float."""
        assert isinstance(MIN_NAME_MATCH, float)

    def test_min_name_match_in_range(self):
        """Test MIN_NAME_MATCH is between 0 and 100."""
        assert 0.0 <= MIN_NAME_MATCH <= 100.0

    def test_min_name_match_value(self):
        """Test MIN_NAME_MATCH has expected value."""
        assert MIN_NAME_MATCH == 60.0

    def test_min_artist_match_is_float(self):
        """Test MIN_ARTIST_MATCH is a float."""
        assert isinstance(MIN_ARTIST_MATCH, float)

    def test_min_artist_match_in_range(self):
        """Test MIN_ARTIST_MATCH is between 0 and 100."""
        assert 0.0 <= MIN_ARTIST_MATCH <= 100.0

    def test_min_artist_match_value(self):
        """Test MIN_ARTIST_MATCH has expected value."""
        assert MIN_ARTIST_MATCH == 70.0

    def test_min_time_match_is_float(self):
        """Test MIN_TIME_MATCH is a float."""
        assert isinstance(MIN_TIME_MATCH, float)

    def test_min_time_match_in_range(self):
        """Test MIN_TIME_MATCH is between 0 and 100."""
        assert 0.0 <= MIN_TIME_MATCH <= 100.0

    def test_min_time_match_value(self):
        """Test MIN_TIME_MATCH has expected value."""
        assert MIN_TIME_MATCH == 25.0

    def test_artist_threshold_higher_than_name(self):
        """Test MIN_ARTIST_MATCH is higher than MIN_NAME_MATCH."""
        assert MIN_ARTIST_MATCH > MIN_NAME_MATCH

    def test_time_threshold_lower_than_others(self):
        """Test MIN_TIME_MATCH is lower than other thresholds."""
        assert MIN_TIME_MATCH < MIN_NAME_MATCH
        assert MIN_TIME_MATCH < MIN_ARTIST_MATCH


class TestPenalties:
    """Test penalty constants."""

    def test_forbidden_word_penalty_is_float(self):
        """Test FORBIDDEN_WORD_PENALTY is a float."""
        assert isinstance(FORBIDDEN_WORD_PENALTY, float)

    def test_forbidden_word_penalty_positive(self):
        """Test FORBIDDEN_WORD_PENALTY is positive."""
        assert FORBIDDEN_WORD_PENALTY > 0.0

    def test_forbidden_word_penalty_value(self):
        """Test FORBIDDEN_WORD_PENALTY has expected value."""
        assert FORBIDDEN_WORD_PENALTY == 15.0

    def test_explicit_mismatch_penalty_is_float(self):
        """Test EXPLICIT_MISMATCH_PENALTY is a float."""
        assert isinstance(EXPLICIT_MISMATCH_PENALTY, float)

    def test_explicit_mismatch_penalty_positive(self):
        """Test EXPLICIT_MISMATCH_PENALTY is positive."""
        assert EXPLICIT_MISMATCH_PENALTY > 0.0

    def test_explicit_mismatch_penalty_value(self):
        """Test EXPLICIT_MISMATCH_PENALTY has expected value."""
        assert EXPLICIT_MISMATCH_PENALTY == 5.0

    def test_forbidden_word_penalty_higher_than_explicit(self):
        """Test FORBIDDEN_WORD_PENALTY is higher than EXPLICIT_MISMATCH_PENALTY."""
        assert FORBIDDEN_WORD_PENALTY > EXPLICIT_MISMATCH_PENALTY


class TestMatchThresholds:
    """Test match threshold constants."""

    def test_high_match_threshold_is_float(self):
        """Test HIGH_MATCH_THRESHOLD is a float."""
        assert isinstance(HIGH_MATCH_THRESHOLD, float)

    def test_high_match_threshold_in_range(self):
        """Test HIGH_MATCH_THRESHOLD is between 0 and 100."""
        assert 0.0 <= HIGH_MATCH_THRESHOLD <= 100.0

    def test_high_match_threshold_value(self):
        """Test HIGH_MATCH_THRESHOLD has expected value."""
        assert HIGH_MATCH_THRESHOLD == 85.0

    def test_isrc_match_threshold_is_float(self):
        """Test ISRC_MATCH_THRESHOLD is a float."""
        assert isinstance(ISRC_MATCH_THRESHOLD, float)

    def test_isrc_match_threshold_in_range(self):
        """Test ISRC_MATCH_THRESHOLD is between 0 and 100."""
        assert 0.0 <= ISRC_MATCH_THRESHOLD <= 100.0

    def test_isrc_match_threshold_value(self):
        """Test ISRC_MATCH_THRESHOLD has expected value."""
        assert ISRC_MATCH_THRESHOLD == 80.0

    def test_high_threshold_above_min_thresholds(self):
        """Test HIGH_MATCH_THRESHOLD is above minimum thresholds."""
        assert HIGH_MATCH_THRESHOLD > MIN_NAME_MATCH
        assert HIGH_MATCH_THRESHOLD > MIN_ARTIST_MATCH
        assert HIGH_MATCH_THRESHOLD > MIN_TIME_MATCH

    def test_isrc_threshold_above_min_thresholds(self):
        """Test ISRC_MATCH_THRESHOLD is above minimum thresholds."""
        assert ISRC_MATCH_THRESHOLD > MIN_NAME_MATCH
        assert ISRC_MATCH_THRESHOLD > MIN_ARTIST_MATCH
        assert ISRC_MATCH_THRESHOLD > MIN_TIME_MATCH


class TestConstantsRelationships:
    """Test relationships between constants."""

    def test_penalty_wont_fail_match(self):
        """Test penalties won't cause matches to fail thresholds alone."""
        # Single forbidden word shouldn't drop below min threshold
        assert 100.0 - FORBIDDEN_WORD_PENALTY > MIN_NAME_MATCH

    def test_thresholds_allow_reasonable_matches(self):
        """Test thresholds allow reasonable matches to pass."""
        # Perfect match minus explicit penalty should still pass
        assert 100.0 - EXPLICIT_MISMATCH_PENALTY > MIN_NAME_MATCH
        assert 100.0 - EXPLICIT_MISMATCH_PENALTY > MIN_ARTIST_MATCH

    def test_high_threshold_is_strict(self):
        """Test HIGH_MATCH_THRESHOLD represents a strict requirement."""
        assert HIGH_MATCH_THRESHOLD >= 80.0

    def test_time_threshold_is_lenient(self):
        """Test MIN_TIME_MATCH is lenient."""
        assert MIN_TIME_MATCH <= 30.0

    def test_all_thresholds_achievable(self):
        """Test all thresholds are achievable (not above 100)."""
        assert MIN_NAME_MATCH < 100.0
        assert MIN_ARTIST_MATCH < 100.0
        assert MIN_TIME_MATCH < 100.0
        assert HIGH_MATCH_THRESHOLD < 100.0
        assert ISRC_MATCH_THRESHOLD < 100.0


class TestConstantsTypes:
    """Test all constants have correct types."""

    def test_all_numeric_constants_are_floats(self):
        """Test all numeric constants are floats."""
        numeric_constants = [
            MIN_NAME_MATCH,
            MIN_ARTIST_MATCH,
            MIN_TIME_MATCH,
            FORBIDDEN_WORD_PENALTY,
            EXPLICIT_MISMATCH_PENALTY,
            HIGH_MATCH_THRESHOLD,
            ISRC_MATCH_THRESHOLD,
        ]
        for constant in numeric_constants:
            assert isinstance(constant, float)

    def test_forbidden_words_is_list_of_strings(self):
        """Test FORBIDDEN_WORDS is a list of strings."""
        assert isinstance(FORBIDDEN_WORDS, list)
        for word in FORBIDDEN_WORDS:
            assert isinstance(word, str)
            assert len(word) > 0


class TestConstantsImmutability:
    """Test constants should not be modified."""

    def test_forbidden_words_comprehensive(self):
        """Test FORBIDDEN_WORDS covers common variations."""
        # Should contain at least these common variations
        common_variations = ["remix", "live", "acoustic", "cover"]
        for variation in common_variations:
            assert variation in FORBIDDEN_WORDS

    def test_constants_reasonable_values(self):
        """Test all constants have reasonable values."""
        # Thresholds should be between 0 and 100
        assert 0 < MIN_NAME_MATCH < 100
        assert 0 < MIN_ARTIST_MATCH < 100
        assert 0 < MIN_TIME_MATCH < 100
        assert 0 < HIGH_MATCH_THRESHOLD < 100
        assert 0 < ISRC_MATCH_THRESHOLD < 100

        # Penalties should be positive but not excessive
        assert 0 < FORBIDDEN_WORD_PENALTY < 50
        assert 0 < EXPLICIT_MISMATCH_PENALTY < 50
