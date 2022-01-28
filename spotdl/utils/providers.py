from rapidfuzz import fuzz
from slugify.main import Slugify


def match_percentage(str1: str, str2: str, score_cutoff: float = 0) -> float:
    """
    A wrapper around `rapidfuzz.fuzz.partial_ratio` to handle UTF-8 encoded
    emojis that usually cause errors. Uses slugify to normalize the strings
    """

    try:
        return fuzz.ratio(str1, str2, score_cutoff=score_cutoff, processor=None)
    # On error, use slugify to handle unicode characters
    except Exception:  # pylint: disable=broad-except
        slugify = Slugify(to_lower=True)
        return fuzz.ratio(str1, str2, score_cutoff=score_cutoff, processor=slugify)
