"""Normalization and fuzzy-matching helpers, ported verbatim from spotDL v4.

These are pure, offline, provider-agnostic string utilities used by the matcher.
The arithmetic and behavior are faithful ports of ``spotdl.utils.formatter`` and
``spotdl.utils.matching`` from spotDL v4; see the Task 3 brief for the CONTRACT.

Two deliberate deviations from v4:

1. ``ratio`` accepts only ``str`` (keeping its ``lru_cache`` type-clean under
   mypy strict). v4 occasionally called ``ratio`` on *tuples*; that path is
   preserved by the separate :func:`sequence_ratio` helper.
2. Collection parameters are ``tuple[...]`` (hashable, immutable) rather than
   v4's ``list``. :func:`based_sort` returns new lists and never mutates its
   inputs (v4 sorted in place).
"""

import re
from functools import lru_cache

import pykakasi
from rapidfuzz import fuzz
from slugify import slugify as _py_slugify

# Hiragana, katakana, half/full-width forms, CJK unified + extension-A.
# Ranges (verbatim from v4): U+3000-303F, U+3040-309F, U+30A0-30FF,
# U+FF00-FF9F, U+4E00-9FAF, U+3400-4DBF.
JAP_REGEX = re.compile("[　-〿぀-ゟ゠-ヿ＀-ﾟ一-龯㐀-䶿]")
# Everything except ASCII letters/digits, hyphen, and ! @ $ becomes a separator.
DISALLOWED_REGEX = re.compile(r"[^-a-zA-Z0-9\!\@\$]+")

# pykakasi ships no type stubs; its factory is untyped under mypy strict.
_KKS = pykakasi.kakasi()  # type: ignore[no-untyped-call]


@lru_cache(maxsize=4096)
def slugify(string: str) -> str:
    """Slugify ``string``, romanizing Japanese kana/kanji via pykakasi (Hepburn).

    Fast path: strings with no Japanese characters go straight through
    python-slugify. python-slugify mangles kana/kanji, so the Japanese path
    romanizes with pykakasi first (inserting hyphens between kana-vs-romaji
    runs) and then slugifies the resulting romaji.
    """
    # Fast path: no Japanese characters -> plain python-slugify.
    if not JAP_REGEX.search(string):
        return _py_slugify(string, regex_pattern=DISALLOWED_REGEX.pattern)

    # Japanese path.
    normal_slug = _py_slugify(string, regex_pattern=JAP_REGEX.pattern)
    results = _KKS.convert(normal_slug)

    result = ""
    for index, item in enumerate(results):
        result += item["hepburn"]
        # v4 duplicated the first clause; collapsed here (behavior-identical).
        # The ``results[index + 1]`` look-ahead is guarded by ``item == results[-1]``.
        if not (
            item["kana"] == item["hepburn"]
            or item == results[-1]
            or results[index + 1]["kana"] == results[index + 1]["hepburn"]
        ):
            result += "-"

    return _py_slugify(result, regex_pattern=DISALLOWED_REGEX.pattern)


@lru_cache(maxsize=8192)
def ratio(string1: str, string2: str) -> float:
    """Cached ``fuzz.ratio`` over two strings (0..100)."""
    return fuzz.ratio(string1, string2)


def sequence_ratio(seq1: tuple[str, ...], seq2: tuple[str, ...]) -> float:
    """``fuzz.ratio`` over two token tuples (order-sensitive, mirrors v4 fixup1)."""
    return fuzz.ratio(seq1, seq2)


def song_title(name: str, artists: tuple[str, ...]) -> str:
    """Build a display title, e.g. ``"Artist1, Artist2 - Song Name"`` (v4)."""
    joined_artists = ", ".join(artists)
    if len(artists) >= 1:
        return f"{joined_artists} - {name}"
    return name


def fill_string(strings: tuple[str, ...], main_string: str, string_to_check: str) -> str:
    """Append de-hyphenated slugs from ``strings`` that appear in
    ``string_to_check`` but not yet in ``main_string`` (v4 ``fill_string``)."""
    final_str = main_string
    test_str = final_str.replace("-", "")
    simple_test_str = string_to_check.replace("-", "")
    for string in strings:
        slug_str = slugify(string).replace("-", "")

        if slug_str in simple_test_str and slug_str not in test_str:
            final_str += f"-{slug_str}"
            test_str += slug_str

    return final_str


def clean_string(
    words: tuple[str, ...],
    string: str,
    *,
    sort: bool = False,
    join_str: str = "-",
) -> str:
    """Join the de-hyphenated slugs of ``words`` not already present in
    ``string`` (v4 ``create_clean_string``)."""
    string = slugify(string).replace("-", "")

    final: list[str] = []
    for word in words:
        slug_word = slugify(word).replace("-", "")

        if slug_word in string:
            continue

        final.append(slug_word)

    if sort:
        return sort_tokens(tuple(final), join_str)

    return f"{join_str}".join(final)


def sort_tokens(tokens: tuple[str, ...], join_str: str = "-") -> str:
    """Sort ``tokens`` lexicographically (on a copy) and join (v4 ``sort_string``)."""
    final = sorted(tokens)
    return f"{join_str}".join(final)


def based_sort(strings: list[str], based_on: list[str]) -> tuple[list[str], list[str]]:
    """Sort ``strings`` by the order of ``based_on`` (v4 ``based_sort``).

    Unlike v4 — which sorted its arguments in place — this copies both inputs
    and returns new lists; the caller's lists are left untouched.
    """
    sorted_strings = sorted(strings)
    sorted_based_on = sorted(based_on)

    list_map = {value: index for index, value in enumerate(sorted_based_on)}

    sorted_strings = sorted(
        sorted_strings,
        key=lambda x: list_map.get(x, -1),
        reverse=True,
    )

    sorted_based_on.reverse()

    return sorted_strings, sorted_based_on
