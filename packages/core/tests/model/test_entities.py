import pytest
from pydantic import ValidationError
from spotdl_core.model import (
    AlbumRef,
    AudioCandidate,
    FeatureVector,
    Match,
    MatchStatus,
    ProviderId,
    Track,
)


def make_track() -> Track:
    return Track(
        name="Song Name",
        artists=("Main Artist", "Feat Artist"),
        duration_ms=200_000,
        album=AlbumRef(name="Album Name", year=2020),
        isrc="USUM72000001",
    )


def test_track_main_artist_is_first_artist() -> None:
    assert make_track().main_artist == "Main Artist"


def test_track_requires_at_least_one_artist() -> None:
    with pytest.raises(ValidationError):
        Track(name="x", artists=(), duration_ms=1000)


def test_track_is_immutable() -> None:
    track = make_track()
    with pytest.raises(ValidationError):
        track.name = "changed"  # type: ignore[misc]


def make_feature_vector() -> FeatureVector:
    return FeatureVector(
        title_similarity=98.0,
        main_artist_similarity=100.0,
        other_artist_similarity=90.0,
        artist_similarity=95.0,
        album_similarity=88.0,
        duration_delta_s=2.0,
        duration_similarity=97.5,
        isrc_equal=True,
        verified_source=True,
        common_word_overlap=True,
        forbidden_words=("remix", "remix"),
        explicit_mismatch=False,
        popularity_prior=0.42,
    )


def test_feature_vector_carries_split_artist_signals() -> None:
    fv = make_feature_vector()
    assert fv.main_artist_similarity == 100.0
    assert fv.other_artist_similarity == 90.0
    assert fv.artist_similarity == 95.0
    assert fv.duration_similarity == 97.5
    assert fv.common_word_overlap is True
    assert fv.forbidden_words == ("remix", "remix")


def test_feature_vector_album_similarity_can_be_none() -> None:
    fv = make_feature_vector().model_copy(update={"album_similarity": None})
    assert fv.album_similarity is None


def test_feature_vector_is_immutable() -> None:
    fv = make_feature_vector()
    with pytest.raises(ValidationError):
        fv.title_similarity = 0.0  # type: ignore[misc]


def test_match_defaults_to_auto_status() -> None:
    candidate = AudioCandidate(
        provider=ProviderId.YTMUSIC,
        provider_id="abc123",
        url="https://music.youtube.com/watch?v=abc123",
        name="Song Name",
    )
    match = Match(candidate=candidate, score=91.5, matcher_version="v5.0")
    assert match.status is MatchStatus.AUTO
    assert match.features is None
