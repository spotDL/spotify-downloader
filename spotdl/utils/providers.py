from rapidfuzz import fuzz
from slugify import slugify


def match_percentage(str1: str, str2: str, score_cutoff: float = 0) -> float:
    """
    A wrapper around `rapidfuzz.fuzz.partial_ratio` to handle UTF-8 encoded
    emojis that usually cause errors. Uses slugify to normalize the strings
    """

    try:
        return fuzz.partial_ratio(str1, str2, score_cutoff=score_cutoff, processor=None)
    # On error, use slugify to handle unicode characters
    except Exception:
        return fuzz.partial_ratio(
            str1, str2, score_cutoff=score_cutoff, processor=slugify
        )
