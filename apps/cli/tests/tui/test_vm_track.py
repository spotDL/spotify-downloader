"""``TrackViewModel`` — the parity core: detail, matches, lyrics, voting, gating."""

from __future__ import annotations

from uuid import uuid4

import pytest
from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.errors import ApiError
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.track import TrackViewModel
from spotdl_cli.viewmodels.types import LyricsChoice, LyricsLine

from .fakes import (
    FakeSpotdlClient,
    make_lyrics,
    make_match,
    make_session,
    make_track,
)


async def test_load_maps_track_matches_lyrics() -> None:
    client = FakeSpotdlClient()
    track_id = uuid4()
    client.tracks[str(track_id)] = make_track(id=track_id, name="Verdis Quo", duration_ms=353_000)
    match_id = uuid4()
    client.matches_by_track[str(track_id)] = [
        make_match(
            id=match_id,
            status="community_verified",
            score=0.834,
            net_score=7,
            upvotes=9,
            downvotes=2,
            provider="youtube",
        )
    ]
    client.lyrics_by_track[str(track_id)] = [
        make_lyrics(kind="plain", source="genius", text="hello\nworld", net_score=1),
        make_lyrics(
            kind="synced",
            source="musixmatch",
            text="[00:01.00]first\n[00:03.50]second",
            net_score=5,
        ),
    ]

    result = await TrackViewModel(client, make_session()).load(track_id)

    assert result.state is LoadState.READY
    detail = result.data
    assert detail is not None
    assert detail.header.title == "Verdis Quo"
    assert detail.header.subtitle == "Artist"

    (match,) = detail.matches
    assert match.id == match_id
    assert match.score == 83  # 0.834 -> 83
    assert match.status == "community_verified"
    assert match.verified is True
    assert (match.upvotes, match.downvotes, match.net_score) == (9, 2, 7)

    # synced-first ordering
    assert [c.kind for c in detail.lyrics] == ["synced", "plain"]
    synced = detail.lyrics[0]
    assert synced.synced is True
    assert synced.lines == (
        LyricsLine(text="first", timestamp_ms=1000),
        LyricsLine(text="second", timestamp_ms=3500),
    )
    plain = detail.lyrics[1]
    assert plain.lines == (
        LyricsLine(text="hello", timestamp_ms=None),
        LyricsLine(text="world", timestamp_ms=None),
    )


def _synced_choice() -> LyricsChoice:
    return LyricsChoice(
        id=uuid4(),
        source="musixmatch",
        kind="synced",
        synced=True,
        net_score=1,
        lines=(
            LyricsLine("one", 1000),
            LyricsLine("two", 3000),
            LyricsLine("three", 5000),
        ),
    )


@pytest.mark.parametrize(
    ("position_ms", "expected"),
    [
        (0, None),  # before first
        (999, None),  # just before first
        (1000, 0),  # exactly first
        (2000, 0),  # between first and second
        (3000, 1),  # exactly second
        (4999, 1),  # between second and third
        (5000, 2),  # exactly third
        (100_000, 2),  # after last
    ],
)
def test_active_synced_line_boundaries(position_ms: int, expected: int | None) -> None:
    assert TrackViewModel.active_synced_line(_synced_choice(), position_ms) == expected


def test_active_synced_line_none_when_no_timestamps() -> None:
    choice = LyricsChoice(
        id=uuid4(),
        source="genius",
        kind="plain",
        synced=False,
        net_score=0,
        lines=(LyricsLine("x", None), LyricsLine("y", None)),
    )
    assert TrackViewModel.active_synced_line(choice, 5000) is None


async def test_vote_match_blocked_when_cannot_vote() -> None:
    client = FakeSpotdlClient()
    vm = TrackViewModel(client, make_session(can_vote=False))
    result = await vm.vote_match(uuid4(), "up")

    assert result.state is LoadState.ERROR
    assert not client.called("vote_match")  # no client call made


async def test_vote_match_maps_updated_row() -> None:
    client = FakeSpotdlClient()
    match_id = uuid4()
    client.vote_match_result = make_match(id=match_id, net_score=8, upvotes=10, downvotes=2)
    result = await TrackViewModel(client, make_session()).vote_match(match_id, "up")

    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.net_score == 8
    assert client.calls[-1] == ("vote_match", (match_id, "up"), {})


async def test_submit_match_requires_loaded_track() -> None:
    client = FakeSpotdlClient()
    vm = TrackViewModel(client, make_session())
    # not loaded yet
    result = await vm.submit_match("https://youtu.be/x")
    assert result.state is LoadState.ERROR
    assert not client.called("submit_match")


async def test_submit_match_maps_success_and_error() -> None:
    client = FakeSpotdlClient()
    track_id = uuid4()
    client.tracks[str(track_id)] = make_track(id=track_id)
    client.matches_by_track[str(track_id)] = []
    client.lyrics_by_track[str(track_id)] = []
    client.submit_match_result = make_match(status="auto")
    vm = TrackViewModel(client, make_session())
    await vm.load(track_id)

    ok = await vm.submit_match("https://youtu.be/x")
    assert ok.state is LoadState.READY
    assert client.calls[-1] == ("submit_match", (track_id, "https://youtu.be/x"), {})

    client.errors["submit_match"] = ApiError(ErrorCode.VALIDATION_ERROR, message="bad url")
    err = await vm.submit_match("nope")
    assert err.state is LoadState.ERROR
    assert err.error is not None
    assert err.error.code == "validation_error"


async def test_enqueue_blocked_when_cannot_download() -> None:
    client = FakeSpotdlClient()
    track_id = uuid4()
    client.tracks[str(track_id)] = make_track(id=track_id)
    client.matches_by_track[str(track_id)] = []
    client.lyrics_by_track[str(track_id)] = []
    vm = TrackViewModel(client, make_session(can_download=False))
    await vm.load(track_id)

    result = await vm.enqueue()
    assert result.state is LoadState.ERROR
    assert not client.called("submit_download")


async def test_enqueue_submits_track_id() -> None:
    from .fakes import make_batch

    client = FakeSpotdlClient()
    track_id = uuid4()
    client.tracks[str(track_id)] = make_track(id=track_id)
    client.matches_by_track[str(track_id)] = []
    client.lyrics_by_track[str(track_id)] = []
    batch_id = uuid4()
    client.submit_download_result = make_batch(batch_id=batch_id)
    vm = TrackViewModel(client, make_session())
    await vm.load(track_id)

    result = await vm.enqueue()
    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.batch_id == batch_id
    submit_call = next(c for c in client.calls if c[0] == "submit_download")
    assert submit_call[1][0].query == str(track_id)


async def test_report_maps_row() -> None:
    from .fakes import make_report

    client = FakeSpotdlClient()
    track_id = uuid4()
    client.tracks[str(track_id)] = make_track(id=track_id)
    client.matches_by_track[str(track_id)] = []
    client.lyrics_by_track[str(track_id)] = []
    client.report_result = make_report(subject_type="track", reason="wrong title")
    vm = TrackViewModel(client, make_session())
    await vm.load(track_id)

    result = await vm.report(field="title", proposed_value="Right", reason="wrong title")
    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.reason == "wrong title"
    report_call = next(c for c in client.calls if c[0] == "submit_report")
    assert report_call[1][0] == "track"
    assert report_call[1][1] == track_id
