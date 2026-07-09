"""Provider-agnostic track -> audio-candidate matching."""

from spotdl_core.matching.api import match, score_candidates
from spotdl_core.matching.features import extract_features
from spotdl_core.matching.scoring import (
    MATCHER_V5_DEFAULT,
    GateReason,
    GateRejection,
    ScoreResult,
    ScoringConfig,
)
from spotdl_core.matching.select import CandidateScore, select

__all__ = [
    "match",
    "score_candidates",
    "select",
    "CandidateScore",
    "ScoringConfig",
    "MATCHER_V5_DEFAULT",
    "ScoreResult",
    "GateReason",
    "GateRejection",
    "extract_features",
]
