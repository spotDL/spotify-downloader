"""Tests for ``spotdl_core.matching.scoring`` — versioned config, gates, ``score()``.

Table-driven. Exercises every hard gate at its boundary, the forbidden-word
penalty (per-entry, matching v4's duplicated list), the conditional album and
duration blends, the explicit-mismatch penalty, lossless config serialization,
and the ``weight_title + weight_artist == 1.0`` validator.

The v4-faithful ``score()`` arithmetic is the release-blocking golden-corpus
signal, so each numeric case pins an exact value.
"""

import math

import pytest
from pydantic import ValidationError
from spotdl_core.matching.scoring import (
    MATCHER_V5_DEFAULT,
    GateReason,
    GateRejection,
    HardGates,
    ScoreResult,
    ScoringConfig,
    SelectionConfig,
    score,
)
from spotdl_core.model import FeatureVector


# --------------------------------------------------------------------------- #
# fixture builder — "perfect" defaults, override per case
# --------------------------------------------------------------------------- #
def fv(
    *,
    title_similarity: float = 100.0,
    main_artist_similarity: float = 100.0,
    other_artist_similarity: float = 0.0,
    artist_similarity: float = 100.0,
    album_similarity: float | None = None,
    duration_delta_s: float = 0.0,
    duration_similarity: float = 100.0,
    isrc_equal: bool = False,
    verified_source: bool = False,
    common_word_overlap: bool = True,
    forbidden_words: tuple[str, ...] = (),
    explicit_mismatch: bool = False,
    popularity_prior: float = 0.0,
) -> FeatureVector:
    return FeatureVector(
        title_similarity=title_similarity,
        main_artist_similarity=main_artist_similarity,
        other_artist_similarity=other_artist_similarity,
        artist_similarity=artist_similarity,
        album_similarity=album_similarity,
        duration_delta_s=duration_delta_s,
        duration_similarity=duration_similarity,
        isrc_equal=isrc_equal,
        verified_source=verified_source,
        common_word_overlap=common_word_overlap,
        forbidden_words=forbidden_words,
        explicit_mismatch=explicit_mismatch,
        popularity_prior=popularity_prior,
    )


# --------------------------------------------------------------------------- #
# perfect features
# --------------------------------------------------------------------------- #
def test_perfect_features_scores_100_and_not_rejected() -> None:
    result = score(fv())
    assert result.rejected is False
    assert result.rejection is None
    assert math.isclose(result.score, 100.0)


# --------------------------------------------------------------------------- #
# gates fire with the right reason at their boundary
# --------------------------------------------------------------------------- #
def test_gate_no_common_word() -> None:
    result = score(fv(common_word_overlap=False))
    assert result.rejected is True
    assert result.score == 0.0
    assert result.rejection is not None
    assert result.rejection.gate is GateReason.NO_COMMON_WORD


def test_gate_common_word_disabled_passes() -> None:
    cfg = ScoringConfig(gates=HardGates(require_common_word=False))
    result = score(fv(common_word_overlap=False), cfg)
    assert result.rejected is False


def test_gate_title_boundary() -> None:
    # v4: name_match <= 60 -> skip. 60.0 gates, 60.01 passes gate 2.
    at = score(fv(title_similarity=60.0))
    assert at.rejected is True
    assert at.rejection is not None
    assert at.rejection.gate is GateReason.TITLE_TOO_LOW

    above = score(fv(title_similarity=60.01))
    assert above.rejected is False


def test_gate_artist_boundary() -> None:
    # v4: artists_match < 70 -> skip. 70.0 passes, 69.99 gates.
    at = score(fv(artist_similarity=70.0))
    assert at.rejected is False

    below = score(fv(artist_similarity=69.99))
    assert below.rejected is True
    assert below.rejection is not None
    assert below.rejection.gate is GateReason.ARTIST_TOO_LOW


def test_gate_duration_boundary() -> None:
    # v4: time_match < 25 -> skip. 25.0 passes gate 4, 24.99 gates.
    # average stays >= 75 so gate 5 (duration<50 AND average<75) does not fire.
    at = score(fv(duration_similarity=25.0))
    assert at.rejected is False

    below = score(fv(duration_similarity=24.99))
    assert below.rejected is True
    assert below.rejection is not None
    assert below.rejection.gate is GateReason.DURATION_TOO_LOW


def test_gate_duration_and_average_too_low() -> None:
    # v4: time_match < 50 AND average < 75 -> skip.
    # title=artist=70 -> average 70 (<75); duration 40 (<50, but >=25 so gate 4 ok).
    result = score(fv(title_similarity=70.0, artist_similarity=70.0, duration_similarity=40.0))
    assert result.rejected is True
    assert result.rejection is not None
    assert result.rejection.gate is GateReason.DURATION_AND_AVERAGE_TOO_LOW


# --------------------------------------------------------------------------- #
# forbidden-word penalty — per entry, matching v4's duplicated list
# --------------------------------------------------------------------------- #
def test_forbidden_single_entry_penalty_gates_title() -> None:
    # ("cover",) -> 61 - 15 = 46 <= 60 -> TITLE_TOO_LOW
    result = score(fv(title_similarity=61.0, forbidden_words=("cover",)))
    assert result.rejected is True
    assert result.rejection is not None
    assert result.rejection.gate is GateReason.TITLE_TOO_LOW


def test_forbidden_double_entry_penalty() -> None:
    # ("remix", "remix") costs -30.
    passes = score(fv(title_similarity=95.0, forbidden_words=("remix", "remix")))
    assert passes.rejected is False  # 95 - 30 = 65 > 60

    gated = score(fv(title_similarity=89.0, forbidden_words=("remix", "remix")))
    assert gated.rejected is True  # 89 - 30 = 59 <= 60
    assert gated.rejection is not None
    assert gated.rejection.gate is GateReason.TITLE_TOO_LOW


def test_forbidden_penalty_configurable() -> None:
    cfg = ScoringConfig(forbidden_word_penalty=10.0)
    # 61 - 10 = 51 <= 60 still gates on default title floor.
    gated = score(fv(title_similarity=61.0, forbidden_words=("cover",)), cfg)
    assert gated.rejected is True
    # 75 - 10 = 65 passes.
    ok = score(fv(title_similarity=75.0, forbidden_words=("cover",)), cfg)
    assert ok.rejected is False


# --------------------------------------------------------------------------- #
# album blend (verified only)
# --------------------------------------------------------------------------- #
def test_album_blend_lowers_verified_vs_unverified() -> None:
    unverified = score(fv(album_similarity=50.0, verified_source=False))
    verified = score(fv(album_similarity=50.0, verified_source=True))
    assert verified.score < unverified.score
    # verified: avg 100 blended with album 50 -> 75, then duration blend (75+100)/2 = 87.5
    assert math.isclose(verified.score, 87.5)
    # unverified: album ignored -> 100 (no duration blend since 100 > 85)
    assert math.isclose(unverified.score, 100.0)


def test_album_blend_skipped_above_ceiling() -> None:
    # album_similarity 90 > ceiling 80 -> no blend even when verified.
    result = score(fv(album_similarity=90.0, verified_source=True))
    assert math.isclose(result.score, 100.0)


def test_album_blend_none_skipped() -> None:
    result = score(fv(album_similarity=None, verified_source=True))
    assert math.isclose(result.score, 100.0)


# --------------------------------------------------------------------------- #
# duration blend + explicit mismatch
# --------------------------------------------------------------------------- #
def test_duration_blend_formula() -> None:
    # Reachable duration-blend case: average 80 (title=artist=80), duration 40.
    # gate 5 needs duration<50 AND average<75; 80 >= 75 so it does not fire.
    # blend: (80 + 40) / 2 = 60.
    result = score(fv(title_similarity=80.0, artist_similarity=80.0, duration_similarity=40.0))
    assert result.rejected is False
    assert math.isclose(result.score, 60.0)


def test_explicit_mismatch_only_inside_blend() -> None:
    # In blend branch: average 80, duration 40 -> 60, minus 5 = 55.
    penalized = score(
        fv(
            title_similarity=80.0,
            artist_similarity=80.0,
            duration_similarity=40.0,
            explicit_mismatch=True,
        )
    )
    assert math.isclose(penalized.score, 55.0)

    # No blend (average 100 > 85): explicit mismatch does nothing.
    no_blend = score(fv(explicit_mismatch=True))
    assert math.isclose(no_blend.score, 100.0)


# --------------------------------------------------------------------------- #
# configurable weights change the score
# --------------------------------------------------------------------------- #
def test_altered_weights_change_score() -> None:
    features = fv(title_similarity=60.01, artist_similarity=100.0, duration_similarity=100.0)
    default = score(features)
    tilted = ScoringConfig(matcher_version="v5.1-experiment", weight_title=0.2, weight_artist=0.8)
    experimental = score(features, tilted)
    assert not math.isclose(default.score, experimental.score)


# --------------------------------------------------------------------------- #
# serialization round-trip
# --------------------------------------------------------------------------- #
def test_config_json_round_trip_default() -> None:
    dumped = MATCHER_V5_DEFAULT.model_dump_json()
    loaded = ScoringConfig.model_validate_json(dumped)
    assert loaded == MATCHER_V5_DEFAULT


def test_config_json_round_trip_experiment() -> None:
    cfg = ScoringConfig(
        matcher_version="v5.1-experiment",
        weight_title=0.3,
        weight_artist=0.7,
        forbidden_word_penalty=20.0,
        gates=HardGates(min_title_similarity=55.0),
        selection=SelectionConfig(near_tie_window=5.0),
    )
    loaded = ScoringConfig.model_validate_json(cfg.model_dump_json())
    assert loaded == cfg
    assert loaded.matcher_version == "v5.1-experiment"


# --------------------------------------------------------------------------- #
# weight validator
# --------------------------------------------------------------------------- #
def test_invalid_weights_raise() -> None:
    with pytest.raises(ValidationError):
        ScoringConfig(weight_title=0.7, weight_artist=0.7)


def test_valid_nondefault_weights_allowed() -> None:
    cfg = ScoringConfig(weight_title=0.3, weight_artist=0.7)
    assert math.isclose(cfg.weight_title + cfg.weight_artist, 1.0)


# --------------------------------------------------------------------------- #
# frozen / immutability
# --------------------------------------------------------------------------- #
def test_models_are_frozen() -> None:
    with pytest.raises(ValidationError):
        MATCHER_V5_DEFAULT.weight_title = 0.9  # type: ignore[misc]
    result = ScoreResult(score=1.0, rejected=False)
    with pytest.raises(ValidationError):
        result.score = 2.0  # type: ignore[misc]


def test_gate_rejection_detail_is_populated() -> None:
    result = score(fv(title_similarity=10.0))
    assert result.rejection is not None
    assert isinstance(result.rejection, GateRejection)
    assert result.rejection.detail  # non-empty human-readable string
