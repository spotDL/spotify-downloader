from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from pydantic import ValidationError
from spotdl_core.download.context import (
    BITRATE_AUTO,
    BITRATE_DISABLE,
    DownloadConfig,
    DownloadContext,
    DownloadOutcome,
    DownloadRequest,
    OutcomeStatus,
    OutputFormat,
    OverwriteMode,
    ProgressCallback,
    ProgressEvent,
    ProgressPhase,
    RestrictMode,
    SkipReason,
)
from spotdl_core.model import AudioCandidate, Lyrics, LyricsKind, ProviderId, Track


@pytest.fixture
def track() -> Track:
    return Track(
        name="Placeholder Song",
        artists=("Placeholder Artist",),
        duration_ms=210_000,
        provider=ProviderId.SPOTIFY,
        provider_id="track123",
    )


@pytest.fixture
def candidate() -> AudioCandidate:
    return AudioCandidate(
        provider=ProviderId.YTMUSIC,
        provider_id="yt123",
        url="https://music.youtube.com/watch?v=yt123",
        name="Placeholder Song",
    )


@pytest.fixture
def request_(track: Track, candidate: AudioCandidate) -> DownloadRequest:
    return DownloadRequest(track=track, candidate=candidate, output_template="")


# --- enum string values (CONTRACT) ---------------------------------------


def test_output_format_values() -> None:
    assert OutputFormat.MP3 == "mp3"
    assert OutputFormat.M4A == "m4a"
    assert OutputFormat.FLAC == "flac"
    assert OutputFormat.OGG == "ogg"
    assert OutputFormat.OPUS == "opus"
    assert OutputFormat.WAV == "wav"
    assert {f.value for f in OutputFormat} == {"mp3", "m4a", "flac", "ogg", "opus", "wav"}


def test_overwrite_mode_values() -> None:
    assert OverwriteMode.SKIP == "skip"
    assert OverwriteMode.FORCE == "force"
    assert OverwriteMode.METADATA == "metadata"
    assert {m.value for m in OverwriteMode} == {"skip", "force", "metadata"}


def test_restrict_mode_values() -> None:
    assert RestrictMode.NONE == "none"
    assert RestrictMode.ASCII == "ascii"
    assert RestrictMode.STRICT == "strict"
    assert {m.value for m in RestrictMode} == {"none", "ascii", "strict"}


def test_skip_reason_values() -> None:
    assert SkipReason.ALREADY_EXISTS == "already_exists"
    assert SkipReason.SKIP_FILE == "skip_file"
    assert SkipReason.IN_ARCHIVE == "in_archive"
    assert SkipReason.EXPLICIT_FILTERED == "explicit_filtered"
    assert {r.value for r in SkipReason} == {
        "already_exists",
        "skip_file",
        "in_archive",
        "explicit_filtered",
    }


def test_outcome_status_values() -> None:
    assert OutcomeStatus.DOWNLOADED == "downloaded"
    assert OutcomeStatus.SKIPPED == "skipped"
    assert OutcomeStatus.FAILED == "failed"
    assert {s.value for s in OutcomeStatus} == {"downloaded", "skipped", "failed"}


def test_progress_phase_values() -> None:
    assert ProgressPhase.PLAN == "plan"
    assert ProgressPhase.FETCH == "fetch"
    assert ProgressPhase.CONVERT == "convert"
    assert ProgressPhase.EMBED == "embed"
    assert ProgressPhase.POST == "post"
    assert ProgressPhase.DONE == "done"
    assert ProgressPhase.SKIPPED == "skipped"
    assert ProgressPhase.ERROR == "error"
    assert {p.value for p in ProgressPhase} == {
        "plan",
        "fetch",
        "convert",
        "embed",
        "post",
        "done",
        "skipped",
        "error",
    }


def test_bitrate_constants() -> None:
    assert BITRATE_AUTO == "auto"
    assert BITRATE_DISABLE == "disable"


# --- request round-trip + defaults ---------------------------------------


def test_request_defaults(request_: DownloadRequest) -> None:
    assert request_.output_format is OutputFormat.MP3
    assert request_.bitrate == BITRATE_AUTO
    assert request_.overwrite is OverwriteMode.SKIP
    assert request_.restrict is RestrictMode.NONE
    assert request_.max_filename_length is None
    assert request_.lyrics is None
    assert request_.embed_lyrics is True
    assert request_.skip_album_art is False
    assert request_.retain_track_cover is False
    assert request_.id3_separator == "/"
    assert request_.track_url is None
    assert request_.generate_lrc is False
    assert request_.sponsor_block is False
    assert request_.respect_skip_file is False
    assert request_.create_skip_file is False
    assert request_.skip_explicit is False
    assert request_.archive == frozenset()
    assert request_.known_paths == ()
    assert request_.detect_formats == ()
    assert request_.list_name is None
    assert request_.list_position is None
    assert request_.list_length is None


def test_request_round_trips(request_: DownloadRequest) -> None:
    dumped = request_.model_dump()
    rebuilt = DownloadRequest.model_validate(dumped)
    assert rebuilt == request_


def test_request_is_frozen(request_: DownloadRequest) -> None:
    with pytest.raises(ValidationError):
        request_.output_format = OutputFormat.FLAC  # type: ignore[misc]


def test_request_carries_lyrics(track: Track, candidate: AudioCandidate) -> None:
    lyrics = Lyrics(kind=LyricsKind.PLAIN, text="la la la", source=ProviderId.LRCLIB)
    req = DownloadRequest(
        track=track,
        candidate=candidate,
        output_template="{title}",
        lyrics=lyrics,
        archive=frozenset({"https://open.spotify.com/track/abc"}),
        known_paths=(Path("/music/dup.mp3"),),
        detect_formats=(OutputFormat.M4A,),
    )
    assert req.lyrics == lyrics
    assert "https://open.spotify.com/track/abc" in req.archive
    assert req.known_paths == (Path("/music/dup.mp3"),)
    assert req.detect_formats == (OutputFormat.M4A,)


# --- config ---------------------------------------------------------------


def test_config_defaults() -> None:
    cfg = DownloadConfig(output_dir=Path("/out"), temp_dir=Path("/tmp/x"))
    assert cfg.output_dir == Path("/out")
    assert cfg.temp_dir == Path("/tmp/x")
    assert cfg.ffmpeg_path == "ffmpeg"
    assert cfg.cookie_file is None
    assert cfg.proxy is None
    assert cfg.ytdlp_args == ()
    assert cfg.ffmpeg_args == ()


def test_config_is_frozen() -> None:
    cfg = DownloadConfig(output_dir=Path("/out"), temp_dir=Path("/tmp/x"))
    with pytest.raises(FrozenInstanceError):
        cfg.ffmpeg_path = "/usr/bin/ffmpeg"  # type: ignore[misc]


# --- context immutability -------------------------------------------------


def test_context_defaults(request_: DownloadRequest) -> None:
    ctx = DownloadContext(request=request_)
    assert ctx.request is request_
    assert ctx.output_path is None
    assert ctx.temp_path is None
    assert ctx.final_path is None
    assert ctx.source_url is None
    assert ctx.source_abr is None
    assert ctx.source_info is None
    assert ctx.skip_reason is None


def test_context_updated_returns_new_frozen_context(request_: DownloadRequest) -> None:
    ctx = DownloadContext(request=request_)
    new = ctx.updated(output_path=Path("/out/song.mp3"), source_abr=256.0)

    # a new object, original untouched
    assert new is not ctx
    assert ctx.output_path is None
    assert ctx.source_abr is None

    # changed fields applied
    assert new.output_path == Path("/out/song.mp3")
    assert new.source_abr == 256.0

    # everything else preserved
    assert new.request is request_
    assert new.temp_path is None
    assert new.skip_reason is None


def test_context_is_frozen(request_: DownloadRequest) -> None:
    ctx = DownloadContext(request=request_)
    with pytest.raises(ValidationError):
        ctx.output_path = Path("/out/song.mp3")  # type: ignore[misc]


def test_context_holds_raw_info(request_: DownloadRequest) -> None:
    info = {"abr": 320, "id": "yt123"}
    ctx = DownloadContext(request=request_, source_info=info)
    assert ctx.source_info == info


# --- outcome factory helpers ---------------------------------------------


def test_outcome_downloaded(track: Track) -> None:
    out = DownloadOutcome.downloaded(track, Path("/out/song.mp3"))
    assert out.status is OutcomeStatus.DOWNLOADED
    assert out.track is track
    assert out.path == Path("/out/song.mp3")
    assert out.skip_reason is None
    assert out.failed_step is None
    assert out.error is None


def test_outcome_skipped(track: Track) -> None:
    out = DownloadOutcome.skipped(track, SkipReason.ALREADY_EXISTS, Path("/out/song.mp3"))
    assert out.status is OutcomeStatus.SKIPPED
    assert out.track is track
    assert out.skip_reason is SkipReason.ALREADY_EXISTS
    assert out.path == Path("/out/song.mp3")
    assert out.failed_step is None
    assert out.error is None


def test_outcome_skipped_without_path(track: Track) -> None:
    out = DownloadOutcome.skipped(track, SkipReason.IN_ARCHIVE)
    assert out.status is OutcomeStatus.SKIPPED
    assert out.skip_reason is SkipReason.IN_ARCHIVE
    assert out.path is None


def test_outcome_failed(track: Track) -> None:
    out = DownloadOutcome.failed(track, step="fetch", error="yt-dlp exploded")
    assert out.status is OutcomeStatus.FAILED
    assert out.track is track
    assert out.failed_step == "fetch"
    assert out.error == "yt-dlp exploded"
    assert out.path is None
    assert out.skip_reason is None


def test_outcome_is_frozen(track: Track) -> None:
    out = DownloadOutcome.downloaded(track, Path("/out/song.mp3"))
    with pytest.raises(ValidationError):
        out.status = OutcomeStatus.FAILED  # type: ignore[misc]


# --- progress callback seam ----------------------------------------------


def test_progress_event_defaults() -> None:
    ev = ProgressEvent(phase=ProgressPhase.FETCH)
    assert ev.phase is ProgressPhase.FETCH
    assert ev.percent is None
    assert ev.message is None


def test_progress_event_is_frozen() -> None:
    ev = ProgressEvent(phase=ProgressPhase.FETCH, percent=50, message="downloading")
    with pytest.raises(ValidationError):
        ev.percent = 60  # type: ignore[misc]


def test_progress_callback_is_invokable() -> None:
    seen: list[ProgressEvent] = []

    def fake(event: ProgressEvent) -> None:
        seen.append(event)

    cb: ProgressCallback = fake
    cb(ProgressEvent(phase=ProgressPhase.CONVERT, percent=42, message="converting"))

    assert len(seen) == 1
    assert seen[0].phase is ProgressPhase.CONVERT
    assert seen[0].percent == 42
    assert seen[0].message == "converting"
