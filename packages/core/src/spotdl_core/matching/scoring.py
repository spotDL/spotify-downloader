"""Versioned, serializable scoring config, typed hard gates, and ``score()``.

This is a **structural** redesign of spotDL v4's ``order_results`` per-result
combination, not an arithmetic one: the thresholds, the ``(artist + name) / 2``
core, the conditional album/duration blends, the forbidden-word penalty, and the
explicit-mismatch penalty are ported verbatim from v4 and expressed as the
frozen, serializable ``MATCHER_V5_DEFAULT`` config so every constant is
explicitly recalibratable per ``matcher_version`` (spec §6.1 / §9 A/B).

Dropped v4 guards (intentional, lossless for v1 providers): the extra branches
keyed on ``result.isrc_search`` and ``result.source == "slider.kz"`` and the dead
``time_match < 0`` branch. v5 has no search-source concept and no slider.kz
provider; the ISRC preference moves to ``matching.select`` (Task 6).
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

from spotdl_core.model import FeatureVector

__all__ = [
    "GateReason",
    "GateRejection",
    "HardGates",
    "SelectionConfig",
    "ScoringConfig",
    "ScoreResult",
    "MATCHER_V5_DEFAULT",
    "score",
]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class GateReason(StrEnum):
    """The hard gate that rejected a candidate (v4 short-circuits on the first)."""

    NO_COMMON_WORD = "no_common_word"
    TITLE_TOO_LOW = "title_too_low"
    ARTIST_TOO_LOW = "artist_too_low"
    DURATION_TOO_LOW = "duration_too_low"
    DURATION_AND_AVERAGE_TOO_LOW = "duration_and_average_too_low"


class GateRejection(_Frozen):
    gate: GateReason
    detail: str  # human-readable, e.g. "title 42.0 <= 60.0"


class HardGates(_Frozen):
    require_common_word: bool = True
    min_title_similarity: float = 60.0  # v4: name_match <= 60 -> skip
    min_artist_similarity: float = 70.0  # v4: artists_match < 70 -> skip
    min_duration_similarity: float = 25.0  # v4: time_match < 25 -> skip
    low_duration_similarity: float = 50.0  # v4: time_match < 50 ...
    low_average_threshold: float = 75.0  # v4: ... and average < 75 -> skip


class SelectionConfig(_Frozen):
    isrc_short_circuit_min_score: float = 80.0  # v4: ISRC best > 80 -> return
    near_tie_window: float = 8.0  # v4: get_best_matches threshold
    popularity_tiebreak_weight: float = 15.0  # v4: views_score max +15


class ScoringConfig(_Frozen):
    matcher_version: str = "v5.0"
    # combination weights (v4 core is a plain (artist + name) / 2 average)
    weight_title: float = 0.5
    weight_artist: float = 0.5
    # forbidden-word penalty magnitude, applied to title before combination
    forbidden_word_penalty: float = 15.0  # v4: name_match -= 15 per word
    # conditional blends (all v4-faithful)
    album_blend_when_verified: bool = True
    album_blend_ceiling: float = 80.0  # v4: verified & album <= 80 -> blend
    duration_blend_ceiling: float = 85.0  # v4: average <= 85 -> blend time
    explicit_mismatch_penalty: float = 5.0  # v4: -5 on explicit mismatch
    gates: HardGates = HardGates()
    selection: SelectionConfig = SelectionConfig()

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "ScoringConfig":
        # weight_title + weight_artist must equal 1.0 so the default equals v4's
        # (artist + name) / 2; a malformed config must fail loudly rather than
        # silently rescaling.
        total = self.weight_title + self.weight_artist
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"weight_title + weight_artist must sum to 1.0, got {total}")
        return self


class ScoreResult(_Frozen):
    score: float  # 0..100
    rejected: bool
    rejection: GateRejection | None = None  # first gate that fired (v4 short-circuits)


MATCHER_V5_DEFAULT: ScoringConfig = ScoringConfig()


def score(features: FeatureVector, config: ScoringConfig = MATCHER_V5_DEFAULT) -> ScoreResult:
    """Score one candidate's feature vector; verbatim port of v4 ``order_results``.

    Hard gates short-circuit on the first failure, exactly like v4, returning a
    ``ScoreResult`` with ``score=0.0`` and the ``GateRejection`` that fired.
    """
    g = config.gates

    # Gate 1: common word (v4 check_common_word skip).
    if g.require_common_word and not features.common_word_overlap:
        return ScoreResult(
            score=0.0,
            rejected=True,
            rejection=GateRejection(gate=GateReason.NO_COMMON_WORD, detail="no shared title word"),
        )

    # Title with forbidden-word penalty (v4: name_match -= 15 per matched entry).
    title = features.title_similarity - config.forbidden_word_penalty * len(
        features.forbidden_words
    )
    artist = features.artist_similarity

    # Gate 2: title floor (v4: name_match <= 60) -- uses the penalized value.
    if title <= g.min_title_similarity:
        return ScoreResult(
            score=0.0,
            rejected=True,
            rejection=GateRejection(
                gate=GateReason.TITLE_TOO_LOW,
                detail=f"title {title} <= {g.min_title_similarity}",
            ),
        )

    # Gate 3: artist floor (v4: artists_match < 70).
    if artist < g.min_artist_similarity:
        return ScoreResult(
            score=0.0,
            rejected=True,
            rejection=GateRejection(
                gate=GateReason.ARTIST_TOO_LOW,
                detail=f"artist {artist} < {g.min_artist_similarity}",
            ),
        )

    # Core combination: (artist + title) / 2 == v4 with weight_title = weight_artist = 0.5.
    average = artist * config.weight_artist + title * config.weight_title

    # Album blend for verified results (v4: verified & album & album <= 80).
    if (
        config.album_blend_when_verified
        and features.verified_source
        and features.album_similarity is not None
        and features.album_similarity <= config.album_blend_ceiling
    ):
        average = (average + features.album_similarity) / 2

    # Gate 4: duration floor (v4: time_match < 25).
    if features.duration_similarity < g.min_duration_similarity:
        return ScoreResult(
            score=0.0,
            rejected=True,
            rejection=GateRejection(
                gate=GateReason.DURATION_TOO_LOW,
                detail=f"duration {features.duration_similarity} < {g.min_duration_similarity}",
            ),
        )

    # Gate 5: weak duration + weak average (v4: time < 50 and average < 75).
    if (
        features.duration_similarity < g.low_duration_similarity
        and average < g.low_average_threshold
    ):
        return ScoreResult(
            score=0.0,
            rejected=True,
            rejection=GateRejection(
                gate=GateReason.DURATION_AND_AVERAGE_TOO_LOW,
                detail=(
                    f"duration {features.duration_similarity} < {g.low_duration_similarity} "
                    f"and average {average} < {g.low_average_threshold}"
                ),
            ),
        )

    # Duration blend when not already confident (v4: average <= 85 -> blend time;
    # then the explicit-mismatch penalty applies only inside this branch).
    if average <= config.duration_blend_ceiling:
        average = (average + features.duration_similarity) / 2
        if features.explicit_mismatch:
            average -= config.explicit_mismatch_penalty

    return ScoreResult(score=min(average, 100.0), rejected=False, rejection=None)
