"""
Module for provider utilities.
"""

from rapidfuzz import fuzz
from slugify import slugify


def match_percentage(str1: str, str2: str, score_cutoff: float = 0) -> float:
    """
    A wrapper around `partial_ratio` to handle UTF-8 encoded characters.

    ### Arguments
    - str1: The first string to compare.
    - str2: The second string to compare.
    - score_cutoff: The score cutoff to use.

    ### Returns
    - The percentage of similarity between the two strings.

    ### Notes
    - Uses slugify to normalize the strings
    """

    try:
        return fuzz.partial_ratio(str1, str2, score_cutoff=score_cutoff, processor=None)
    except Exception:
        # On error, use slugify to handle unicode characters.
        return fuzz.partial_ratio(
            str1, str2, score_cutoff=score_cutoff, processor=slugify
        )
