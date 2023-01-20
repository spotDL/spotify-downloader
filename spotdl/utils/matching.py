"""
Module for all things matching related
"""

from itertools import zip_longest
from typing import Dict, List, Optional, Tuple

from spotdl.types.result import Result
from spotdl.types.song import Song
from spotdl.utils.formatter import (
    create_search_query,
    create_song_title,
    ratio,
    slugify,
)

__all__ = [
    "fill_string",
    "create_clean_string",
    "sort_string",
    "based_sort",
    "check_common_word",
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

    final_str = main_string.replace("-", "")
    simple_test_str = string_to_check.replace("-", "")
    for string in strings:
        slug_str = slugify(string).replace("-", "")

        if slug_str in simple_test_str and slug_str not in final_str:
            final_str += f"-{slug_str}"

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

    # Sort both strings and then joint them
    test_str1 = sort_string(test_str1.split("-"), "-")
    test_str2 = sort_string(test_str2.split("-"), "-")

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

    slug_song_main_artist = slugify(song.artists[0])
    slug_result_main_artist = slugify(result.artists[0])

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
    return ratio(slug_song_main_artist, slug_result_main_artist)


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

    slug_song_artists = slugify(", ".join(song.artists))
    slug_result_artists = slugify(", ".join(result.artists)) if result.artists else ""

    # match the song's artists with the result's artists
    # if the number of artists is the same
    if len(song.artists) == len(result.artists):
        return ratio(slug_song_artists, slug_result_artists)

    # Calculate the percentage of artists that are present in the result
    artists_percentage = (len(result.artists) * 100) / len(song.artists)

    if artists_percentage > 60 and len(song.artists) > 2:
        # Create lists of artists in song and result
        # After that sort them based on the order of the result's artists
        artist1_list, artist2_list = based_sort(
            list(map(slugify, song.artists)), list(map(slugify, result.artists))
        )

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

    # If we have a verified result, we don't need to fix anything
    if result.verified or score > 50:
        return score

    # If we didn't find any artist match,
    # we fallback to channel name match
    channel_name_match = ratio(
        slugify(song.artist),
        slugify(", ".join(result.artists)) if result.artists else "",
    )

    if channel_name_match > score:
        score = channel_name_match

    # If artist match is still too low,
    # we fallback to matching all song artist names
    # with the result's title
    if score <= 50:
        artist_title_match = 0.0
        for artist in song.artists:
            slug_artist = slugify(artist).replace("-", "")

            if slug_artist in slugify(result.name).replace("-", ""):
                artist_title_match += 1.0

        artist_title_match = (artist_title_match / len(song.artists)) * 100

        if artist_title_match > score:
            score = artist_title_match

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
    slug_song_artist = slugify(song.artists[0])
    slug_song_name = slugify(song.name)
    slug_result_name = slugify(result.name)
    slug_result_artists = slugify(", ".join(result.artists)) if result.artists else ""

    # Check if the main artist is simlar
    has_main_artist = (score / (2 if len(song.artists) > 1 else 1)) > 50

    match_str1, match_str2 = create_match_strings(song, result, search_query)

    # Add 10 points to the score
    # if the name match is greater than 75%
    if ratio(match_str1, match_str2) >= 75:
        score += 10

    # If the result doesn't have the same number of artists but has
    # the same main artist and similar name
    # we add 25% to the artist match
    if (
        result.artists
        and len(result.artists) < len(song.artists)
        and slug_song_artist.replace("-", "")
        in [
            slug_result_artists.replace("-", ""),
            slug_result_name.replace("-", ""),
        ]
    ):
        score += 25

    # Check if the song album name is very similar to the result album name
    # if it is, we increase the artist match
    if result.album:
        if (
            ratio(
                slugify(result.album),
                slugify(song.album_name),
            )
            >= 85
        ):
            score += 10

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

        if artist_title_match > score:
            score = artist_title_match

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

    # Calculate initial name match
    name_match = ratio(
        slugify(result.name),
        slugify(song.name),
    )

    # If name match is lower than 60%,
    # we try to match using the test strings
    if name_match <= 75:
        name_match = ratio(
            match_str1,
            match_str2,
        )

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

    if result.duration > song.duration:
        return 100 - (result.duration - song.duration)

    return 100 - (song.duration - result.duration)


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
