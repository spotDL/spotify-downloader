"""Public matching entry points: ``score_candidates`` + ``match``.

``match()`` is the ONE public entry the spec calls for (spec §6.2
``GET /tracks/{id}/matches`` returns a ranked list with scores). It is exactly
``select(tuple(score_candidates(...)), config)``.

``score_candidates()`` is the explainability hook: it returns a
``CandidateScore`` for **every** candidate — including gate-rejected ones with a
populated ``result.rejection`` — so a server can inspect why any candidate lost.
``match()`` then keeps only the viable ones, ranked.
"""

from spotdl_core.matching.features import extract_features
from spotdl_core.matching.scoring import MATCHER_V5_DEFAULT, ScoringConfig, score
from spotdl_core.matching.select import CandidateScore, select
from spotdl_core.model import AudioCandidate, Match, Track

__all__ = ["score_candidates", "match"]


def score_candidates(
    track: Track,
    candidates: tuple[AudioCandidate, ...] | list[AudioCandidate],
    config: ScoringConfig = MATCHER_V5_DEFAULT,
) -> list[CandidateScore]:
    """Score every candidate (incl. rejected) for server-side explainability."""
    scored: list[CandidateScore] = []
    for candidate in candidates:
        features = extract_features(track, candidate)
        result = score(features, config)
        scored.append(CandidateScore(candidate=candidate, features=features, result=result))
    return scored


def match(
    track: Track,
    candidates: tuple[AudioCandidate, ...] | list[AudioCandidate],
    config: ScoringConfig = MATCHER_V5_DEFAULT,
) -> list[Match]:
    """Rank candidates into viable-only ``list[Match]`` (the one public entry)."""
    return select(tuple(score_candidates(track, candidates, config)), config)
