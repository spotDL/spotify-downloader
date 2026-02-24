"""Main matching engine for ordering and selecting best results."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from spotdl_core.matching.constants import (
    EXPLICIT_MISMATCH_PENALTY,
    FORBIDDEN_WORD_PENALTY,
    HIGH_MATCH_THRESHOLD,
    MIN_ARTIST_MATCH,
    MIN_NAME_MATCH,
    MIN_TIME_MATCH,
)
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
)
if TYPE_CHECKING:
    from spotdl_core.types.result import Result
    from spotdl_core.types.song import Song

logger = logging.getLogger(__name__)


def order_results(
    results: list[Result],
    song: Song,
    search_query: str | None = None,
    *,
    min_name_match: float | None = None,
    min_artist_match: float | None = None,
    min_time_match: float | None = None,
) -> dict[Result, float]:
    """
    Order results by match quality against a song.

    This is the main matching function that combines all scoring
    algorithms to produce a ranked list of results.

    Args:
        results: List of search results to evaluate
        song: Song to match against
        search_query: Optional search query used for the search
        min_name_match: Override for minimum name match threshold
        min_artist_match: Override for minimum artist match threshold
        min_time_match: Override for minimum time match threshold

    Returns:
        Dictionary mapping results to their match scores (0-100)
    """
    # Use provided thresholds or fall back to constants
    effective_min_name = min_name_match if min_name_match is not None else MIN_NAME_MATCH
    effective_min_artist = min_artist_match if min_artist_match is not None else MIN_ARTIST_MATCH
    effective_min_time = min_time_match if min_time_match is not None else MIN_TIME_MATCH

    links_with_match_value: dict[Result, float] = {}

    for result in results:
        logger.debug(
            "[%s|%s] Calculating match for %s",
            song.song_id,
            result.platform_id,
            result.url,
        )

        # Quick filter: skip results with no common words
        if not check_common_word(song, result):
            logger.debug(
                "[%s|%s] Skipping - no common words",
                song.song_id,
                result.platform_id,
            )
            continue

        # Calculate main artist match
        artists_match = calc_main_artist_match(song, result)
        logger.debug(
            "[%s|%s] Main artist match: %.2f",
            song.song_id,
            result.platform_id,
            artists_match,
        )

        # Calculate other artists match
        other_artists_match = calc_artists_match(song, result)
        logger.debug(
            "[%s|%s] Other artists match: %.2f",
            song.song_id,
            result.platform_id,
            other_artists_match,
        )

        artists_match += other_artists_match

        # Normalize artist match for multiple artists
        artists_match = artists_match / (2 if len(song.artists) > 1 else 1)
        logger.debug(
            "[%s|%s] Normalized artists match: %.2f",
            song.song_id,
            result.platform_id,
            artists_match,
        )

        # Apply artist match fixups
        artists_match = artists_match_fixup1(song, result, artists_match)
        artists_match = artists_match_fixup2(song, result, artists_match, search_query)
        artists_match = artists_match_fixup3(song, result, artists_match)
        logger.debug(
            "[%s|%s] Final artists match: %.2f",
            song.song_id,
            result.platform_id,
            artists_match,
        )

        # Calculate name match
        name_match = calc_name_match(song, result, search_query)
        logger.debug(
            "[%s|%s] Initial name match: %.2f",
            song.song_id,
            result.platform_id,
            name_match,
        )

        # Check for forbidden words and apply penalty
        contains_fwords, found_fwords = check_forbidden_words(song, result)
        if contains_fwords:
            name_match -= len(found_fwords) * FORBIDDEN_WORD_PENALTY
            logger.debug(
                "[%s|%s] Forbidden words penalty: %s",
                song.song_id,
                result.platform_id,
                found_fwords,
            )

        # Calculate album and time matches
        album_match = calc_album_match(song, result)
        time_match = calc_time_match(song, result)
        logger.debug(
            "[%s|%s] Album: %.2f, Time: %.2f",
            song.song_id,
            result.platform_id,
            album_match,
            time_match,
        )

        # Apply minimum thresholds
        if name_match <= effective_min_name:
            logger.debug(
                "[%s|%s] Skipping - name match %.2f <= %.2f",
                song.song_id,
                result.platform_id,
                name_match,
                effective_min_name,
            )
            continue

        if artists_match < effective_min_artist:
            logger.debug(
                "[%s|%s] Skipping - artist match %.2f < %.2f",
                song.song_id,
                result.platform_id,
                artists_match,
                effective_min_artist,
            )
            continue

        # Calculate average match
        average_match = (artists_match + name_match) / 2
        logger.debug(
            "[%s|%s] Average match: %.2f",
            song.song_id,
            result.platform_id,
            average_match,
        )

        # For verified results with album data but low album match,
        # factor in the album match
        if (
            result.verified
            and not result.isrc_search
            and result.album_name
            and album_match <= 80
        ):
            average_match = (average_match + album_match) / 2
            logger.debug(
                "[%s|%s] Average with album: %.2f",
                song.song_id,
                result.platform_id,
                average_match,
            )

        # Apply time match threshold
        if time_match < effective_min_time:
            logger.debug(
                "[%s|%s] Skipping - time match %.2f < %.2f",
                song.song_id,
                result.platform_id,
                time_match,
                effective_min_time,
            )
            continue

        # Skip if both time and average are low
        if time_match < 50 and average_match < 75:
            logger.debug(
                "[%s|%s] Skipping - time %.2f < 50 and average %.2f < 75",
                song.song_id,
                result.platform_id,
                time_match,
                average_match,
            )
            continue

        # Factor in time match for lower-quality matches
        if (
            (not result.isrc_search and average_match <= HIGH_MATCH_THRESHOLD)
            or time_match < 0
        ):
            average_match = (average_match + time_match) / 2
            logger.debug(
                "[%s|%s] Average with time: %.2f",
                song.song_id,
                result.platform_id,
                average_match,
            )

            # Penalize explicit mismatch
            if (
                result.explicit is not None
                and song.explicit is not None
                and result.explicit != song.explicit
            ):
                average_match -= EXPLICIT_MISMATCH_PENALTY
                logger.debug(
                    "[%s|%s] Explicit mismatch penalty applied",
                    song.song_id,
                    result.platform_id,
                )

        average_match = min(average_match, 100)
        logger.debug(
            "[%s|%s] Final score: %.2f",
            song.song_id,
            result.platform_id,
            average_match,
        )

        links_with_match_value[result] = average_match

    return links_with_match_value


def get_best_matches(
    results: dict[Result, float], score_threshold: float = 5.0
) -> list[tuple[Result, float]]:
    """
    Get the best matches from scored results.

    Returns results within the threshold of the highest score.

    Args:
        results: Dictionary of results with their scores
        score_threshold: Maximum difference from best score to include

    Returns:
        List of (result, score) tuples for best matches
    """
    if not results:
        return []

    result_items = list(results.items())

    # Sort by highest score
    sorted_results = sorted(result_items, key=lambda x: x[1], reverse=True)

    best_score = sorted_results[0][1]

    # Return all results within threshold of best
    return [
        (result, score)
        for result, score in sorted_results
        if (best_score - score) <= score_threshold
    ]


def get_best_result(
    results: list[Result],
    song: Song,
    search_query: str | None = None,
    min_score: float = 80.0,
) -> tuple[Result, float] | None:
    """
    Get the single best matching result for a song.

    Convenience function that combines order_results and get_best_matches.

    Args:
        results: List of search results
        song: Song to match against
        search_query: Optional search query used
        min_score: Minimum score required to return a result

    Returns:
        Tuple of (best_result, score) or None if no match meets threshold
    """
    scored = order_results(results, song, search_query)
    best_matches = get_best_matches(scored)

    if not best_matches:
        return None

    best_result, best_score = best_matches[0]

    if best_score < min_score:
        return None

    return best_result, best_score
