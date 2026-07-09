"""Tests for ``spotdl_core.matching.text`` — v4-verbatim normalization helpers.

Every case in this module mirrors a row of the Task 3 CONTRACT tables. The
Japanese slugify rows assert *properties* (non-empty, no surviving CJK
codepoint, valid slug) rather than brittle romaji strings, plus a single golden
string captured from the installed pykakasi so drift is visible on a bump.
"""

import re

import pytest
from spotdl_core.matching.text import (
    JAP_REGEX,
    based_sort,
    clean_string,
    fill_string,
    ratio,
    sequence_ratio,
    slugify,
    song_title,
    sort_tokens,
)

# --------------------------------------------------------------------------- #
# slugify — ASCII / diacritic / whitespace rows
# --------------------------------------------------------------------------- #

_SLUGIFY_ASCII_CASES = [
    ("Hello World", "hello-world"),
    ("AC/DC", "ac-dc"),
    ("Beyoncé", "beyonce"),
    ("Motörhead", "motorhead"),
    ("Song (feat. X)", "song-feat-x"),
    ("Café!@$", "cafe!@$"),
    ("P!nk", "p!nk"),
    ("  spaced  out  ", "spaced-out"),
    ("AaaA---bbb", "aaaa-bbb"),
    ("", ""),
]


@pytest.mark.parametrize(("value", "expected"), _SLUGIFY_ASCII_CASES)
def test_slugify_ascii_and_diacritics(value: str, expected: str) -> None:
    assert slugify(value) == expected


# --------------------------------------------------------------------------- #
# slugify — Japanese romaji path (property-based)
# --------------------------------------------------------------------------- #

_SLUGIFY_JAPANESE_INPUTS = [
    "解憶",  # kanji
    "光",  # single kanji
    "ポップコーン",  # katakana
]


@pytest.mark.parametrize("value", _SLUGIFY_JAPANESE_INPUTS)
def test_slugify_japanese_produces_ascii_slug(value: str) -> None:
    result = slugify(value)
    # non-empty
    assert result
    # no surviving Japanese codepoint
    assert JAP_REGEX.search(result) is None
    # pure ASCII
    assert result.isascii()
    # valid slug: only allowed characters, no leading/trailing/doubled hyphen
    assert re.fullmatch(r"[a-z0-9!@$]+(?:-[a-z0-9!@$]+)*", result)


def test_slugify_japanese_golden_string() -> None:
    # Golden captured from installed pykakasi (2.3.x). May need refreshing on a
    # pykakasi bump — that is the point: drift becomes a visible test failure.
    assert slugify("解憶") == "jie-yi"


# --------------------------------------------------------------------------- #
# ratio / sequence_ratio
# --------------------------------------------------------------------------- #


def test_ratio_identical_strings() -> None:
    assert ratio("abc", "abc") == 100.0


def test_ratio_two_empty_strings() -> None:
    # NOTE: the brief's table predicted 0.0, but rapidfuzz 3.x defines
    # fuzz.ratio("", "") == 100.0. The port is a verbatim fuzz.ratio wrapper, so
    # we assert the real installed behavior (documented in the task report).
    assert ratio("", "") == 100.0


def test_ratio_near_miss_is_between_70_and_100() -> None:
    result = ratio("hello", "hallo")
    assert 70 < result < 100


def test_ratio_is_pure_across_repeat_calls() -> None:
    assert ratio("some string", "other string") == ratio("some string", "other string")


def test_sequence_ratio_identical_tuples() -> None:
    assert sequence_ratio(("a", "b"), ("a", "b")) == 100.0


def test_sequence_ratio_order_matters() -> None:
    assert sequence_ratio(("a", "b", "c"), ("c", "b", "a")) < 100


# --------------------------------------------------------------------------- #
# song_title
# --------------------------------------------------------------------------- #

_SONG_TITLE_CASES = [
    ("Name", ("A", "B"), "A, B - Name"),
    ("Name", ("A",), "A - Name"),
    ("Name", (), "Name"),
]


@pytest.mark.parametrize(("name", "artists", "expected"), _SONG_TITLE_CASES)
def test_song_title(name: str, artists: tuple[str, ...], expected: str) -> None:
    assert song_title(name, artists) == expected


# --------------------------------------------------------------------------- #
# fill_string
# --------------------------------------------------------------------------- #


def test_fill_string_appends_missing_slug() -> None:
    assert (
        fill_string(("Feat Artist",), "song-name", "song-name-featartist") == "song-name-featartist"
    )


def test_fill_string_does_not_readd_present_token() -> None:
    # "song" is already present in main_string, so it is not appended again.
    assert fill_string(("song",), "song-name", "song-name") == "song-name"


def test_fill_string_skips_token_absent_from_check_string() -> None:
    # slug not present in string_to_check -> nothing appended.
    assert fill_string(("Nope",), "song-name", "song-name") == "song-name"


# --------------------------------------------------------------------------- #
# clean_string
# --------------------------------------------------------------------------- #


def test_clean_string_drops_present_word() -> None:
    assert clean_string(("name",), "song-name") == ""


def test_clean_string_keeps_absent_word() -> None:
    assert clean_string(("artist",), "song-name") == "artist"


def test_clean_string_sort_orders_lexicographically() -> None:
    assert clean_string(("zebra", "alpha"), "song-name", sort=True) == "alpha-zebra"


def test_clean_string_custom_join_str() -> None:
    assert clean_string(("zebra", "alpha"), "song-name", join_str="_") == "zebra_alpha"


# --------------------------------------------------------------------------- #
# sort_tokens
# --------------------------------------------------------------------------- #


def test_sort_tokens_sorts_and_joins() -> None:
    assert sort_tokens(("c", "a", "b")) == "a-b-c"


def test_sort_tokens_custom_join_str() -> None:
    assert sort_tokens(("c", "a", "b"), join_str="_") == "a_b_c"


# --------------------------------------------------------------------------- #
# based_sort
# --------------------------------------------------------------------------- #


def test_based_sort_aligns_and_reverses() -> None:
    strings, based_on = based_sort(["a", "b", "c"], ["c", "b", "a"])
    assert strings == ["c", "b", "a"]
    assert based_on == ["c", "b", "a"]


def test_based_sort_does_not_mutate_inputs() -> None:
    original_strings = ["a", "b", "c"]
    original_based_on = ["c", "b", "a"]
    based_sort(original_strings, original_based_on)
    # v4 mutated in place; the port must leave caller lists untouched.
    assert original_strings == ["a", "b", "c"]
    assert original_based_on == ["c", "b", "a"]
