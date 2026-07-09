"""ffmpeg conversion, bitrate modes, and the move-not-reencode fast path.

Ports v4's ``spotdl/utils/ffmpeg.py`` (``FFMPEG_FORMATS``, ``convert``) and the
downloader convert/move block against the v5 model. The ``FFMPEG_CODECS`` table,
the special-case codec selection, the bitrate-resolution rules, and the
move-fast-path predicate are a CONTRACT (output-format parity — other tools read
the produced containers). Progress parsing and subprocess plumbing are
implementation.

ffmpeg is always invoked as ``[config.ffmpeg_path, *args]`` — never through a
shell. On a non-zero return code the captured ffmpeg output is surfaced in the
:class:`ConversionFailed` message (v4 wrote a sidecar error file; v5 leaves
persistence to the server/CLI) and any partial output file is removed.
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import shutil
import subprocess
from pathlib import Path

from spotdl_core.download.context import (
    BITRATE_AUTO,
    BITRATE_DISABLE,
    Bitrate,
    DownloadConfig,
    DownloadContext,
    OutputFormat,
    ProgressCallback,
    ProgressEvent,
    ProgressPhase,
)
from spotdl_core.providers.errors import ConversionFailed

__all__ = [
    "FFMPEG_CODECS",
    "ConvertStep",
    "build_ffmpeg_command",
    "resolve_bitrate",
    "should_move",
]


# --- codec table (CONTRACT, port of v4 FFMPEG_FORMATS) --------------------

FFMPEG_CODECS: dict[OutputFormat, list[str]] = {
    OutputFormat.MP3: ["-codec:a", "libmp3lame"],
    OutputFormat.FLAC: ["-codec:a", "flac", "-sample_fmt", "s16"],
    OutputFormat.OGG: ["-codec:a", "libvorbis"],
    OutputFormat.OPUS: ["-codec:a", "libopus"],
    OutputFormat.M4A: ["-codec:a", "aac"],
    OutputFormat.WAV: ["-codec:a", "pcm_s16le"],
}


# --- progress parsing regexes (port of v4 DUR_REGEX / TIME_REGEX) ---------

_DUR_REGEX = re.compile(r"Duration: (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})")
_TIME_REGEX = re.compile(r"out_time=(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})")


def _to_ms(hour: str, min: str, sec: str, ms: str) -> float:  # noqa: A002 - regex group names
    return (int(hour) * 3_600_000) + (int(min) * 60_000) + (int(sec) * 1000) + int(ms)


# --- bitrate resolution (CONTRACT) ----------------------------------------


def resolve_bitrate(bitrate: Bitrate, source_abr: float | None) -> str | None:
    """Resolve the request bitrate token to a concrete ffmpeg value (or ``None``).

    - ``"auto"``   -> ``"<int(source_abr)>k"`` when a source ABR is known, else ``"128k"``.
    - ``"disable"`` -> ``None`` (no ``-b:a``/``-q:a``; also enables the move fast path).
    - anything else -> returned unchanged; :func:`build_ffmpeg_command` decides
      whether it is applied as VBR (``-q:a``, all-digits) or CBR (``-b:a``).
    """
    if bitrate == BITRATE_AUTO:
        return f"{int(source_abr)}k" if source_abr else "128k"
    if bitrate == BITRATE_DISABLE:
        return None
    return bitrate


# --- move fast path (CONTRACT) --------------------------------------------


def should_move(input_ext: str, output_format: OutputFormat, bitrate: Bitrate) -> bool:
    """Whether the fetched file can be moved instead of re-encoded.

    ``True`` when the request bitrate is ``"auto"``/``"disable"`` **and** the
    source container already matches the output format.

    Deviation from v4: v4 additionally suppressed the fast path for the ``piped``
    audio provider unless the bitrate was ``"disable"``. v5's fetcher is
    provider-agnostic at this layer, so we key purely on ext + bitrate.
    """
    return bitrate in (BITRATE_AUTO, BITRATE_DISABLE) and input_ext == output_format.value


# --- ffmpeg command building (CONTRACT) -----------------------------------


def build_ffmpeg_command(
    ffmpeg: str,
    input_file: Path,
    input_ext: str,
    output_file: Path,
    output_format: OutputFormat,
    bitrate: str | None,
    ffmpeg_args: tuple[str, ...],
) -> list[str]:
    """Build the exact ffmpeg argv (port of v4 ``convert`` argument building).

    Layout: ``-nostdin -y -i <in> -movflags +faststart`` then codec args, then
    bitrate args, then passthrough ``ffmpeg_args``, then ``<out>``. Codec
    selection:

    - output ``opus`` and input ext != ``webm`` -> ``-c:a libopus`` (force re-encode).
    - (``opus`` from ``webm``) or (``m4a`` from ``m4a``), and no bitrate/passthrough
      -> ``-vn -c:a copy`` (stream copy, no re-encode).
    - otherwise -> the ``FFMPEG_CODECS`` row for the output format.
    """
    args: list[str] = [
        "-nostdin",
        "-y",
        "-i",
        str(input_file.resolve()),
        "-movflags",
        "+faststart",
    ]

    if output_format is OutputFormat.OPUS and input_ext != "webm":
        args.extend(["-c:a", "libopus"])
    elif (
        (output_format is OutputFormat.OPUS and input_ext == "webm")
        or (output_format is OutputFormat.M4A and input_ext == "m4a")
    ) and not (bitrate or ffmpeg_args):
        args.extend(["-vn", "-c:a", "copy"])
    else:
        args.extend(FFMPEG_CODECS[output_format])

    if bitrate:
        # all-digits -> VBR quality (-q:a); otherwise CBR (-b:a). (v4 parity.)
        if bitrate.isdigit():
            args.extend(["-q:a", bitrate])
        else:
            args.extend(["-b:a", bitrate])

    args.extend(ffmpeg_args)
    args.append(str(output_file.resolve()))

    return [ffmpeg, *args]


# --- pipeline step --------------------------------------------------------


class ConvertStep:
    """Convert (or move) the fetched temp file into the planned output path.

    When :func:`should_move` applies, the temp file is relocated with
    :func:`shutil.move` (byte-identical, no re-encode). Otherwise ffmpeg is run
    in a worker thread; its ``-progress`` stream is parsed into
    ``ProgressEvent(phase=CONVERT)`` when a callback is injected. The temp file
    is always removed afterwards.
    """

    def __init__(self, config: DownloadConfig, on_progress: ProgressCallback | None = None) -> None:
        self._config = config
        self._on_progress = on_progress

    async def __call__(self, ctx: DownloadContext) -> DownloadContext:
        request = ctx.request
        temp_path = ctx.temp_path
        output_path = ctx.output_path
        if temp_path is None:
            raise ConversionFailed("no fetched audio to convert (temp_path is unset)")
        if output_path is None:
            raise ConversionFailed("no output path planned (output_path is unset)")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        input_ext = temp_path.suffix.lstrip(".")

        try:
            if should_move(input_ext, request.output_format, request.bitrate):
                shutil.move(str(temp_path), str(output_path))
            else:
                bitrate = resolve_bitrate(request.bitrate, ctx.source_abr)
                command = build_ffmpeg_command(
                    self._config.ffmpeg_path,
                    temp_path,
                    input_ext,
                    output_path,
                    request.output_format,
                    bitrate,
                    self._config.ffmpeg_args,
                )
                await asyncio.to_thread(self._run_ffmpeg, command, output_path)
        finally:
            if temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()

        return ctx.updated(final_path=output_path)

    def _emit(self, percent: int | None) -> None:
        if self._on_progress is None:
            return
        # progress is best-effort: a raising callback must never abort a convert
        with contextlib.suppress(Exception):
            self._on_progress(ProgressEvent(phase=ProgressPhase.CONVERT, percent=percent))

    def _run_ffmpeg(self, command: list[str], output_path: Path) -> None:
        """Run ffmpeg synchronously, streaming ``-progress`` for percent updates.

        stderr is merged into stdout so a failure message is fully captured;
        ``-progress -`` prints machine-readable ``out_time=`` lines we parse for
        percent. On a non-zero return code the partial output is deleted and the
        captured output is raised as :class:`ConversionFailed`.
        """
        # Insert progress/plumbing flags (implementation detail, not part of the
        # contract argv). They are global options and safely precede -nostdin.
        run_command = [command[0], "-progress", "-", "-nostats", *command[1:]]

        try:
            process = subprocess.Popen(
                run_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except OSError as exc:
            self._cleanup_partial(output_path)
            raise ConversionFailed(f"failed to launch ffmpeg ({command[0]}): {exc}") from exc

        buffer: list[str] = []
        total_ms: float | None = None
        self._emit(0)

        with process:
            assert process.stdout is not None
            for raw in process.stdout:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                buffer.append(line)

                if self._on_progress is None:
                    continue
                if total_ms is None:
                    dur = _DUR_REGEX.search(line)
                    if dur:
                        total_ms = _to_ms(**dur.groupdict())
                        continue
                if total_ms:
                    match = _TIME_REGEX.search(line)
                    if match:
                        elapsed = _to_ms(**match.groupdict())
                        percent = max(0, min(100, int(elapsed / total_ms * 100)))
                        self._emit(percent)

        if process.returncode != 0:
            self._cleanup_partial(output_path)
            raise ConversionFailed("\n".join(buffer).strip() or "ffmpeg conversion failed")

        self._emit(100)

    @staticmethod
    def _cleanup_partial(output_path: Path) -> None:
        if output_path.exists():
            with contextlib.suppress(OSError):
                output_path.unlink()
