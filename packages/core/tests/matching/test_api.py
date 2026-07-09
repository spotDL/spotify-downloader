"""Tests for ``spotdl_core.matching.api`` — ``score_candidates`` + ``match``.

``match()`` is the single public entry point (``select(score_candidates(...))``).
``score_candidates()`` is the explainability hook: it returns a
``CandidateScore`` for **every** candidate, including gate-rejected ones with a
populated ``result.rejection``, so a server can explain why a candidate lost.
"""

from spotdl_core.matching.api import match, score_candidates
from spotdl_core.matching.select import CandidateScore
from spotdl_core.model import AudioCandidate, Match, ProviderId, Track


def track(
    name: str = "Song",
    artists: tuple[str, ...] = ("Artist",),
    duration_ms: int = 200_000,
    isrc: str | None = None,
) -> Track:
    return Track(name=name, artists=artists, duration_ms=duration_ms, isrc=isrc)


def cand(
    provider_id: str,
    *,
    name: str = "Song",
    artists: tuple[str, ...] = ("Artist",),
    duration_ms: int | None = 200_000,
    isrc: str | None = None,
    verified: bool = False,
    popularity: int | None = None,
) -> AudioCandidate:
    return AudioCandidate(
        provider=ProviderId.YTMUSIC,
        provider_id=provider_id,
        url=f"https://example.test/{provider_id}",
        name=name,
        artists=artists,
        duration_ms=duration_ms,
        isrc=isrc,
        verified=verified,
        popularity=popularity,
    )


# --------------------------------------------------------------------------- #
# match() end-to-end
# --------------------------------------------------------------------------- #
def test_match_returns_good_first_and_drops_gated() -> None:
    good = cand("good")
    # remix-trap: gated on duration (10s vs 200s -> duration_similarity ~ 0).
    remix = cand("remix", name="Song Remix", duration_ms=10_000)
    # wrong-artist: gated on artist floor.
    wrong = cand("wrong", artists=("Nobody Else Entirely",))

    matches = match(track(), (good, remix, wrong))

    assert all(isinstance(m, Match) for m in matches)
    assert matches[0].candidate.provider_id == "good"
    returned = {m.candidate.provider_id for m in matches}
    assert "remix" not in returned
    assert "wrong" not in returned
    assert returned == {"good"}


def test_match_empty_candidates_returns_empty() -> None:
    assert match(track(), ()) == []


def test_match_accepts_list_or_tuple() -> None:
    good = cand("good")
    as_list = match(track(), [good])
    as_tuple = match(track(), (good,))
    assert [m.candidate.provider_id for m in as_list] == ["good"]
    assert [m.candidate.provider_id for m in as_tuple] == ["good"]


def test_match_stores_base_score_and_features() -> None:
    matches = match(track(), (cand("good"),))
    assert len(matches) == 1
    assert matches[0].score == 100.0
    assert matches[0].features is not None
    assert matches[0].matcher_version == "v5.0"


# --------------------------------------------------------------------------- #
# score_candidates() — explainability hook
# --------------------------------------------------------------------------- #
def test_score_candidates_includes_rejected_with_rejection() -> None:
    good = cand("good")
    wrong = cand("wrong", artists=("Nobody Else Entirely",))

    scored = score_candidates(track(), (good, wrong))

    assert all(isinstance(cs, CandidateScore) for cs in scored)
    by_id = {cs.candidate.provider_id: cs for cs in scored}
    assert set(by_id) == {"good", "wrong"}

    assert by_id["good"].result.rejected is False
    assert by_id["wrong"].result.rejected is True
    assert by_id["wrong"].result.rejection is not None
    assert by_id["wrong"].result.rejection.detail


def test_score_candidates_returns_every_candidate() -> None:
    cands = tuple(cand(f"c{i}") for i in range(4))
    scored = score_candidates(track(), cands)
    assert len(scored) == 4


def test_score_candidates_features_populated() -> None:
    scored = score_candidates(track(), (cand("good"),))
    assert scored[0].features.title_similarity == 100.0
    assert scored[0].features.artist_similarity == 100.0


# --------------------------------------------------------------------------- #
# ISRC end-to-end through match()
# --------------------------------------------------------------------------- #
def test_match_isrc_rule_a_pins_single_verified_isrc() -> None:
    # One verified ISRC-equal candidate that is otherwise gated (bad duration)
    # is still pinned first via rule A.
    isrc = cand("isrc", isrc="USABC1234567", verified=True, duration_ms=10_000)
    other = cand("other")
    matches = match(track(isrc="US-ABC-12-34567"), (isrc, other))
    assert matches[0].candidate.provider_id == "isrc"
