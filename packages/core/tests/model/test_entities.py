import pytest
from pydantic import ValidationError
from spotdl_core.model import (
    AlbumRef,
    AudioCandidate,
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
