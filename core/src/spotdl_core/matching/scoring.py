"""Scoring functions for song-to-result matching."""

from __future__ import annotations

import logging
from itertools import product, zip_longest
from math import exp
from typing import TYPE_CHECKING

from spotdl_core.matching.constants import FORBIDDEN_WORDS
from spotdl_core.matching.utils import (
    based_sort,
    create_clean_string,
    create_song_title,
    fill_string,
    ratio,
    slugify,
    sort_string,
)

if TYPE_CHECKING:
    from spotdl_core.types.result import Result
    from spotdl_core.types.song import Song

logger = logging.getLogger(__name__)


def check_common_word(song: Song, result: Result) -> bool:
    """
    Check if at least one word from the song name exists in the result name.

    This is a quick filter to skip completely unrelated results.

    Args:
        song: Song to match
        result: Result to check

    Returns:
        True if at least one common word found
    """
    sentence_words = slugify(song.name).split("-")
    to_check = slugify(result.name).replace("-", "")

    for word in sentence_words:
        if word and word in to_check:
            return True

    return False


def check_forbidden_words(song: Song, result: Result) -> tuple[bool, list[str]]:
    """
    Check if result contains forbidden words not present in song name.

    Forbidden words indicate different versions (remix, live, etc.).

    Args:
        song: Song to match
        result: Result to check

    Returns:
        Tuple of (has_forbidden_words, list_of_found_words)
    """
    song_name = slugify(song.name).replace("-", "")
    to_check = slugify(result.name).replace("-", "")

    words = []
    for word in FORBIDDEN_WORDS:
        if word in to_check and word not in song_name:
            words.append(word)

    return len(words) > 0, words


def create_match_strings(
    song: Song, result: Result, search_query: str | None = None
) -> tuple[str, str]:
    """
    Create normalized strings for matching song and result.

    Fills both strings with missing artist names to improve comparison.

    Args:
        song: Song to match
        result: Result to match
        search_query: Optional search query used

    Returns:
        Tuple of (result_string, song_string) for comparison
    """
    slug_song_name = slugify(song.name)

    if search_query:
        slug_song_title = slugify(search_query)
    else:
        slug_song_title = slugify(create_song_title(song.name, song.artists))

    test_str1 = slugify(result.name)
    test_str2 = slug_song_name if result.verified else slug_song_title

    # Fill strings with missing artists
    test_str1 = fill_string(song.artists, test_str1, test_str2)
    test_str2 = fill_string(song.artists, test_str2, test_str1)

    # Sort and join for consistent comparison
    test_list1, test_list2 = based_sort(test_str1.split("-"), test_str2.split("-"))
    test_str1, test_str2 = "-".join(test_list1), "-".join(test_list2)

    return test_str1, test_str2


def calc_main_artist_match(song: Song, result: Result) -> float:
    """
    Calculate match score for the main/primary artist.

    Args:
        song: Song to match
        result: Result to match

    Returns:
        Match score from 0 to 100
    """
    main_artist_match = 0.0

    # Result has no artists, return 0.0
    if not result.artists:
        return main_artist_match

    song_artists = list(map(slugify, song.artists))
    result_artists = list(map(slugify, result.artists))
    sorted_song_artists, sorted_result_artists = based_sort(song_artists, result_artists)

    slug_song_main_artist = slugify(song.artists[0])
    slug_result_main_artist = sorted_result_artists[0]

    # Result has only one artist, but song has multiple artists
    # Check if other song artists are contained in the main artist name
    if len(song.artists) > 1 and len(result.artists) == 1:
        for artist in map(slugify, song.artists[1:]):
            artist = sort_string(slugify(artist).split("-"), "-")
            res_main_artist = sort_string(slug_result_main_artist.split("-"), "-")

            if artist in res_main_artist:
                main_artist_match += 100 / len(song.artists)

        return main_artist_match

    # Match main result artist with main song artist
    main_artist_match = ratio(slug_song_main_artist, slug_result_main_artist)

    # If match is low and song has multiple artists,
    # try matching other artist combinations
    if main_artist_match < 50 and len(song_artists) > 1:
        for song_artist, result_artist in product(
            song_artists[:2], sorted_result_artists[:2]
        ):
            new_artist_match = ratio(song_artist, result_artist)
            main_artist_match = max(main_artist_match, new_artist_match)

    return main_artist_match


def calc_artists_match(song: Song, result: Result) -> float:
    """
    Calculate match score for all artists (excluding main artist).

    Args:
        song: Song to match
        result: Result to match

    Returns:
        Match score from 0 to 100
    """
    artist_match_number = 0.0

    # Single artist or no result artists
    if len(song.artists) == 1 or not result.artists:
        return artist_match_number

    artist1_list, artist2_list = based_sort(
        list(map(slugify, song.artists)), list(map(slugify, result.artists))
    )

    # Remove main artist from lists
    artist1_list, artist2_list = artist1_list[1:], artist2_list[1:]

    artists_match = 0.0
    for artist1, artist2 in zip_longest(artist1_list, artist2_list):
        artist12_match = ratio(artist1, artist2) if artist1 and artist2 else 0.0
        artists_match += artist12_match

    if artist1_list:
        artist_match_number = artists_match / len(artist1_list)

    return artist_match_number


def artists_match_fixup1(song: Song, result: Result, score: float) -> float:
    """
    First fixup pass for artist matching on unverified results.

    Tries channel name matching and artist-in-title matching.

    Args:
        song: Song to match
        result: Result to match
        score: Current artist match score

    Returns:
        Adjusted score
    """
    # Skip if already good score or verified result
    if result.verified or score > 50:
        return score

    # Try matching against channel name
    channel_name_match = ratio(
        slugify(song.artist),
        slugify(", ".join(result.artists)) if result.artists else "",
    )
    score = max(score, channel_name_match)

    # Try finding artist names in result title
    if score <= 70:
        artist_title_match = 0.0
        result_name = slugify(result.name).replace("-", "")
        for artist in song.artists:
            slug_artist = slugify(artist).replace("-", "")
            if slug_artist in result_name:
                artist_title_match += 1.0

        artist_title_match = (artist_title_match / len(song.artists)) * 100
        score = max(score, artist_title_match)

    # Try matching split artist names
    if score <= 70:
        artist_list1 = []
        for artist in song.artists:
            artist_list1.extend(slugify(artist).split("-"))

        artist_list2 = []
        if result.artists:
            for artist in result.artists:
                artist_list2.extend(slugify(artist).split("-"))

        artist_tuple1 = tuple(artist_list1)
        artist_tuple2 = tuple(artist_list2)

        artist_title_match = ratio(artist_tuple1, artist_tuple2)
        score = max(score, artist_title_match)

    return score


def artists_match_fixup2(
    song: Song, result: Result, score: float, search_query: str | None = None
) -> float:
    """
    Second fixup pass for artist matching on verified results.

    Checks for artists in the result name.

    Args:
        song: Song to match
        result: Result to match
        score: Current artist match score
        search_query: Optional search query used

    Returns:
        Adjusted score
    """
    if score > 70 or not result.verified:
        return score

    slug_song_name = slugify(song.name)
    slug_result_name = slugify(result.name)

    # Check if main artist was found
    has_main_artist = (score / (2 if len(song.artists) > 1 else 1)) > 50

    _, match_str2 = create_match_strings(song, result, search_query)

    # Check for other artists in result name
    artists_to_check = song.artists[int(has_main_artist) :]
    for artist in artists_to_check:
        artist = slugify(artist).replace("-", "")
        if artist in match_str2.replace("-", ""):
            score += 5

    # Try matching cleaned artist strings
    if score <= 70:
        artist_list1 = create_clean_string(song.artists, slug_song_name, True)
        artist_list2 = create_clean_string(
            list(result.artists) if result.artists else [result.artist],
            slug_result_name,
            True,
        )

        artist_title_match = ratio(artist_list1, artist_list2)
        score = max(score, artist_title_match)

    return score


def artists_match_fixup3(song: Song, result: Result, score: float) -> float:
    """
    Third fixup pass for single-artist results.

    Handles cases where result has one artist but song has multiple.

    Args:
        song: Song to match
        result: Result to match
        score: Current artist match score

    Returns:
        Adjusted score
    """
    if (
        score > 70
        or not result.artists
        or len(result.artists) > 1
        or len(song.artists) == 1
    ):
        return score

    # Compare result name to song title with single artist
    artists_score_fixup = ratio(
        slugify(result.name),
        slugify(create_song_title(song.name, [song.artist])),
    )

    if artists_score_fixup >= 80:
        score = (score + artists_score_fixup) / 2

    return min(score, 100)


def calc_name_match(
    song: Song, result: Result, search_query: str | None = None
) -> float:
    """
    Calculate match score for song name vs result name.

    Args:
        song: Song to match
        result: Result to match
        search_query: Optional search query used

    Returns:
        Match score from 0 to 100
    """
    match_str1, match_str2 = create_match_strings(song, result, search_query)
    result_name, song_name = slugify(result.name), slugify(song.name)

    res_list, song_list = based_sort(result_name.split("-"), song_name.split("-"))
    result_name, song_name = "-".join(res_list), "-".join(song_list)

    # Initial name match
    name_match = ratio(result_name, song_name)

    # Try with filled match strings if initial match is low
    if name_match <= 75:
        second_name_match = ratio(match_str1, match_str2)
        name_match = max(name_match, second_name_match)

    return name_match


def calc_time_match(song: Song, result: Result) -> float:
    """
    Calculate match score based on duration difference.

    Uses exponential decay - larger differences get lower scores.

    Args:
        song: Song to match
        result: Result to match

    Returns:
        Match score from 0 to 100
    """
    time_diff = abs(song.duration - result.duration)
    score = exp(-0.1 * time_diff)
    return score * 100


def calc_album_match(song: Song, result: Result) -> float:
    """
    Calculate match score for album name.

    Args:
        song: Song to match
        result: Result to match

    Returns:
        Match score from 0 to 100
    """
    if not result.album_name:
        return 0.0

    return ratio(slugify(song.album_name), slugify(result.album_name))
