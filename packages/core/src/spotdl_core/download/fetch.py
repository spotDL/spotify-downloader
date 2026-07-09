"""yt-dlp audio fetch behind an injectable seam.

The download pipeline reaches yt-dlp only through the :class:`Fetcher` protocol,
so the default test suite fills it with a fake and never touches the network.
:class:`FetchStep` is the pipeline-facing adapter; :class:`YtDlpFetcher` is the
concrete, network-backed implementation.

``Fetcher`` / ``FetchResult`` / ``FetchStep`` are a CONTRACT (Plan 4 Task 5 and
Plan 7 wiring). ``YtDlpFetcher``'s internals (option dict, extractor args) are
implementation and mirror v4's ``spotdl/providers/audio/base.py``. The actual
``yt_dlp`` import is deferred to call time so ``import spotdl_core.download.fetch``
works — and the default suite runs — without yt-dlp doing any network I/O.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from spotdl_core.download.context import (
    DownloadConfig,
    DownloadContext,
    OutputFormat,
    ProgressCallback,
    ProgressEvent,
    ProgressPhase,
)
from spotdl_core.model import AudioCandidate
from spotdl_core.providers.errors import AudioFetchFailed

if TYPE_CHECKING:
    from yt_dlp import YoutubeDL  # type: ignore[import-untyped]

__all__ = [
    "FetchResult",
    "FetchStep",
    "Fetcher",
    "YtDlpFetcher",
    "build_ytdlp_options",
    "make_ytdlp_progress_hook",
    "ytdl_format_for",
    "ytdlp_progress_event",
]


# --- result / protocol ----------------------------------------------------


class FetchResult(BaseModel):
    """Outcome of fetching one audio candidate into the temp dir."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    path: Path  # downloaded file in the temp dir
    ext: str  # container extension without dot (e.g. "webm", "m4a")
    source_url: str  # the URL yt-dlp actually fetched
    abr: float | None = None  # average audio bitrate reported by yt-dlp (kbps)
    info: dict[str, Any] = {}  # raw yt-dlp info dict (SponsorBlock input)


@runtime_checkable
class Fetcher(Protocol):
    """Seam over audio fetching. The default suite injects a fake."""

    async def fetch(
        self,
        candidate: AudioCandidate,
        *,
        output_format: OutputFormat,
        temp_dir: Path,
        on_progress: ProgressCallback | None = None,
    ) -> FetchResult: ...


# --- format selection (pure) ----------------------------------------------


def ytdl_format_for(output_format: OutputFormat) -> str:
    """yt-dlp ``format`` selector per output container (port of v4 base provider).

    Prefer a same-container source so the move-not-reencode fast path (Task 6)
    can apply, then fall back to any best audio.
    """
    if output_format is OutputFormat.M4A:
        return "bestaudio[ext=m4a]/bestaudio/best"
    if output_format is OutputFormat.OPUS:
        return "bestaudio[ext=webm]/bestaudio/best"
    return "bestaudio"


# --- progress adapter -----------------------------------------------------


def ytdlp_progress_event(data: dict[str, Any]) -> ProgressEvent | None:
    """Map a raw yt-dlp progress dict to a FETCH :class:`ProgressEvent`.

    Returns ``None`` for statuses that carry no meaningful progress. ``percent``
    is left ``None`` when yt-dlp has not reported a total size yet.
    """
    status = data.get("status")
    if status == "downloading":
        total = data.get("total_bytes") or data.get("total_bytes_estimate")
        downloaded = data.get("downloaded_bytes")
        percent: int | None = None
        if total and downloaded is not None:
            percent = max(0, min(100, int(downloaded / total * 100)))
        return ProgressEvent(phase=ProgressPhase.FETCH, percent=percent)
    if status == "finished":
        return ProgressEvent(phase=ProgressPhase.FETCH, percent=100)
    return None


def make_ytdlp_progress_hook(
    on_progress: ProgressCallback,
) -> Callable[[dict[str, Any]], None]:
    """Wrap a :class:`ProgressCallback` into a yt-dlp progress hook.

    Progress is best-effort: a raising callback must never abort the download.
    """

    def hook(data: dict[str, Any]) -> None:
        event = ytdlp_progress_event(data)
        if event is None:
            return
        # progress is best-effort: a raising callback must never abort a download
        with contextlib.suppress(Exception):
            on_progress(event)

    return hook


# --- yt-dlp option building -----------------------------------------------


def _youtube_dl() -> type[YoutubeDL]:
    """Lazily import ``YoutubeDL`` (kept out of module import time)."""
    from yt_dlp import YoutubeDL

    return YoutubeDL  # type: ignore[no-any-return]


def _merge_ytdlp_args(args: tuple[str, ...], defaults: dict[str, Any]) -> dict[str, Any]:
    """Port of v4 ``args_to_ytdlp_options``: parse passthrough CLI args and layer
    our defaults over them, but let a user-provided value win only when it
    differs from yt-dlp's own default for that key."""
    from yt_dlp import parse_options

    parsed: dict[str, Any] = parse_options(list(args)).ydl_opts
    default_options: dict[str, Any] = parse_options([]).ydl_opts

    for key, value in defaults.items():
        # add our default when the user did not set the key, or overrode it back
        # to yt-dlp's own default (v4 args_to_ytdlp_options semantics)
        if key not in parsed or parsed[key] == default_options.get(key):
            parsed[key] = value

    return parsed


def build_ytdlp_options(
    config: DownloadConfig, output_format: OutputFormat, temp_dir: Path
) -> dict[str, Any]:
    """Assemble the ``YoutubeDL`` options dict (port of v4 base-provider init).

    ``temp_dir`` drives ``outtmpl`` so fetched files land beside the pipeline's
    temp area. ``cookiefile``/``proxy``/passthrough args all flow from
    :class:`DownloadConfig`.
    """
    options: dict[str, Any] = {
        "format": ytdl_format_for(output_format),
        "quiet": True,
        "no_warnings": True,
        "encoding": "UTF-8",
        "cookiefile": str(config.cookie_file) if config.cookie_file else None,
        "outtmpl": str((temp_dir / "%(id)s.%(ext)s").resolve()),
        "retries": 5,
        "extractor_args": {},
    }

    if config.proxy:
        options["proxy"] = config.proxy

    if config.ytdlp_args:
        options = _merge_ytdlp_args(config.ytdlp_args, options)

    return options


# --- concrete yt-dlp fetcher ----------------------------------------------


class YtDlpFetcher:
    """Concrete :class:`Fetcher` backed by yt-dlp (lazily imported)."""

    def __init__(self, config: DownloadConfig) -> None:
        self._config = config

    async def fetch(
        self,
        candidate: AudioCandidate,
        *,
        output_format: OutputFormat,
        temp_dir: Path,
        on_progress: ProgressCallback | None = None,
    ) -> FetchResult:
        temp_dir.mkdir(parents=True, exist_ok=True)
        options = build_ytdlp_options(self._config, output_format, temp_dir)
        youtube_dl = _youtube_dl()

        def _run() -> dict[str, Any]:
            with youtube_dl(options) as ydl:
                if on_progress is not None:
                    ydl.add_progress_hook(make_ytdlp_progress_hook(on_progress))
                info = ydl.extract_info(candidate.url, download=True)
            if not info:
                raise AudioFetchFailed(f"yt-dlp returned no metadata for {candidate.url}")
            return info  # type: ignore[no-any-return]

        try:
            info = await asyncio.to_thread(_run)
        except AudioFetchFailed:
            raise
        except Exception as exc:  # noqa: BLE001 - normalise every yt-dlp failure
            raise AudioFetchFailed(f"yt-dlp download error for {candidate.url}: {exc}") from exc

        info_id = info.get("id")
        ext = info.get("ext")
        if not info_id or not ext:
            raise AudioFetchFailed(f"yt-dlp metadata missing id/ext for {candidate.url}")

        path = temp_dir / f"{info_id}.{ext}"
        if not path.exists():
            raise AudioFetchFailed(f"yt-dlp did not produce expected file {path}")

        abr = info.get("abr")
        source_url = info.get("original_url") or info.get("webpage_url") or candidate.url
        return FetchResult(
            path=path,
            ext=str(ext),
            source_url=str(source_url),
            abr=float(abr) if abr is not None else None,
            info=info,
        )


# --- pipeline step --------------------------------------------------------


class FetchStep:
    """Pipeline adapter around a :class:`Fetcher`.

    The CONTRACT constructor is ``(fetcher, on_progress=None)``. ``temp_dir`` is
    an additional keyword-only injection (default: :func:`tempfile.gettempdir`)
    supplied by the engine (Task 9) from ``DownloadConfig.temp_dir`` — the
    context/protocol require a temp dir but the frozen ``DownloadContext`` does
    not carry one, so the step is told where to place fetched audio.
    """

    def __init__(
        self,
        fetcher: Fetcher,
        on_progress: ProgressCallback | None = None,
        *,
        temp_dir: Path | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._on_progress = on_progress
        if temp_dir is None:
            import tempfile

            temp_dir = Path(tempfile.gettempdir())
        self._temp_dir = temp_dir

    async def __call__(self, ctx: DownloadContext) -> DownloadContext:
        request = ctx.request
        try:
            result = await self._fetcher.fetch(
                request.candidate,
                output_format=request.output_format,
                temp_dir=self._temp_dir,
                on_progress=self._on_progress,
            )
        except AudioFetchFailed:
            raise
        except Exception as exc:  # noqa: BLE001 - any fetcher failure is a fetch error
            raise AudioFetchFailed(str(exc)) from exc

        return ctx.updated(
            temp_path=result.path,
            source_url=result.source_url,
            source_abr=result.abr,
            source_info=result.info,
        )
