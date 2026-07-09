"""Tests for ``spotdl_core.matching.select`` — ranking, ISRC rules, tiebreak.

Verbatim port of v4's ``get_best_matches`` + ``get_best_result`` + the
``base.search`` ISRC short-circuit. Selection accuracy is the release-blocking
golden-corpus signal, so every ordering rule is pinned:

  * ISRC rule A (unconditional): exactly one ISRC-equal candidate that is
    ``verified`` is pinned first even if it was gate-rejected (v4 returned it
    before scoring ran).
  * ISRC rule B (score-checked): the best ISRC-equal viable candidate scoring
    ``>= isrc_short_circuit_min_score`` wins even over a higher-scoring
    non-ISRC candidate.
  * Near-tie window + popularity tiebreak: within ``near_tie_window`` points of
    the best, higher ``popularity_prior`` ranks first; outside the window,
    score order is preserved and popularity is ignored.
"""

from spotdl_core.matching.scoring import (
    GateReason,
    GateRejection,
    ScoreResult,
)
from spotdl_core.matching.select import CandidateScore, select
from spotdl_core.model import AudioCandidate, FeatureVector, MatchStatus, ProviderId


# --------------------------------------------------------------------------- #
# builders
# --------------------------------------------------------------------------- #
def cand(
    provider_id: str = "x",
    *,
    verified: bool = False,
) -> AudioCandidate:
    return AudioCandidate(
        provider=ProviderId.YTMUSIC,
        provider_id=provider_id,
        url=f"https://example.test/{provider_id}",
        name="Song",
        artists=("Artist",),
        duration_ms=200_000,
        verified=verified,
    )


def fv(*, isrc_equal: bool = False, popularity_prior: float = 0.0) -> FeatureVector:
    return FeatureVector(
        title_similarity=100.0,
        main_artist_similarity=100.0,
        other_artist_similarity=0.0,
        artist_similarity=100.0,
        album_similarity=None,
        duration_delta_s=0.0,
        duration_similarity=100.0,
        isrc_equal=isrc_equal,
        verified_source=False,
        common_word_overlap=True,
        forbidden_words=(),
        explicit_mismatch=False,
        popularity_prior=popularity_prior,
    )


def cs(
    score: float,
    *,
    provider_id: str = "x",
    isrc_equal: bool = False,
    verified: bool = False,
    popularity_prior: float = 0.0,
    rejected: bool = False,
) -> CandidateScore:
    rejection = (
        GateRejection(gate=GateReason.DURATION_TOO_LOW, detail="gated") if rejected else None
    )
    return CandidateScore(
        candidate=cand(provider_id, verified=verified),
        features=fv(isrc_equal=isrc_equal, popularity_prior=popularity_prior),
        result=ScoreResult(score=score, rejected=rejected, rejection=rejection),
    )


def urls(matches: list) -> list[str]:
    return [m.candidate.provider_id for m in matches]


# --------------------------------------------------------------------------- #
# empty / all-rejected
# --------------------------------------------------------------------------- #
def test_empty_returns_empty() -> None:
    assert select(()) == []


def test_all_rejected_returns_empty() -> None:
    scored = (cs(0.0, provider_id="a", rejected=True), cs(0.0, provider_id="b", rejected=True))
    assert select(scored) == []


# --------------------------------------------------------------------------- #
# single viable
# --------------------------------------------------------------------------- #
def test_single_viable_preserves_base_score() -> None:
    matches = select((cs(87.5, provider_id="a"),))
    assert len(matches) == 1
    assert matches[0].candidate.provider_id == "a"
    assert matches[0].score == 87.5
    assert matches[0].status is MatchStatus.AUTO
    assert matches[0].matcher_version == "v5.0"
    assert matches[0].features is not None


# --------------------------------------------------------------------------- #
# ISRC rule A — unconditional (exactly one ISRC-equal, verified)
# --------------------------------------------------------------------------- #
def test_isrc_rule_a_returns_gated_verified_isrc_first() -> None:
    # The single ISRC-equal candidate is verified but was gate-rejected (score 0).
    # v4 returned it before scoring ran -> it is still pinned first.
    winner = cs(0.0, provider_id="isrc", isrc_equal=True, verified=True, rejected=True)
    other = cs(95.0, provider_id="other")
    matches = select((winner, other))
    assert urls(matches) == ["isrc", "other"]
    assert matches[0].score == 0.0  # honest computed score; pin is by ordering


def test_isrc_rule_a_requires_verified() -> None:
    # Same shape but not verified -> rule A does not fire; the gated ISRC
    # candidate is not viable, so only the non-ISRC candidate is returned.
    isrc = cs(0.0, provider_id="isrc", isrc_equal=True, verified=False, rejected=True)
    other = cs(95.0, provider_id="other")
    matches = select((isrc, other))
    assert urls(matches) == ["other"]


def test_isrc_rule_a_not_fired_with_two_isrc_equal() -> None:
    # Two ISRC-equal candidates -> rule A needs exactly one; falls through.
    a = cs(70.0, provider_id="a", isrc_equal=True, verified=True)
    b = cs(90.0, provider_id="b", isrc_equal=True, verified=True)
    matches = select((a, b))
    # Rule B fires (both >= 80? only b). b scores 90 >= 80 -> b wins.
    assert matches[0].candidate.provider_id == "b"


# --------------------------------------------------------------------------- #
# ISRC rule B — score-checked short-circuit
# --------------------------------------------------------------------------- #
def test_isrc_rule_b_beats_higher_non_isrc() -> None:
    isrc = cs(82.0, provider_id="isrc", isrc_equal=True)
    non_isrc = cs(95.0, provider_id="non")
    matches = select((non_isrc, isrc))
    assert matches[0].candidate.provider_id == "isrc"
    # rest is score-sorted: non-isrc (95) after the pinned isrc.
    assert urls(matches) == ["isrc", "non"]


def test_isrc_rule_b_below_threshold_does_not_short_circuit() -> None:
    # Two ISRC-equal candidates at 79 and 75: below isrc_short_circuit_min_score
    # (80) and not exactly-one-verified, so rank by score normally.
    a = cs(79.0, provider_id="a", isrc_equal=True)
    b = cs(75.0, provider_id="b", isrc_equal=True)
    matches = select((b, a))
    assert urls(matches) == ["a", "b"]


# --------------------------------------------------------------------------- #
# near-tie window + popularity tiebreak
# --------------------------------------------------------------------------- #
def test_near_tie_popularity_reorders_within_window() -> None:
    # 90 and 88 are within 8 points; higher popularity ranks first.
    top = cs(90.0, provider_id="top", popularity_prior=0.2)
    pop = cs(88.0, provider_id="pop", popularity_prior=0.9)
    matches = select((top, pop))
    assert urls(matches) == ["pop", "top"]


def test_outside_window_preserves_score_order() -> None:
    # 90 and 78 differ by 12 (> 8): popularity ignored, score order preserved.
    top = cs(90.0, provider_id="top", popularity_prior=0.2)
    low = cs(78.0, provider_id="low", popularity_prior=0.9)
    matches = select((top, low))
    assert urls(matches) == ["top", "low"]


def test_no_popularity_variance_preserves_score_order() -> None:
    # Equal popularity within window -> no reorder (v4 highest in (0, lowest)).
    a = cs(90.0, provider_id="a", popularity_prior=0.5)
    b = cs(88.0, provider_id="b", popularity_prior=0.5)
    matches = select((a, b))
    assert urls(matches) == ["a", "b"]


def test_tail_outside_window_kept_in_score_order() -> None:
    # Window {90, 88} reordered by popularity; tail {70} appended after.
    top = cs(90.0, provider_id="top", popularity_prior=0.2)
    pop = cs(88.0, provider_id="pop", popularity_prior=0.9)
    tail = cs(70.0, provider_id="tail", popularity_prior=1.0)
    matches = select((tail, top, pop))
    assert urls(matches) == ["pop", "top", "tail"]


def test_base_score_preserved_despite_popularity_reorder() -> None:
    # Popularity affects ordering only, not the persisted score.
    top = cs(90.0, provider_id="top", popularity_prior=0.2)
    pop = cs(88.0, provider_id="pop", popularity_prior=0.9)
    matches = select((top, pop))
    scores = {m.candidate.provider_id: m.score for m in matches}
    assert scores == {"top": 90.0, "pop": 88.0}
