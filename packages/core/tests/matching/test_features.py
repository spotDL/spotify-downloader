"""Tests for ``spotdl_core.matching.features`` — v4-verbatim per-signal features.

Table-driven: one parametrized test per feature over small hand-built
``Track``/``AudioCandidate`` fixtures, plus the mandatory trap scenarios from
the Task 4 CONTRACT (remix double-penalty, multi-artist collapse, feat. fixup,
CJK titles, duration outlier, ISRC normalization, popularity clamp).
"""

import math

import pytest
from spotdl_core.matching.features import (
    FORBIDDEN_WORDS,
    album_similarity,
    artist_similarity,
    common_word_overlap,
    duration_delta_s,
    duration_similarity,
    explicit_mismatch,
    extract_features,
    forbidden_words,
    isrc_equal,
    main_artist_similarity,
    other_artist_similarity,
    popularity_prior,
    title_similarity,
)
from spotdl_core.model import AlbumRef, AudioCandidate, FeatureVector, ProviderId, Track


# --------------------------------------------------------------------------- #
# fixture builders
# --------------------------------------------------------------------------- #
def track(
    name: str = "Song",
    artists: tuple[str, ...] = ("Artist",),
    duration_ms: int = 200_000,
    album: str | None = None,
    isrc: str | None = None,
    explicit: bool | None = None,
) -> Track:
    return Track(
        name=name,
        artists=artists,
        duration_ms=duration_ms,
        album=AlbumRef(name=album) if album is not None else None,
        isrc=isrc,
        explicit=explicit,
    )


def cand(
    name: str = "Song",
    artists: tuple[str, ...] = ("Artist",),
    duration_ms: int | None = 200_000,
    album: str | None = None,
    isrc: str | None = None,
    verified: bool = False,
    popularity: int | None = None,
) -> AudioCandidate:
    return AudioCandidate(
        provider=ProviderId.YTMUSIC,
        provider_id="x",
        url="https://example.test/x",
        name=name,
        artists=artists,
        duration_ms=duration_ms,
        album=album,
        isrc=isrc,
        verified=verified,
        popularity=popularity,
    )


# --------------------------------------------------------------------------- #
# FORBIDDEN_WORDS — verbatim from v4 (duplicates load-bearing)
# --------------------------------------------------------------------------- #
def test_forbidden_words_list_is_v4_verbatim() -> None:
    assert FORBIDDEN_WORDS == (
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
    )
    # remix/reverb/live each appear twice; that duplication is intentional.
    assert FORBIDDEN_WORDS.count("remix") == 2
    assert FORBIDDEN_WORDS.count("reverb") == 2
    assert FORBIDDEN_WORDS.count("live") == 2


# --------------------------------------------------------------------------- #
# common_word_overlap
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "t_name, c_name, expected",
    [
        ("Song", "Song", True),
        ("Hello World", "A Hello Track", True),  # "hello" substring
        ("Song", "Totally Different", False),
        ("Song", "songbird", True),  # substring match
    ],
)
def test_common_word_overlap(t_name: str, c_name: str, expected: bool) -> None:
    assert common_word_overlap(track(name=t_name), cand(name=c_name)) is expected


# --------------------------------------------------------------------------- #
# title_similarity
# --------------------------------------------------------------------------- #
def test_title_similarity_exact() -> None:
    assert title_similarity(track(name="Song"), cand(name="Song")) == pytest.approx(100.0)


def test_title_similarity_different_is_lower_than_exact() -> None:
    # A mismatched title scores strictly below an exact one. (The absolute floor
    # is ~50 because v4's create_match_strings fills the shared artist into both
    # match strings; that artist-fill behavior is intentional v4 parity.)
    t = track(name="Song", artists=("Aaaaaa",))
    exact = title_similarity(t, cand(name="Song", artists=("Aaaaaa",)))
    different = title_similarity(t, cand(name="Zzzzzz", artists=("Qqqqqq",)))
    assert different < exact
    assert different < 60


# --------------------------------------------------------------------------- #
# main_artist_similarity
# --------------------------------------------------------------------------- #
def test_main_artist_similarity_no_candidate_artists_is_zero() -> None:
    assert main_artist_similarity(track(artists=("A",)), cand(artists=())) == 0.0


def test_main_artist_similarity_exact() -> None:
    assert main_artist_similarity(
        track(artists=("Artist",)), cand(artists=("Artist",))
    ) == pytest.approx(100.0)


def test_main_artist_similarity_collapse_contains_path() -> None:
    # track has 2 artists, candidate collapses both into a single artist string.
    score = main_artist_similarity(track(artists=("A", "B")), cand(artists=("A B",)))
    assert score > 0


# --------------------------------------------------------------------------- #
# other_artist_similarity
# --------------------------------------------------------------------------- #
def test_other_artist_similarity_single_track_artist_is_zero() -> None:
    assert other_artist_similarity(track(artists=("A",)), cand(artists=("A", "B"))) == 0.0


def test_other_artist_similarity_no_candidate_artists_is_zero() -> None:
    assert other_artist_similarity(track(artists=("A", "B")), cand(artists=())) == 0.0


def test_other_artist_similarity_matching_secondary() -> None:
    score = other_artist_similarity(
        track(artists=("Main", "Second")), cand(artists=("Main", "Second"))
    )
    assert score == pytest.approx(100.0)


# --------------------------------------------------------------------------- #
# artist_similarity (composed + 3 fixups)
# --------------------------------------------------------------------------- #
def test_artist_similarity_exact() -> None:
    assert artist_similarity(
        track(artists=("Artist",)), cand(artists=("Artist",))
    ) == pytest.approx(100.0)


def test_artist_similarity_feat_notation_recovered_by_fixup() -> None:
    # track "Song" by (A, B); candidate lists only A but names both -> fixup path.
    score = artist_similarity(
        track(name="Song", artists=("A", "B")),
        cand(name="A, B - Song", artists=("A",)),
    )
    assert score > 70


def test_artist_similarity_clamped_to_100() -> None:
    score = artist_similarity(track(artists=("Artist",)), cand(artists=("Artist",)))
    assert score <= 100


# --------------------------------------------------------------------------- #
# album_similarity
# --------------------------------------------------------------------------- #
def test_album_similarity_none_when_candidate_has_no_album() -> None:
    assert album_similarity(track(album="A"), cand(album=None)) is None


def test_album_similarity_exact() -> None:
    assert album_similarity(track(album="Great Album"), cand(album="Great Album")) == pytest.approx(
        100.0
    )


def test_album_similarity_track_without_album() -> None:
    # candidate has album, track does not -> ratio against empty string.
    assert album_similarity(track(album=None), cand(album="Great Album")) == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# duration
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "t_ms, c_ms, expected_delta",
    [
        (200_000, 200_000, 0.0),
        (200_000, 210_000, 10.0),
        (200_000, None, 200.0),  # unknown candidate duration -> full track length
    ],
)
def test_duration_delta_s(t_ms: int, c_ms: int | None, expected_delta: float) -> None:
    assert duration_delta_s(track(duration_ms=t_ms), cand(duration_ms=c_ms)) == pytest.approx(
        expected_delta
    )


@pytest.mark.parametrize(
    "delta_ms, expected",
    [
        (0, 100.0),
        (10_000, math.exp(-1.0) * 100),
        (30_000, math.exp(-3.0) * 100),
        (60_000, math.exp(-6.0) * 100),
    ],
)
def test_duration_similarity(delta_ms: int, expected: float) -> None:
    assert duration_similarity(
        track(duration_ms=200_000), cand(duration_ms=200_000 + delta_ms)
    ) == pytest.approx(expected)


def test_duration_similarity_outlier_45s_below_5() -> None:
    assert duration_similarity(track(duration_ms=200_000), cand(duration_ms=245_000)) < 5


# --------------------------------------------------------------------------- #
# forbidden_words
# --------------------------------------------------------------------------- #
def test_forbidden_words_remix_double_entry() -> None:
    assert forbidden_words(track(name="Song"), cand(name="Song (Remix)")) == (
        "remix",
        "remix",
    )


def test_forbidden_words_cover_single_entry() -> None:
    assert forbidden_words(track(name="Song"), cand(name="Song (Cover)")) == ("cover",)


def test_forbidden_words_present_in_both_is_empty() -> None:
    assert forbidden_words(track(name="Song Remix"), cand(name="Song Remix")) == ()


def test_forbidden_words_none() -> None:
    assert forbidden_words(track(name="Song"), cand(name="Song")) == ()


# --------------------------------------------------------------------------- #
# explicit_mismatch  (candidate has no explicit field -> always False)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("t_explicit", [None, True, False])
def test_explicit_mismatch_always_false_without_candidate_signal(
    t_explicit: bool | None,
) -> None:
    assert explicit_mismatch(track(explicit=t_explicit), cand()) is False


# --------------------------------------------------------------------------- #
# isrc_equal
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "t_isrc, c_isrc, expected",
    [
        ("USUM71234567", "us-um7-12-34567", True),
        ("USUM71234567", "USUM71234567", True),
        ("USUM71234567", None, False),
        (None, "USUM71234567", False),
        (None, None, False),
        ("USUM71234567", "GBUM71234567", False),
    ],
)
def test_isrc_equal(t_isrc: str | None, c_isrc: str | None, expected: bool) -> None:
    assert isrc_equal(track(isrc=t_isrc), cand(isrc=c_isrc)) is expected


# --------------------------------------------------------------------------- #
# popularity_prior
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "popularity, expected",
    [
        (None, 0.0),
        (0, 0.0),
        (50, 0.5),
        (100, 1.0),
        (150, 1.0),  # clamped
    ],
)
def test_popularity_prior(popularity: int | None, expected: float) -> None:
    assert popularity_prior(cand(popularity=popularity)) == pytest.approx(expected)


def test_popularity_prior_custom_max() -> None:
    assert popularity_prior(cand(popularity=500), max_popularity=1000.0) == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# CJK title (romaji via slugify)
# --------------------------------------------------------------------------- #
def test_cjk_title_and_common_word() -> None:
    jp = "こんにちは"  # こんにちは
    assert title_similarity(track(name=jp), cand(name=jp)) > 80
    assert common_word_overlap(track(name=jp), cand(name=jp)) is True


# --------------------------------------------------------------------------- #
# extract_features — assembly + exact-match scenario
# --------------------------------------------------------------------------- #
def test_extract_features_exact_match_scenario() -> None:
    t = track(name="Song", artists=("Artist",), duration_ms=200_000, album="Album")
    c = cand(
        name="Song",
        artists=("Artist",),
        duration_ms=200_000,
        album="Album",
        verified=True,
        popularity=100,
    )
    fv = extract_features(t, c)
    assert isinstance(fv, FeatureVector)
    assert fv.title_similarity == pytest.approx(100.0)
    assert fv.artist_similarity == pytest.approx(100.0)
    assert fv.duration_similarity == pytest.approx(100.0)
    assert fv.duration_delta_s == pytest.approx(0.0)
    assert fv.forbidden_words == ()
    assert fv.album_similarity == pytest.approx(100.0)
    assert fv.common_word_overlap is True
    assert fv.verified_source is True
    assert fv.popularity_prior == pytest.approx(1.0)
    assert fv.explicit_mismatch is False


def test_extract_features_verified_source_reflects_candidate() -> None:
    assert extract_features(track(), cand(verified=False)).verified_source is False
    assert extract_features(track(), cand(verified=True)).verified_source is True
