"""
Module for all things matching related
"""

import logging
from itertools import product, zip_longest
from math import exp
from typing import Dict, List, Optional, Tuple

from spotdl.types.result import Result
from spotdl.types.song import Song
from spotdl.utils.formatter import (
    create_search_query,
    create_song_title,
    ratio,
    slugify,
)
from spotdl.utils.logging import MATCH

__all__ = [
    "FORBIDDEN_WORDS",
    "fill_string",
    "create_clean_string",
    "sort_string",
    "based_sort",
    "check_common_word",
    "check_forbidden_words",
    "create_match_strings",
    "get_best_matches",
    "calc_main_artist_match",
    "calc_artists_match",
    "artists_match_fixup1",
    "artists_match_fixup2",
    "artists_match_fixup3",
    "calc_name_match",
    "calc_time_match",
    "calc_album_match",
]

logger = logging.getLogger(__name__)

FORBIDDEN_WORDS = [
    "bassboosted",
    "remix",
    "remastered",
    "remaster",
    "reverb",
    "bassboost",
    "live",
    "acoustic",
    "8daudio",
    "concert",
    "live",
    "acapella",
    "slowed",
    "instrumental",
    "remix",
    "cover",
    "reverb",
]


def debug(song_id: str, result_id: str, message: str) -> None:
    """
    Log a message with MATCH level

    ### Arguments
    - message: message to log
    """

    logger.log(MATCH, "[%s|%s] %s", song_id, result_id, message)


def fill_string(strings: List[str], main_string: str, string_to_check: str) -> str:
    """
    Create a string with strings from `strings` list
    if they are not yet present in main_string
    but are present in string_to_check

    ### Arguments
    - strings: strings to check
    - main_string: string to add strings to
    - string_to_check: string to check if strings are present in

    ### Returns
    - string with strings from `strings` list
    """

    final_str = main_string
    test_str = final_str.replace("-", "")
    simple_test_str = string_to_check.replace("-", "")
    for string in strings:
        slug_str = slugify(string).replace("-", "")

        if slug_str in simple_test_str and slug_str not in test_str:
            final_str += f"-{slug_str}"
            test_str += slug_str

    return final_str


def create_clean_string(
    words: List[str], string: str, sort: bool = False, join_str: str = "-"
) -> str:
    """
    Create a string with strings from `words` list
    if they are not yet present in `string`

    ### Arguments
    - words: strings to check
    - string: string to check if strings are present in
    - sort: sort strings in list
    - join_str: string to join strings with

    ### Returns
    - string with strings from `words` list
    """

    string = slugify(string).replace("-", "")

    final = []
    for word in words:
        word = slugify(word).replace("-", "")

        if word in string:
            continue

        final.append(word)

    if sort:
        return sort_string(final, join_str)

    return f"{join_str}".join(final)


def sort_string(strings: List[str], join_str: str) -> str:
    """
    Sort strings in list and join them with `join` string

    ### Arguments
    - strings: strings to sort
    - join: string to join strings with

    ### Returns
    - joined sorted string
    """

    final_str = strings
    final_str.sort()

    return f"{join_str}".join(final_str)


def based_sort(strings: List[str], based_on: List[str]) -> Tuple[List[str], List[str]]:
    """
    Sort strings in list based on the order of strings in `based_on` list

    ### Arguments
    - strings: strings to sort
    - based_on: strings to sort `strings` list based on

    ### Returns
    - sorted list of strings
    """

    strings.sort()
    based_on.sort()

    list_map = {value: index for index, value in enumerate(based_on)}

    strings = sorted(
        strings,
        key=lambda x: list_map.get(x, -1),
        reverse=True,
    )

    based_on.reverse()

    return strings, based_on


def check_common_word(song: Song, result: Result) -> bool:
    """
    Check if a word is present in a sentence

    ### Arguments
    - song: song to match
    - result: result to match

    ### Returns
    - True if word is present in sentence, False otherwise
    """

    sentence_words = slugify(song.name).split("-")
    to_check = slugify(result.name).replace("-", "")

    for word in sentence_words:
        if word != "" and word in to_check:
            return True

    return False


def check_forbidden_words(song: Song, result: Result) -> Tuple[bool, List[str]]:
    """
    Check if a forbidden word is present in the result name

    ### Arguments
    - song: song to match
    - result: result to match

    ### Returns
    - True if forbidden word is present in result name, False otherwise
    """

    song_name = slugify(song.name).replace("-", "")
    to_check = slugify(result.name).replace("-", "")

    words = []
    for word in FORBIDDEN_WORDS:
        if word in to_check and word not in song_name:
            words.append(word)

    return len(words) > 0, words


def create_match_strings(
    song: Song, result: Result, search_query: Optional[str] = None
) -> Tuple[str, str]:
    """
    Create strings based on song and result to match
    fill strings with missing artists

    ### Arguments
    - song: song to match
    - result: result to match

    ### Returns
    - tuple of strings to match
    """

    slug_song_name = slugify(song.name)
    slug_song_title = slugify(
        create_song_title(song.name, song.artists)
        if not search_query
        else create_search_query(song, search_query, False, None, True)
    )

    test_str1 = slugify(result.name)
    test_str2 = slug_song_name if result.verified else slug_song_title

    # Fill strings with missing artists
    test_str1 = fill_string(song.artists, test_str1, test_str2)
    test_str2 = fill_string(song.artists, test_str2, test_str1)

    # Sort both strings and then join them
    test_list1, test_list2 = based_sort(test_str1.split("-"), test_str2.split("-"))
    test_str1, test_str2 = "-".join(test_list1), "-".join(test_list2)

    return test_str1, test_str2


def get_best_matches(
    results: Dict[Result, float], score_threshold: float
) -> List[Tuple[Result, float]]:
    """
    Get best matches from a list of results

    ### Arguments
    - results: list of results to match
    - score_threshold: threshold to match results

    ### Returns
    - list of best matches
    """

    result_items = list(results.items())

    # Sort results by highest score
    sorted_results = sorted(result_items, key=lambda x: x[1], reverse=True)

    best_score = sorted_results[0][1]

    return [
        result
        for result in sorted_results
        if (best_score - result[1]) <= score_threshold
    ]


def calc_main_artist_match(song: Song, result: Result) -> float:
    """
    Check if main artist is present in list of artists

    ### Arguments
    - main_artist: main artist to check
    - artists: list of artists to check

    ### Returns
    - True if main artist is present in list of artists, False otherwise
    """

    main_artist_match = 0.0

    # Result has no artists, return 0.0
    if not result.artists:
        return main_artist_match

    song_artists, result_artists = list(map(slugify, song.artists)), list(
        map(slugify, result.artists)
    )
    sorted_song_artists, sorted_result_artists = based_sort(
        song_artists, result_artists
    )

    debug(song.song_id, result.result_id, f"Song artists: {sorted_song_artists}")
    debug(song.song_id, result.result_id, f"Result artists: {sorted_result_artists}")

    slug_song_main_artist = slugify(song.artists[0])
    slug_result_main_artist = sorted_result_artists[0]

    # Result has only one artist, but song has multiple artists
    # we can assume that other artists are in the main artist name
    if len(song.artists) > 1 and len(result.artists) == 1:
        for artist in map(slugify, song.artists[1:]):
            artist = sort_string(slugify(artist).split("-"), "-")

            res_main_artist = sort_string(slug_result_main_artist.split("-"), "-")

            if artist in res_main_artist:
                main_artist_match += 100 / len(song.artists)

        return main_artist_match

    # Match main result artist with main song artist
    main_artist_match = ratio(slug_song_main_artist, slug_result_main_artist)

    debug(
        song.song_id, result.result_id, f"First main artist match: {main_artist_match}"
    )

    # Use second artist from the sorted list to
    # calculate the match if the first artist match is too low
    if main_artist_match < 50 and len(song_artists) > 1:
        for song_artist, result_artist in product(
            song_artists[:2], sorted_result_artists[:2]
        ):
            new_artist_match = ratio(song_artist, result_artist)
            debug(
                song.song_id,
                result.result_id,
                f"Matched {song_artist} with {result_artist}: {new_artist_match}",
            )

            main_artist_match = max(main_artist_match, new_artist_match)

    return main_artist_match


def calc_artists_match(song: Song, result: Result) -> float:
    """
    Check if all artists are present in list of artists

    ### Arguments
    - song: song to match
    - result: result to match

    ### Returns
    - artists match percentage
    """

    artist_match_number = 0.0

    # Result has only one artist, return 0.0
    if len(song.artists) == 1 or not result.artists:
        return artist_match_number

    artist1_list, artist2_list = based_sort(
        list(map(slugify, song.artists)), list(map(slugify, result.artists))
    )

    # Remove main artist from the lists
    artist1_list, artist2_list = artist1_list[1:], artist2_list[1:]

    artists_match = 0.0
    for artist1, artist2 in zip_longest(artist1_list, artist2_list):
        artist12_match = ratio(artist1, artist2)
        artists_match += artist12_match

    artist_match_number = artists_match / len(artist1_list)

    return artist_match_number


def artists_match_fixup1(song: Song, result: Result, score: float) -> float:
    """
    Multiple fixes to the artists score for
    not verified results to improve the accuracy

    ### Arguments
    - song: song to match
    - result: result to match
    - score: current score

    ### Returns
    - new score
    """

    # If we have a verified result, we don't have to fix anything
    if result.verified or score > 50:
        return score

    # If we didn't find any artist match,
    # we fallback to channel name match
    channel_name_match = ratio(
        slugify(song.artist),
        slugify(", ".join(result.artists)) if result.artists else "",
    )

    score = max(score, channel_name_match)

    # If artist match is still too low,
    # we fallback to matching all song artist names
    # with the result's title
    if score <= 70:
        artist_title_match = 0.0
        result_name = slugify(result.name).replace("-", "")
        for artist in song.artists:
            slug_artist = slugify(artist).replace("-", "")

            if slug_artist in result_name:
                artist_title_match += 1.0

        artist_title_match = (artist_title_match / len(song.artists)) * 100

        score = max(score, artist_title_match)

    # If artist match is still too low,
    # we fallback to matching all song artist names
    # with the result's artists
    if score <= 70:
        # Song artists: ['charlie-moncler', 'fukaj', 'mata', 'pedro']
        # Result artists: ['fukaj-mata-charlie-moncler-und-pedro']

        # For artist_list1
        artist_list1 = []
        for artist in song.artists:
            artist_list1.extend(slugify(artist).split("-"))

        # For artist_list2
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
    song: Song, result: Result, score: float, search_query: Optional[str] = None
) -> float:
    """
    Multiple fixes to the artists score for
    verified results to improve the accuracy

    ### Arguments
    - song: song to match
    - result: result to match
    - score: current score

    ### Returns
    - new score
    """

    if score > 70 or not result.verified:
        # Don't fixup the score
        # if the artist match is already high
        # or if the result is not verified
        return score

    # Slugify some variables
    slug_song_name = slugify(song.name)
    slug_result_name = slugify(result.name)

    # # Check if the main artist is simlar
    has_main_artist = (score / (2 if len(song.artists) > 1 else 1)) > 50

    _, match_str2 = create_match_strings(song, result, search_query)

    # Check if other song artists are in the result name
    # if they are, we increase the artist match
    # (main artist is already checked, so we skip it)
    artists_to_check = song.artists[int(has_main_artist) :]
    for artist in artists_to_check:
        artist = slugify(artist).replace("-", "")
        if artist in match_str2.replace("-", ""):
            score += 5

    # if the artist match is still too low,
    # we fallback to matching all song artist names
    # with the result's artists
    if score <= 70:
        # Artists from song/result name without the song/result name words
        artist_list1 = create_clean_string(song.artists, slug_song_name, True)
        artist_list2 = create_clean_string(
            list(result.artists) if result.artists else [result.author],
            slug_result_name,
            True,
        )

        artist_title_match = ratio(artist_list1, artist_list2)

        score = max(score, artist_title_match)

    return score


def artists_match_fixup3(song: Song, result: Result, score: float) -> float:
    """
    Calculate match percentage based result's name
    and song's title if the result has exactly one artist
    and the song has more than one artist

    ### Arguments
    - song: song to match
    - result: result to match
    - score: current score

    ### Returns
    - new score
    """

    if (
        score > 70
        or not result.artists
        or len(result.artists) > 1
        or len(song.artists) == 1
    ):
        # Don't fixup the score
        # if the score is already high
        # or if the result has more than one artist
        # or if the song has only one artist
        return score

    artists_score_fixup = ratio(
        slugify(result.name),
        slugify(create_song_title(song.name, [song.artist])),
    )

    if artists_score_fixup >= 80:
        score = (score + artists_score_fixup) / 2

    # Make sure that the score is not higher than 100
    score = min(score, 100)

    return score


def calc_name_match(
    song: Song, result: Result, search_query: Optional[str] = None
) -> float:
    """
    Calculate name match percentage

    ### Arguments
    - song: song to match
    - result: result to match

    ### Returns
    - name match percentage
    """

    # Create match strings that will be used
    # to calculate name match value
    match_str1, match_str2 = create_match_strings(song, result, search_query)
    result_name, song_name = slugify(result.name), slugify(song.name)

    res_list, song_list = based_sort(result_name.split("-"), song_name.split("-"))
    result_name, song_name = "-".join(res_list), "-".join(song_list)

    # Calculate initial name match
    name_match = ratio(result_name, song_name)

    debug(song.song_id, result.result_id, f"MATCH STRINGS: {match_str1} - {match_str2}")
    debug(
        song.song_id,
        result.result_id,
        f"SLUG MATCH STRINGS: {song_name} - {result_name}",
    )
    debug(song.song_id, result.result_id, f"First name match: {name_match}")

    # If name match is lower than 60%,
    # we try to match using the test strings
    if name_match <= 75:
        second_name_match = ratio(
            match_str1,
            match_str2,
        )

        debug(
            song.song_id,
            result.result_id,
            f"Second name match: {second_name_match}",
        )

        name_match = max(name_match, second_name_match)

    return name_match


def calc_time_match(song: Song, result: Result) -> float:
    """
    Calculate time difference between song and result

    ### Arguments
    - song: song to match
    - result: result to match

    ### Returns
    - time difference between song and result
    """

    time_diff = abs(song.duration - result.duration)
    score = exp(-0.1 * time_diff)
    return score * 100


def calc_album_match(song: Song, result: Result) -> float:
    """
    Calculate album match percentage

    ### Arguments
    - song: song to match
    - result: result to match

    ### Returns
    - album match percentage
    """

    if not result.album:
        return 0.0

    return ratio(slugify(song.album_name), slugify(result.album))


def order_results(
    results: List[Result],
    song: Song,
    search_query: Optional[str] = None,
) -> Dict[Result, float]:
    """
    Order results.

    ### Arguments
    - results: The results to order.
    - song: The song to order for.
    - search_query: The search query.

    ### Returns
    - The ordered results.
    """

    # Assign an overall avg match value to each result
    links_with_match_value = {}

    # Iterate over all results
    for result in results:
        debug(
            song.song_id,
            result.result_id,
            f"Calculating match value for {result.url} - {result.json}",
        )

        # skip results that have no common words in their name
        if not check_common_word(song, result):
            debug(
                song.song_id, result.result_id, "Skipping result due to no common words"
            )

            continue

        # Calculate match value for main artist
        artists_match = calc_main_artist_match(song, result)
        debug(song.song_id, result.result_id, f"Main artist match: {artists_match}")

        # Calculate match value for all artists
        other_artists_match = calc_artists_match(song, result)
        debug(
            song.song_id,
            result.result_id,
            f"Other artists match: {other_artists_match}",
        )

        artists_match += other_artists_match

        # Calculate initial artist match value
        debug(song.song_id, result.result_id, f"Initial artists match: {artists_match}")
        artists_match = artists_match / (2 if len(song.artists) > 1 else 1)
        debug(song.song_id, result.result_id, f"First artists match: {artists_match}")

        # First attempt to fix artist match
        artists_match = artists_match_fixup1(song, result, artists_match)
        debug(
            song.song_id,
            result.result_id,
            f"Artists match after fixup1: {artists_match}",
        )

        # Second attempt to fix artist match
        artists_match = artists_match_fixup2(song, result, artists_match)
        debug(
            song.song_id,
            result.result_id,
            f"Artists match after fixup2: {artists_match}",
        )

        # Third attempt to fix artist match
        artists_match = artists_match_fixup3(song, result, artists_match)
        debug(
            song.song_id,
            result.result_id,
            f"Artists match after fixup3: {artists_match}",
        )

        debug(song.song_id, result.result_id, f"Final artists match: {artists_match}")

        # Calculate name match
        name_match = calc_name_match(song, result, search_query)
        debug(song.song_id, result.result_id, f"Initial name match: {name_match}")

        # Check if result contains forbidden words
        contains_fwords, found_fwords = check_forbidden_words(song, result)
        if contains_fwords:
            for _ in found_fwords:
                name_match -= 15

        debug(
            song.song_id,
            result.result_id,
            f"Contains forbidden words: {contains_fwords}, {found_fwords}",
        )
        debug(song.song_id, result.result_id, f"Final name match: {name_match}")

        # Calculate album match
        album_match = calc_album_match(song, result)
        debug(song.song_id, result.result_id, f"Final album match: {album_match}")

        # Calculate time match
        time_match = calc_time_match(song, result)
        debug(song.song_id, result.result_id, f"Final time match: {time_match}")

        # Ignore results with name match lower than 60%
        if name_match <= 60:
            debug(
                song.song_id,
                result.result_id,
                "Skipping result due to name match lower than 60%",
            )
            continue

        # Ignore results with artists match lower than 70%
        if artists_match < 70 and result.source != "slider.kz":
            debug(
                song.song_id,
                result.result_id,
                "Skipping result due to artists match lower than 70%",
            )
            continue

        # Calculate total match
        average_match = (artists_match + name_match) / 2
        debug(song.song_id, result.result_id, f"Average match: {average_match}")

        if (
            result.verified
            and not result.isrc_search
            and result.album
            and album_match <= 80
        ):
            # we are almost certain that this is the correct result
            # so we add the album match to the average match
            average_match = (average_match + album_match) / 2
            debug(
                song.song_id,
                result.result_id,
                f"Average match /w album match: {average_match}",
            )

        # Skip results with time match lower than 25%
        if time_match < 25:
            debug(
                song.song_id,
                result.result_id,
                "Skipping result due to time match lower than 25%",
            )
            continue

        # If the time match is lower than 50%
        # and the average match is lower than 75%
        # we skip the result
        if time_match < 50 and average_match < 75:
            debug(
                song.song_id,
                result.result_id,
                "Skipping result due to time match < 50% and average match < 75%",
            )
            continue

        if (
            (not result.isrc_search and average_match <= 85)
            or result.source == "slider.kz"
            or time_match < 0
        ):
            # Don't add time to avg match if average match is not the best
            # (lower than 85%), always include time match if result is from
            # slider.kz or if time match is lower than 0
            average_match = (average_match + time_match) / 2

            debug(
                song.song_id,
                result.result_id,
                f"Average match /w time match: {average_match}",
            )

            if (result.explicit is not None and song.explicit is not None) and (
                result.explicit != song.explicit
            ):
                debug(
                    song.song_id,
                    result.result_id,
                    "Lowering average match due to explicit mismatch",
                )

                average_match -= 5

        average_match = min(average_match, 100)
        debug(song.song_id, result.result_id, f"Final average match: {average_match}")

        # the results along with the avg Match
        links_with_match_value[result] = average_match

    return links_with_match_value
