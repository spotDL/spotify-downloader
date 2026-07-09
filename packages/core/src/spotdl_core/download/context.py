"""Download pipeline spine: request/config/context/outcome models, enums,
progress events, and the ``Step`` type.

Everything public here is a CONTRACT (spec §5.4, Plan 4 Task 3): Plan 7 builds
``DownloadRequest``s from server settings and reads ``DownloadOutcome``; the
pipeline steps (Tasks 4-9) read/write the frozen ``DownloadContext`` via
``.updated(...)``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from spotdl_core.model import AudioCandidate, Lyrics, Track

# --- enums ----------------------------------------------------------------


class OutputFormat(StrEnum):
    MP3 = "mp3"
    M4A = "m4a"
    FLAC = "flac"
    OGG = "ogg"
    OPUS = "opus"
    WAV = "wav"


class OverwriteMode(StrEnum):
    SKIP = "skip"  # keep existing file, do nothing
    FORCE = "force"  # re-download, replacing existing
    METADATA = "metadata"  # keep audio, re-embed metadata only


class RestrictMode(StrEnum):
    NONE = "none"  # no restriction (sanitize only)
    ASCII = "ascii"  # NFKD -> ASCII transliteration (v4 restrict="ascii", non-strict)
    STRICT = "strict"  # yt-dlp strict filename sanitization (v4 restrict="strict")


class SkipReason(StrEnum):
    ALREADY_EXISTS = "already_exists"  # file present, overwrite=skip
    SKIP_FILE = "skip_file"  # ".skip" sidecar present, respect_skip_file
    IN_ARCHIVE = "in_archive"  # track url in the archive set
    EXPLICIT_FILTERED = "explicit_filtered"  # explicit track, skip_explicit


class OutcomeStatus(StrEnum):
    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    FAILED = "failed"


class ProgressPhase(StrEnum):
    PLAN = "plan"
    FETCH = "fetch"
    CONVERT = "convert"
    EMBED = "embed"
    POST = "post"
    DONE = "done"
    SKIPPED = "skipped"
    ERROR = "error"


# Bitrate is a validated string: "auto" (derive from source), "disable" (no
# -b:a/-q:a and enables the move-not-reencode fast path), an integer string
# like "320" -> VBR quality (-q:a), or "<n>k"/"<n>K" -> CBR (-b:a). See Task 6.
Bitrate = str
BITRATE_AUTO: Bitrate = "auto"
BITRATE_DISABLE: Bitrate = "disable"


# --- progress -------------------------------------------------------------


class ProgressEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    phase: ProgressPhase
    percent: int | None = None  # 0-100 within the phase, when known
    message: str | None = None


# Consumed later by the server WS relay (Plan 7) and the CLI progress bars
# (Plan 8). Synchronous, best-effort, must never raise into the pipeline.
ProgressCallback = Callable[[ProgressEvent], None]


# --- request / config -----------------------------------------------------


class DownloadRequest(BaseModel):
    """Everything about downloading ONE track. Immutable; built by the caller
    (server, Plan 7) from resolved metadata + the chosen match candidate."""

    model_config = ConfigDict(frozen=True)

    track: Track
    candidate: AudioCandidate  # chosen audio source (head of matching.match())
    output_template: str  # v4 `output`; empty string -> default template
    output_format: OutputFormat = OutputFormat.MP3
    bitrate: Bitrate = BITRATE_AUTO
    overwrite: OverwriteMode = OverwriteMode.SKIP
    restrict: RestrictMode = RestrictMode.NONE
    max_filename_length: int | None = None

    # metadata / tagging
    lyrics: Lyrics | None = None
    embed_lyrics: bool = True
    skip_album_art: bool = False
    retain_track_cover: bool = False
    id3_separator: str = "/"
    track_url: str | None = None  # canonical track URL for WOAS tag (spotify link)

    # post-processing
    generate_lrc: bool = False
    sponsor_block: bool = False

    # skip / overwrite / archive inputs (evaluated purely in Task 4)
    respect_skip_file: bool = False
    create_skip_file: bool = False
    skip_explicit: bool = False
    archive: frozenset[str] = frozenset()  # already-downloaded track URLs
    known_paths: tuple[Path, ...] = ()  # duplicate files found by a prior scan
    detect_formats: tuple[OutputFormat, ...] = ()  # extra extensions to treat as "exists"

    # playlist context for {list-*} template vars and m3u
    list_name: str | None = None
    list_position: int | None = None
    list_length: int | None = None


@dataclass(frozen=True)
class DownloadConfig:
    """Process-level I/O configuration, injected once into the engine. Not
    per-track. ffmpeg is a binary located here, never a pip dependency."""

    output_dir: Path
    temp_dir: Path
    ffmpeg_path: str = "ffmpeg"  # resolved on PATH by default
    cookie_file: Path | None = None  # yt-dlp cookiefile
    proxy: str | None = None  # http(s) proxy for yt-dlp + cover fetch
    ytdlp_args: tuple[str, ...] = ()  # passthrough to yt-dlp (already tokenized)
    ffmpeg_args: tuple[str, ...] = ()  # passthrough appended to the ffmpeg command


# --- threaded pipeline context --------------------------------------------


class DownloadContext(BaseModel):
    """Frozen state threaded through the pipeline. Each step returns a new
    context via `.updated(...)`. `arbitrary_types_allowed` covers `Path` and
    the raw yt-dlp info dict."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    request: DownloadRequest
    output_path: Path | None = None  # set by the plan step (final destination)
    temp_path: Path | None = None  # fetched audio in the temp dir
    final_path: Path | None = None  # after convert/move -> equals output_path on success
    source_url: str | None = None  # resolved audio download URL (candidate.url)
    source_abr: float | None = None  # audio bitrate reported by the fetcher (for "auto")
    source_info: dict[str, Any] | None = None  # raw yt-dlp info (SponsorBlock input)
    skip_reason: SkipReason | None = None

    def updated(self, **changes: Any) -> DownloadContext:
        return self.model_copy(update=changes)


# A pipeline step: async, typed context in -> typed context out. Concrete
# steps are small callables (usually classes capturing an injected
# collaborator) implementing this signature. The engine composes them.
Step = Callable[[DownloadContext], Awaitable[DownloadContext]]


# --- outcome --------------------------------------------------------------


class DownloadOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    status: OutcomeStatus
    track: Track
    path: Path | None = None
    skip_reason: SkipReason | None = None
    failed_step: str | None = None  # "plan"|"fetch"|"convert"|"embed"|"post"
    error: str | None = None  # human-readable message for the batch error summary

    @classmethod
    def downloaded(cls, track: Track, path: Path) -> DownloadOutcome:
        return cls(status=OutcomeStatus.DOWNLOADED, track=track, path=path)

    @classmethod
    def skipped(cls, track: Track, reason: SkipReason, path: Path | None = None) -> DownloadOutcome:
        return cls(status=OutcomeStatus.SKIPPED, track=track, skip_reason=reason, path=path)

    @classmethod
    def failed(cls, track: Track, *, step: str, error: str) -> DownloadOutcome:
        return cls(status=OutcomeStatus.FAILED, track=track, failed_step=step, error=error)
