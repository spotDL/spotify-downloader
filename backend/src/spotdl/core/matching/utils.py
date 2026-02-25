"""Utility functions for string matching and manipulation."""

from __future__ import annotations

import re
from functools import lru_cache

import pykakasi
from rapidfuzz import fuzz
from slugify import slugify as py_slugify

# Japanese character detection regex
JAP_REGEX = re.compile(
    r"[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf]"
)

# Allowed characters after slugification
DISALLOWED_REGEX = re.compile(r"[^-a-zA-Z0-9!@$]+")

# Kakasi instance for Japanese romanization
_KKS = pykakasi.kakasi()  # type: ignore[no-untyped-call]


@lru_cache(maxsize=4096)
def slugify(string: str) -> str:
    """
    Slugify a string, with special handling for Japanese characters.

    Args:
        string: The string to slugify

    Returns:
        Slugified string with hyphens between words
    """
    # If no Japanese characters, use simple slugify
    if not JAP_REGEX.search(string):
        return py_slugify(string, regex_pattern=DISALLOWED_REGEX.pattern)

    # For Japanese text, first slugify to preserve structure
    normal_slug = py_slugify(string, regex_pattern=JAP_REGEX.pattern)

    # Convert to romaji using kakasi
    results = _KKS.convert(normal_slug)

    result = ""
    for index, item in enumerate(results):
        result += item["hepburn"]
        # Add hyphen between Japanese-to-romaji conversions
        if not (
            item["kana"] == item["hepburn"]
            or (
                item == results[-1]
                or results[index + 1]["kana"] == results[index + 1]["hepburn"]
            )
        ):
            result += "-"

    return py_slugify(result, regex_pattern=DISALLOWED_REGEX.pattern)


@lru_cache(maxsize=4096)
def ratio(string1: str | tuple[str, ...], string2: str | tuple[str, ...]) -> float:
    """
    Calculate fuzzy match ratio between two strings or tuples.

    Wrapper for rapidfuzz.fuzz.ratio with caching.

    Args:
        string1: First string or tuple of strings
        string2: Second string or tuple of strings

    Returns:
        Match ratio from 0 to 100
    """
    return fuzz.ratio(string1, string2)


def fill_string(strings: list[str], main_string: str, string_to_check: str) -> str:
    """
    Add strings to main_string if they exist in string_to_check but not in main_string.

    Used to normalize artist names across song and result strings.

    Args:
        strings: List of strings (usually artist names) to potentially add
        main_string: The string to add to (slugified)
        string_to_check: The reference string to check for presence

    Returns:
        main_string with additional strings appended
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
    words: list[str], string: str, sort: bool = False, join_str: str = "-"
) -> str:
    """
    Create a string from words that are not already in the given string.

    Args:
        words: Words to check
        string: String to check against
        sort: Whether to sort the result
        join_str: String to join words with

    Returns:
        Joined string of words not in the input string
    """
    string = slugify(string).replace("-", "")

    final = []
    for word in words:
        word = slugify(word).replace("-", "")
        if word not in string:
            final.append(word)

    if sort:
        return sort_string(final, join_str)

    return join_str.join(final)


def sort_string(strings: list[str], join_str: str) -> str:
    """
    Sort strings and join them.

    Args:
        strings: Strings to sort and join
        join_str: String to join with

    Returns:
        Sorted and joined string
    """
    sorted_strings = sorted(strings)
    return join_str.join(sorted_strings)


def based_sort(strings: list[str], based_on: list[str]) -> tuple[list[str], list[str]]:
    """
    Sort strings based on the order in another list.

    Args:
        strings: Strings to sort
        based_on: Reference list for ordering

    Returns:
        Tuple of (sorted strings, reversed based_on)
    """
    strings = sorted(strings)
    based_on = sorted(based_on)

    list_map = {value: index for index, value in enumerate(based_on)}

    strings = sorted(
        strings,
        key=lambda x: list_map.get(x, -1),
        reverse=True,
    )

    based_on.reverse()

    return strings, based_on


def create_song_title(song_name: str, song_artists: list[str]) -> str:
    """
    Create a display title from song name and artists.

    Args:
        song_name: Name of the song
        song_artists: List of artist names

    Returns:
        Formatted title like "Artist1, Artist2 - Song Name"
    """
    joined_artists = ", ".join(song_artists)
    if len(song_artists) >= 1:
        return f"{joined_artists} - {song_name}"
    return song_name


def create_search_query(
    song_name: str, song_artists: list[str], short: bool = False
) -> str:
    """
    Create a search query from song metadata.

    Args:
        song_name: Name of the song
        song_artists: List of artist names
        short: Whether to use only the first artist

    Returns:
        Search query string
    """
    if short:
        # Filter artists already in song name
        artists = [
            artist
            for artist in song_artists
            if slugify(artist) not in slugify(song_name)
        ]
        # Ensure at least the main artist is included
        if not artists or artists[0] != song_artists[0]:
            artists.insert(0, song_artists[0])
        return create_song_title(song_name, [artists[0]])

    return create_song_title(song_name, song_artists)
