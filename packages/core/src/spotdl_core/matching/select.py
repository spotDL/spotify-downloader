"""Ranking + ISRC rules + popularity tiebreak — verbatim port of v4 selection.

This is the ``select`` sub-module: it turns a bag of already-scored candidates
into a ranked ``list[Match]``. The arithmetic is a verbatim structural port of
spotDL v4's ``base.search`` ISRC short-circuit, ``get_best_result``, and
``get_best_matches`` (network parts removed — ``popularity`` replaces the
``get_views`` tiebreak, and there is no "search" step here).

Two ISRC rules, in v4 order:

* **Rule A — unconditional.** v4's ``base.search`` returned the single ISRC
  result immediately when there was *exactly one* and it was ``verified``, with
  no score check, before ``order_results`` (scoring/gating) ever ran. So rule A
  is evaluated over **all** scored candidates (including gate-rejected ones) and
  pins the winner first even if it scored 0. The pin is expressed by *ordering*;
  ``Match.score`` stays the honest computed value.
* **Rule B — score-checked.** v4's ``best_isrc[1] > 80`` path (folded together
  with ``get_best_result``'s ``best > 80 and isrc_search`` early return): the
  best *viable* ISRC-equal candidate scoring ``>= isrc_short_circuit_min_score``
  wins even over a higher-scoring non-ISRC candidate.

If neither ISRC rule fires, rank by score, take the near-tie window (within
``near_tie_window`` points of the best, per v4 ``get_best_matches``), and apply
the popularity tiebreak inside that window (v4 ``get_best_result`` views
normalization, with ``popularity_prior`` in place of ``views``).

**Documented deviation from v4:** the persisted ``Match.score`` is always the
*base* score. Popularity affects **ordering only**, never the stored number
(v4 returned the views-adjusted score for the winner only; storing base scores
keeps the field meaning consistent across the whole returned list). Likewise, in
the no-popularity-variance branch v4 reused ``best_result`` as its loop variable
and returned the *last-iterated* near-tie entry; v5 preserves score order
instead. (The corpus recorder still replicates v4's buggy behavior — Task 8.)
"""

from pydantic import BaseModel, ConfigDict

from spotdl_core.matching.scoring import (
    MATCHER_V5_DEFAULT,
    ScoreResult,
    ScoringConfig,
)
from spotdl_core.model import AudioCandidate, FeatureVector, Match, MatchStatus

__all__ = ["CandidateScore", "select"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class CandidateScore(_Frozen):
    """One candidate paired with its extracted features and scoring result."""

    candidate: AudioCandidate
    features: FeatureVector
    result: ScoreResult


def _to_match(cs: CandidateScore, config: ScoringConfig) -> Match:
    return Match(
        candidate=cs.candidate,
        score=cs.result.score,
        matcher_version=config.matcher_version,
        status=MatchStatus.AUTO,
        features=cs.features,
    )


def select(
    scored: tuple[CandidateScore, ...], config: ScoringConfig = MATCHER_V5_DEFAULT
) -> list[Match]:
    """Rank scored candidates into ``list[Match]`` (viable-only, head = best)."""
    sel = config.selection
    viable = [cs for cs in scored if not cs.result.rejected]

    def match(cs: CandidateScore) -> Match:
        return _to_match(cs, config)

    # ISRC rule A — unconditional (v4 base.search: exactly one ISRC result and it
    # is verified -> return it with NO score check, before any scoring/gating).
    # Evaluated over ALL scored candidates (incl. gate-rejected).
    isrc_all = [cs for cs in scored if cs.features.isrc_equal]
    if len(isrc_all) == 1 and isrc_all[0].candidate.verified:
        winner = isrc_all[0]
        rest = sorted(
            (cs for cs in viable if cs is not winner),
            key=lambda cs: cs.result.score,
            reverse=True,
        )
        return [match(winner)] + [match(cs) for cs in rest]

    if not viable:
        return []

    # ISRC rule B — score-checked short-circuit (v4 base.search: best ISRC result
    # with score > 80 -> return it even if a non-ISRC result scores higher).
    isrc_hits = [
        cs
        for cs in viable
        if cs.features.isrc_equal and cs.result.score >= sel.isrc_short_circuit_min_score
    ]
    if isrc_hits:
        winner = max(isrc_hits, key=lambda cs: cs.result.score)
        rest = sorted(
            (cs for cs in viable if cs is not winner),
            key=lambda cs: cs.result.score,
            reverse=True,
        )
        return [match(winner)] + [match(cs) for cs in rest]

    ordered = sorted(viable, key=lambda cs: cs.result.score, reverse=True)
    best = ordered[0].result.score

    # Near-tie window (v4 get_best_matches: within 8 points of the best).
    window = [cs for cs in ordered if best - cs.result.score <= sel.near_tie_window]
    tail = ordered[len(window) :]

    if len(window) > 1:
        # Popularity tiebreak (v4 get_best_result views normalization, popularity
        # in place of views). Only engages when popularity actually differs.
        pops = [cs.features.popularity_prior for cs in window]
        hi, lo = max(pops), min(pops)
        if hi not in (0.0, lo):

            def adjusted(cs: CandidateScore) -> float:
                norm = (cs.features.popularity_prior - lo) / (hi - lo)
                return min(cs.result.score + norm * sel.popularity_tiebreak_weight, 100.0)

            window = sorted(window, key=adjusted, reverse=True)

    return [match(cs) for cs in (window + tail)]
