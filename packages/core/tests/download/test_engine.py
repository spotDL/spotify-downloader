"""Tests for ``spotdl_core.download.engine`` — the ``DownloadEngine`` that
composes the plan/fetch/convert/embed/post pipeline into
``download(request, on_progress)``.

The external audio fetch, cover download, synced-lyrics search, and SponsorBlock
seams are all faked, so every case here is fully offline. Pure-plan cases (skip
decisions, metadata-only re-embed, the move fast path) need no ffmpeg; the two
re-encode/end-to-end cases are gated behind the ``requires_ffmpeg`` autoskip
fixture and operate on the committed tiny synthetic-silence fixtures.

``DownloadEngine.download(request, on_progress=None) -> DownloadOutcome`` is a
CONTRACT (spec §5.4; Plan 7's worker calls exactly this): per-track failures
never raise out of ``download`` — they are returned as a ``FAILED`` outcome
tagged with the failing step.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from spotdl_core.download.context import (
    BITRATE_AUTO,
    BITRATE_DISABLE,
    DownloadConfig,
    DownloadRequest,
    OutcomeStatus,
    OutputFormat,
    OverwriteMode,
    ProgressEvent,
    ProgressPhase,
    SkipReason,
)
from spotdl_core.download.engine import DownloadEngine
from spotdl_core.download.fetch import FetchResult
from spotdl_core.download.paths import build_output_path
from spotdl_core.model import AlbumRef, AudioCandidate, Lyrics, LyricsKind, ProviderId, Track
from spotdl_core.providers.errors import AudioFetchFailed

FIXTURES = Path(__file__).parent / "fixtures"

SYNCED_LRC = "[00:01.00]First synced line\n[00:12.34]Second synced line"
TRACK_URL = "https://open.spotify.com/track/sp123"
SOURCE_URL = "https://music.youtube.com/watch?v=abc123"


# --- offline seams --------------------------------------------------------


class FakeFetcher:
    """Offline ``Fetcher`` that copies a committed fixture into the temp dir.

    Records every call so tests can assert the fetcher was (not) invoked, and can
    be told to raise instead — modelling a yt-dlp failure.
    """

    def __init__(
        self,
        *,
        source: Path = FIXTURES / "tiny.m4a",
        ext: str = "m4a",
        abr: float | None = None,
        error: Exception | None = None,
    ) -> None:
        self._source = source
        self._ext = ext
        self._abr = abr
        self._error = error
        self.calls: list[AudioCandidate] = []

    async def fetch(
        self,
        candidate: AudioCandidate,
        *,
        output_format: OutputFormat,
        temp_dir: Path,
        on_progress: Any = None,
    ) -> FetchResult:
        self.calls.append(candidate)
        if self._error is not None:
            raise self._error
        temp_dir.mkdir(parents=True, exist_ok=True)
        dest = temp_dir / f"faketrack.{self._ext}"
        shutil.copy(self._source, dest)
        if on_progress is not None:
            on_progress(ProgressEvent(phase=ProgressPhase.FETCH, percent=100))
        return FetchResult(
            path=dest,
            ext=self._ext,
            source_url=candidate.url,
            abr=self._abr,
            info={"id": "faketrack", "ext": self._ext},
        )


class ProgressRecorder:
    """Collects every :class:`ProgressEvent` the pipeline emits."""

    def __init__(self) -> None:
        self.events: list[ProgressEvent] = []

    def __call__(self, event: ProgressEvent) -> None:
        self.events.append(event)

    def phases(self) -> list[ProgressPhase]:
        return [event.phase for event in self.events]


# --- fixtures / builders --------------------------------------------------


def _track(*, explicit: bool = False) -> Track:
    return Track(
        name="Test Song",
        artists=("Test Artist",),
        duration_ms=1_000,
        album=AlbumRef(name="Test Album", album_artist="Test Artist"),
        explicit=explicit,
        provider=ProviderId.SPOTIFY,
        provider_id="sp123",
    )


def _candidate() -> AudioCandidate:
    return AudioCandidate(
        provider=ProviderId.YTMUSIC,
        provider_id="abc123",
        url=SOURCE_URL,
        name="Test Song",
    )


def _request(**overrides: Any) -> DownloadRequest:
    base: dict[str, Any] = {
        "track": _track(),
        "candidate": _candidate(),
        "output_template": "",
        "output_format": OutputFormat.MP3,
        "track_url": TRACK_URL,
    }
    base.update(overrides)
    return DownloadRequest(**base)


def _config(tmp_path: Path, **overrides: Any) -> DownloadConfig:
    params: dict[str, Any] = {
        "output_dir": tmp_path / "out",
        "temp_dir": tmp_path / "tmp",
        "ffmpeg_path": "ffmpeg",
    }
    params.update(overrides)
    return DownloadConfig(**params)


def _engine(config: DownloadConfig, fetcher: FakeFetcher | None = None) -> DownloadEngine:
    return DownloadEngine(config, fetcher=fetcher if fetcher is not None else FakeFetcher())


# --- happy path (requires ffmpeg) -----------------------------------------


async def test_happy_path_downloads_and_reports_progress(
    tmp_path: Path, requires_ffmpeg: None
) -> None:
    config = _config(tmp_path)
    fetcher = FakeFetcher()
    request = _request(output_format=OutputFormat.MP3)
    progress = ProgressRecorder()

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request, progress)

    expected = build_output_path(request, config)
    assert outcome.status is OutcomeStatus.DOWNLOADED
    assert outcome.path == expected
    assert expected.exists()
    assert expected.suffix == ".mp3"
    assert fetcher.calls  # the fetch seam was exercised

    # Real ID3 tags were embedded (offline mutagen on the converted mp3).
    from mutagen.id3 import ID3

    tags = ID3(str(expected))
    assert tags.getall("TIT2")[0].text[0] == "Test Song"

    # FETCH -> CONVERT -> EMBED -> DONE appears in order among emitted phases.
    phases = progress.phases()
    for phase in (
        ProgressPhase.FETCH,
        ProgressPhase.CONVERT,
        ProgressPhase.EMBED,
        ProgressPhase.DONE,
    ):
        assert phase in phases
    assert (
        phases.index(ProgressPhase.FETCH)
        < phases.index(ProgressPhase.CONVERT)
        < phases.index(ProgressPhase.EMBED)
        < phases.index(ProgressPhase.DONE)
    )


# --- skip decisions (no ffmpeg needed) ------------------------------------


async def test_skip_already_exists_without_fetching(tmp_path: Path) -> None:
    config = _config(tmp_path)
    request = _request(overwrite=OverwriteMode.SKIP)
    output_path = build_output_path(request, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"pre-existing")
    fetcher = FakeFetcher()

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    assert outcome.status is OutcomeStatus.SKIPPED
    assert outcome.skip_reason is SkipReason.ALREADY_EXISTS
    assert fetcher.calls == []  # never fetched
    assert output_path.read_bytes() == b"pre-existing"  # untouched


async def test_skip_in_archive_without_fetching(tmp_path: Path) -> None:
    config = _config(tmp_path)
    request = _request(archive=frozenset({TRACK_URL}))
    fetcher = FakeFetcher()

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    assert outcome.status is OutcomeStatus.SKIPPED
    assert outcome.skip_reason is SkipReason.IN_ARCHIVE
    assert fetcher.calls == []


async def test_skip_when_skip_sidecar_present(tmp_path: Path) -> None:
    config = _config(tmp_path)
    request = _request(respect_skip_file=True)
    output_path = build_output_path(request, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Path(str(output_path.absolute()) + ".skip").write_text("")
    fetcher = FakeFetcher()

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    assert outcome.status is OutcomeStatus.SKIPPED
    assert outcome.skip_reason is SkipReason.SKIP_FILE
    assert fetcher.calls == []


async def test_skip_explicit_track(tmp_path: Path) -> None:
    config = _config(tmp_path)
    request = _request(track=_track(explicit=True), skip_explicit=True)
    fetcher = FakeFetcher()

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    assert outcome.status is OutcomeStatus.SKIPPED
    assert outcome.skip_reason is SkipReason.EXPLICIT_FILTERED
    assert fetcher.calls == []


# --- metadata-only branch (offline: m4a + real mutagen) -------------------


async def test_metadata_only_reembeds_without_fetching(tmp_path: Path) -> None:
    config = _config(tmp_path)
    request = _request(output_format=OutputFormat.M4A, overwrite=OverwriteMode.METADATA)
    output_path = build_output_path(request, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "tiny.m4a", output_path)  # a real, valid m4a
    fetcher = FakeFetcher(error=AssertionError("fetch must not run in metadata mode"))

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    assert outcome.status is OutcomeStatus.DOWNLOADED
    assert outcome.path == output_path
    assert fetcher.calls == []  # metadata-only never fetches

    from mutagen.mp4 import MP4

    audio = MP4(str(output_path))
    assert audio["\xa9nam"] == ["Test Song"]


# --- failure isolation ----------------------------------------------------


async def test_fetch_failure_is_isolated(tmp_path: Path) -> None:
    config = _config(tmp_path)
    fetcher = FakeFetcher(error=AudioFetchFailed("yt-dlp exploded"))
    request = _request()

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    assert outcome.status is OutcomeStatus.FAILED
    assert outcome.failed_step == "fetch"
    assert outcome.error
    assert "exploded" in outcome.error


async def test_embed_failure_is_isolated(tmp_path: Path) -> None:
    config = _config(tmp_path)
    # Opus bytes carried under an .m4a name are not a valid MP4 container, so the
    # (move-fast-path) embed step raises MetadataEmbedFailed -> failed_step "embed".
    fetcher = FakeFetcher(source=FIXTURES / "tiny.opus", ext="m4a")
    request = _request(output_format=OutputFormat.M4A, bitrate=BITRATE_DISABLE)

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    assert outcome.status is OutcomeStatus.FAILED
    assert outcome.failed_step == "embed"
    assert outcome.error


async def test_unexpected_error_reported_as_unknown_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    fetcher = FakeFetcher(ext="m4a")
    request = _request(output_format=OutputFormat.M4A, bitrate=BITRATE_DISABLE)

    class BoomEmbed:
        def __init__(self, *args: Any, **kwargs: Any) -> None: ...

        async def __call__(self, ctx: Any) -> Any:
            raise RuntimeError("something nobody typed")  # not a DownloadFailed

    # A bare, non-DownloadFailed error escaping a step lands in the catch-all
    # bucket and is reported as step "unknown" (never propagates).
    monkeypatch.setattr("spotdl_core.download.engine.EmbedStep", BoomEmbed)

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    assert outcome.status is OutcomeStatus.FAILED
    assert outcome.failed_step == "unknown"
    assert outcome.error


async def test_conversion_failure_is_isolated(tmp_path: Path) -> None:
    config = _config(tmp_path, ffmpeg_path="/nonexistent/ffmpeg")
    fetcher = FakeFetcher()  # m4a fixture
    request = _request(output_format=OutputFormat.MP3, bitrate=BITRATE_AUTO)

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    assert outcome.status is OutcomeStatus.FAILED
    assert outcome.failed_step == "convert"
    assert outcome.error
    # A partial output must not be left behind.
    assert not build_output_path(request, config).exists()


# --- move fast path (offline: m4a copy) -----------------------------------


async def test_move_fast_path_relocates_file(tmp_path: Path) -> None:
    config = _config(tmp_path)
    fetcher = FakeFetcher(ext="m4a")
    request = _request(output_format=OutputFormat.M4A, bitrate=BITRATE_DISABLE)

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    output_path = build_output_path(request, config)
    assert outcome.status is OutcomeStatus.DOWNLOADED
    assert output_path.exists()
    # The temp file was consumed by the move (no leftover temp audio).
    assert list(config.temp_dir.glob("*.m4a")) == []


async def test_create_skip_file_written_on_success(tmp_path: Path) -> None:
    config = _config(tmp_path)
    fetcher = FakeFetcher(ext="m4a")
    request = _request(
        output_format=OutputFormat.M4A, bitrate=BITRATE_DISABLE, create_skip_file=True
    )

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    output_path = build_output_path(request, config)
    assert outcome.status is OutcomeStatus.DOWNLOADED
    assert Path(str(output_path.absolute()) + ".skip").exists()


async def test_generate_lrc_written_from_synced_request_lyrics(tmp_path: Path) -> None:
    config = _config(tmp_path)
    fetcher = FakeFetcher(ext="m4a")
    lyrics = Lyrics(kind=LyricsKind.SYNCED, text=SYNCED_LRC, source=ProviderId.LRCLIB)
    request = _request(
        output_format=OutputFormat.M4A,
        bitrate=BITRATE_DISABLE,
        generate_lrc=True,
        lyrics=lyrics,
    )

    outcome = await DownloadEngine(config, fetcher=fetcher).download(request)

    output_path = build_output_path(request, config)
    assert outcome.status is OutcomeStatus.DOWNLOADED
    lrc_path = output_path.with_suffix(".lrc")
    assert lrc_path.exists()
    assert lrc_path.read_text(encoding="utf-8") == SYNCED_LRC
