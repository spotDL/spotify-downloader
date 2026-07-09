"""Tests for ``spotdl_core.download.fetch`` — yt-dlp audio fetch behind an
injectable seam.

The default suite is fully offline: the ``Fetcher`` seam is filled with a fake
that hands back a real (tiny, synthetic-silence) media file, so ``FetchStep`` is
exercised end-to-end without touching the network. The pure helpers
(``ytdl_format_for``, ``build_ytdlp_options``, the progress adapter) are
unit-tested directly; ``build_ytdlp_options`` uses yt-dlp's ``parse_options``,
which is import-only (no network).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from spotdl_core.download.context import (
    DownloadConfig,
    DownloadContext,
    DownloadRequest,
    OutputFormat,
    ProgressEvent,
    ProgressPhase,
)
from spotdl_core.download.fetch import (
    FetchResult,
    FetchStep,
    YtDlpFetcher,
    build_ytdlp_options,
    make_ytdlp_progress_hook,
    ytdl_format_for,
    ytdlp_progress_event,
)
from spotdl_core.model import AudioCandidate, ProviderId, Track
from spotdl_core.providers.errors import AudioFetchFailed

FIXTURES = Path(__file__).parent / "fixtures"


# --- fixtures -------------------------------------------------------------


def _candidate() -> AudioCandidate:
    return AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt123",
        url="https://youtube.com/watch?v=yt123",
        name="Song Name",
    )


def _track() -> Track:
    return Track(
        name="Song Name",
        artists=("Main Artist",),
        duration_ms=214_000,
        provider=ProviderId.SPOTIFY,
        provider_id="sp123",
    )


def _request() -> DownloadRequest:
    return DownloadRequest(
        track=_track(),
        candidate=_candidate(),
        output_template="",
        output_format=OutputFormat.M4A,
    )


def _config(tmp_path: Path) -> DownloadConfig:
    return DownloadConfig(output_dir=tmp_path / "out", temp_dir=tmp_path / "temp")


class _FakeFetcher:
    """Offline seam: copies the committed tiny fixture into ``temp_dir`` and
    returns a populated ``FetchResult``. Records the args it was called with."""

    def __init__(self, tmp_path: Path) -> None:
        self._tmp = tmp_path
        self.calls: list[dict[str, Any]] = []

    async def fetch(
        self,
        candidate: AudioCandidate,
        *,
        output_format: OutputFormat,
        temp_dir: Path,
        on_progress: Any = None,
    ) -> FetchResult:
        self.calls.append(
            {"candidate": candidate, "output_format": output_format, "temp_dir": temp_dir}
        )
        dest = self._tmp / "yt123.m4a"
        shutil.copyfile(FIXTURES / "tiny.m4a", dest)
        return FetchResult(
            path=dest,
            ext="m4a",
            source_url=candidate.url,
            abr=129.0,
            info={"id": "yt123", "ext": "m4a", "abr": 129.0},
        )


class _RaisingFetcher:
    async def fetch(
        self,
        candidate: AudioCandidate,
        *,
        output_format: OutputFormat,
        temp_dir: Path,
        on_progress: Any = None,
    ) -> FetchResult:
        raise RuntimeError("boom from yt-dlp")


# --- ytdl_format_for ------------------------------------------------------


def test_ytdl_format_for_m4a() -> None:
    assert ytdl_format_for(OutputFormat.M4A) == "bestaudio[ext=m4a]/bestaudio/best"


def test_ytdl_format_for_opus() -> None:
    assert ytdl_format_for(OutputFormat.OPUS) == "bestaudio[ext=webm]/bestaudio/best"


@pytest.mark.parametrize(
    "fmt", [OutputFormat.MP3, OutputFormat.FLAC, OutputFormat.OGG, OutputFormat.WAV]
)
def test_ytdl_format_for_others(fmt: OutputFormat) -> None:
    assert ytdl_format_for(fmt) == "bestaudio"


# --- build_ytdlp_options --------------------------------------------------


def test_build_ytdlp_options_basics(tmp_path: Path) -> None:
    config = _config(tmp_path)
    temp_dir = tmp_path / "temp"
    opts = build_ytdlp_options(config, OutputFormat.M4A, temp_dir)

    assert opts["format"] == "bestaudio[ext=m4a]/bestaudio/best"
    assert "cookiefile" in opts
    assert str(temp_dir.resolve()) in opts["outtmpl"]
    assert opts["outtmpl"].endswith("%(id)s.%(ext)s")


def test_build_ytdlp_options_cookiefile_and_proxy(tmp_path: Path) -> None:
    cookie = tmp_path / "cookies.txt"
    cookie.write_text("# netscape cookie file\n")
    config = DownloadConfig(
        output_dir=tmp_path / "out",
        temp_dir=tmp_path / "temp",
        cookie_file=cookie,
        proxy="http://127.0.0.1:8080",
    )
    opts = build_ytdlp_options(config, OutputFormat.MP3, tmp_path / "temp")
    assert opts["cookiefile"] == str(cookie)
    assert opts["proxy"] == "http://127.0.0.1:8080"


def test_build_ytdlp_options_no_proxy_omits_key(tmp_path: Path) -> None:
    opts = build_ytdlp_options(_config(tmp_path), OutputFormat.MP3, tmp_path / "temp")
    assert "proxy" not in opts
    assert opts["cookiefile"] is None


def test_build_ytdlp_options_merges_passthrough_args(tmp_path: Path) -> None:
    config = DownloadConfig(
        output_dir=tmp_path / "out",
        temp_dir=tmp_path / "temp",
        ytdlp_args=("--no-check-certificates",),
    )
    opts = build_ytdlp_options(config, OutputFormat.MP3, tmp_path / "temp")
    # user passthrough is honoured
    assert opts["nocheckcertificate"] is True
    # our defaults survive the merge
    assert opts["format"] == "bestaudio"
    assert opts["outtmpl"].endswith("%(id)s.%(ext)s")


# --- progress adapter -----------------------------------------------------


def test_progress_event_downloading_with_totals() -> None:
    event = ytdlp_progress_event(
        {"status": "downloading", "downloaded_bytes": 25, "total_bytes": 100}
    )
    assert event == ProgressEvent(phase=ProgressPhase.FETCH, percent=25)


def test_progress_event_uses_estimate_when_total_missing() -> None:
    event = ytdlp_progress_event(
        {"status": "downloading", "downloaded_bytes": 50, "total_bytes_estimate": 200}
    )
    assert event is not None
    assert event.percent == 25


def test_progress_event_downloading_without_totals_has_no_percent() -> None:
    event = ytdlp_progress_event({"status": "downloading", "downloaded_bytes": 10})
    assert event is not None
    assert event.phase is ProgressPhase.FETCH
    assert event.percent is None


def test_progress_event_finished_is_full() -> None:
    event = ytdlp_progress_event({"status": "finished"})
    assert event == ProgressEvent(phase=ProgressPhase.FETCH, percent=100)


def test_progress_event_unknown_status_is_none() -> None:
    assert ytdlp_progress_event({"status": "error"}) is None


def test_make_ytdlp_progress_hook_invokes_callback() -> None:
    seen: list[ProgressEvent] = []
    hook = make_ytdlp_progress_hook(seen.append)
    hook({"status": "downloading", "downloaded_bytes": 30, "total_bytes": 60})
    hook({"status": "unknown-noise"})  # ignored, no event
    assert seen == [ProgressEvent(phase=ProgressPhase.FETCH, percent=50)]


def test_make_ytdlp_progress_hook_swallows_callback_errors() -> None:
    def _boom(_event: ProgressEvent) -> None:
        raise ValueError("callback exploded")

    hook = make_ytdlp_progress_hook(_boom)
    # progress must never raise into the pipeline
    hook({"status": "downloading", "downloaded_bytes": 1, "total_bytes": 2})


# --- FetchStep ------------------------------------------------------------


async def test_fetch_step_success(tmp_path: Path) -> None:
    fetcher = _FakeFetcher(tmp_path)
    ctx = DownloadContext(request=_request())
    step = FetchStep(fetcher, temp_dir=tmp_path / "temp")

    result = await step(ctx)

    assert result.temp_path is not None
    assert result.temp_path.exists()
    assert result.source_url == "https://youtube.com/watch?v=yt123"
    assert result.source_abr == 129.0
    assert result.source_info == {"id": "yt123", "ext": "m4a", "abr": 129.0}
    # the step forwarded the request's output format to the fetcher
    assert fetcher.calls[0]["output_format"] is OutputFormat.M4A
    assert fetcher.calls[0]["candidate"] is ctx.request.candidate


async def test_fetch_step_wraps_errors_as_audio_fetch_failed(tmp_path: Path) -> None:
    step = FetchStep(_RaisingFetcher(), temp_dir=tmp_path / "temp")
    ctx = DownloadContext(request=_request())

    with pytest.raises(AudioFetchFailed) as excinfo:
        await step(ctx)
    assert excinfo.value.step == "fetch"
    assert "boom from yt-dlp" in str(excinfo.value)


async def test_fetch_step_passes_through_audio_fetch_failed(tmp_path: Path) -> None:
    class _AlreadyWrapped:
        async def fetch(self, candidate: Any, **_: Any) -> FetchResult:
            raise AudioFetchFailed("already typed")

    step = FetchStep(_AlreadyWrapped(), temp_dir=tmp_path / "temp")
    with pytest.raises(AudioFetchFailed) as excinfo:
        await step(DownloadContext(request=_request()))
    assert str(excinfo.value) == "already typed"


# --- YtDlpFetcher (offline: no download; missing-metadata + error mapping) --


async def test_ytdlp_fetcher_maps_errors_to_audio_fetch_failed(tmp_path: Path) -> None:
    """Without patching the network, a bogus URL must surface as
    ``AudioFetchFailed`` rather than a raw yt-dlp exception. We monkeypatch the
    lazily-imported extractor so no real request is made."""
    fetcher = YtDlpFetcher(_config(tmp_path))

    class _FakeYDL:
        def __init__(self, _opts: dict[str, Any]) -> None:
            pass

        def __enter__(self) -> _FakeYDL:
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def add_progress_hook(self, _hook: Any) -> None:
            pass

        def extract_info(self, _url: str, download: bool = False) -> dict[str, Any]:
            raise RuntimeError("HTTP Error 403: Forbidden")

    import spotdl_core.download.fetch as fetch_mod

    orig = fetch_mod._youtube_dl
    fetch_mod._youtube_dl = lambda: _FakeYDL  # type: ignore[attr-defined]
    try:
        with pytest.raises(AudioFetchFailed) as excinfo:
            await fetcher.fetch(
                _candidate(),
                output_format=OutputFormat.MP3,
                temp_dir=tmp_path / "temp",
            )
    finally:
        fetch_mod._youtube_dl = orig  # type: ignore[attr-defined]
    assert excinfo.value.step == "fetch"


async def test_ytdlp_fetcher_builds_result_from_info(tmp_path: Path) -> None:
    """Drive the happy path with a fake YoutubeDL that 'downloads' by writing
    the expected temp file, proving id/ext/abr wiring without the network."""
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True)
    fetcher = YtDlpFetcher(_config(tmp_path))

    class _FakeYDL:
        def __init__(self, _opts: dict[str, Any]) -> None:
            pass

        def __enter__(self) -> _FakeYDL:
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def add_progress_hook(self, _hook: Any) -> None:
            pass

        def extract_info(self, _url: str, download: bool = False) -> dict[str, Any]:
            shutil.copyfile(FIXTURES / "tiny.m4a", temp_dir / "abc.m4a")
            return {
                "id": "abc",
                "ext": "m4a",
                "abr": 130.5,
                "original_url": "https://music.youtube.com/watch?v=abc",
            }

    import spotdl_core.download.fetch as fetch_mod

    orig = fetch_mod._youtube_dl
    fetch_mod._youtube_dl = lambda: _FakeYDL  # type: ignore[attr-defined]
    try:
        result = await fetcher.fetch(
            _candidate(), output_format=OutputFormat.M4A, temp_dir=temp_dir
        )
    finally:
        fetch_mod._youtube_dl = orig  # type: ignore[attr-defined]

    assert result.path == temp_dir / "abc.m4a"
    assert result.path.exists()
    assert result.ext == "m4a"
    assert result.abr == 130.5
    assert result.source_url == "https://music.youtube.com/watch?v=abc"
