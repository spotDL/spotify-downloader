"""Matching engine for offline mode (ported from backend)."""

from spotdl_cli.matching.constants import (
    FORBIDDEN_WORDS,
    MIN_ARTIST_MATCH,
    MIN_NAME_MATCH,
    MIN_TIME_MATCH,
)
from spotdl_cli.matching.engine import get_best_matches, get_best_result, order_results
from spotdl_cli.matching.scoring import (
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
)

__all__ = [
    "FORBIDDEN_WORDS",
    "MIN_ARTIST_MATCH",
    "MIN_NAME_MATCH",
    "MIN_TIME_MATCH",
    "artists_match_fixup1",
    "artists_match_fixup2",
    "artists_match_fixup3",
    "calc_album_match",
    "calc_artists_match",
    "calc_main_artist_match",
    "calc_name_match",
    "calc_time_match",
    "check_common_word",
    "check_forbidden_words",
    "get_best_matches",
    "get_best_result",
    "order_results",
]
