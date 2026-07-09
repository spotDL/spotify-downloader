"""Tests for ``spotdl_core.download.convert`` — ffmpeg conversion, bitrate
modes, and the move-not-reencode fast path.

The pure surface (``resolve_bitrate``, ``should_move``, ``build_ffmpeg_command``)
is exercised without ffmpeg and asserts the exact argv (output-format parity is
a CONTRACT). The ``ConvertStep`` behaviours that need a real encoder are guarded
by the ``requires_ffmpeg`` autoskip fixture and operate on tiny synthetic-silence
inputs, so the default suite stays offline and never depends on an installed
ffmpeg.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest
from spotdl_core.download.context import (
    BITRATE_AUTO,
    BITRATE_DISABLE,
    DownloadConfig,
    DownloadContext,
    DownloadRequest,
    OutputFormat,
    ProgressEvent,
    ProgressPhase,
)
from spotdl_core.download.convert import (
    FFMPEG_CODECS,
    ConvertStep,
    build_ffmpeg_command,
    resolve_bitrate,
    should_move,
)
from spotdl_core.model import AudioCandidate, ProviderId, Track
from spotdl_core.providers.errors import ConversionFailed

FIXTURES = Path(__file__).parent / "fixtures"


# --- helpers --------------------------------------------------------------


def _track() -> Track:
    return Track(
        name="Song Name",
        artists=("Main Artist",),
        duration_ms=1_000,
        provider=ProviderId.SPOTIFY,
        provider_id="sp123",
    )


def _candidate() -> AudioCandidate:
    return AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt123",
        url="https://youtube.com/watch?v=yt123",
        name="Song Name",
    )


def _request(
    *,
    output_format: OutputFormat = OutputFormat.MP3,
    bitrate: str = BITRATE_AUTO,
) -> DownloadRequest:
    return DownloadRequest(
        track=_track(),
        candidate=_candidate(),
        output_template="",
        output_format=output_format,
        bitrate=bitrate,
    )


def _config(tmp_path: Path, **kw: object) -> DownloadConfig:
    return DownloadConfig(
        output_dir=tmp_path / "out",
        temp_dir=tmp_path / "temp",
        **kw,  # type: ignore[arg-type]
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- resolve_bitrate ------------------------------------------------------


def test_resolve_bitrate_auto_uses_source_abr() -> None:
    assert resolve_bitrate(BITRATE_AUTO, 129.0) == "129k"


def test_resolve_bitrate_auto_truncates_to_int() -> None:
    assert resolve_bitrate(BITRATE_AUTO, 130.9) == "130k"


def test_resolve_bitrate_auto_falls_back_to_128k() -> None:
    assert resolve_bitrate(BITRATE_AUTO, None) == "128k"
    assert resolve_bitrate(BITRATE_AUTO, 0.0) == "128k"


def test_resolve_bitrate_disable_is_none() -> None:
    assert resolve_bitrate(BITRATE_DISABLE, 200.0) is None


def test_resolve_bitrate_passthrough_digits() -> None:
    assert resolve_bitrate("320", None) == "320"


def test_resolve_bitrate_passthrough_cbr() -> None:
    assert resolve_bitrate("320k", None) == "320k"


# --- should_move ----------------------------------------------------------


@pytest.mark.parametrize(
    ("input_ext", "output_format", "bitrate", "expected"),
    [
        ("m4a", OutputFormat.M4A, BITRATE_AUTO, True),
        ("m4a", OutputFormat.M4A, BITRATE_DISABLE, True),
        ("opus", OutputFormat.OPUS, BITRATE_AUTO, True),
        # ext mismatch -> re-encode
        ("webm", OutputFormat.OPUS, BITRATE_AUTO, False),
        ("m4a", OutputFormat.MP3, BITRATE_AUTO, False),
        # explicit bitrate -> re-encode even if ext matches
        ("m4a", OutputFormat.M4A, "320k", False),
        ("mp3", OutputFormat.MP3, "0", False),
    ],
)
def test_should_move_truth_table(
    input_ext: str, output_format: OutputFormat, bitrate: str, expected: bool
) -> None:
    assert should_move(input_ext, output_format, bitrate) is expected


# --- FFMPEG_CODECS contract table -----------------------------------------


def test_ffmpeg_codecs_table_matches_contract() -> None:
    assert FFMPEG_CODECS == {
        OutputFormat.MP3: ["-codec:a", "libmp3lame"],
        OutputFormat.FLAC: ["-codec:a", "flac", "-sample_fmt", "s16"],
        OutputFormat.OGG: ["-codec:a", "libvorbis"],
        OutputFormat.OPUS: ["-codec:a", "libopus"],
        OutputFormat.M4A: ["-codec:a", "aac"],
        OutputFormat.WAV: ["-codec:a", "pcm_s16le"],
    }


# --- build_ffmpeg_command -------------------------------------------------


def _base(input_file: Path) -> list[str]:
    return [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-i",
        str(input_file.resolve()),
        "-movflags",
        "+faststart",
    ]


def test_build_command_mp3_with_auto_bitrate(tmp_path: Path) -> None:
    in_file = tmp_path / "in.m4a"
    out_file = tmp_path / "out.mp3"
    cmd = build_ffmpeg_command("ffmpeg", in_file, "m4a", out_file, OutputFormat.MP3, "128k", ())
    assert cmd == [
        *_base(in_file),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(out_file.resolve()),
    ]


def test_build_command_opus_from_webm_is_stream_copy(tmp_path: Path) -> None:
    in_file = tmp_path / "in.webm"
    out_file = tmp_path / "out.opus"
    cmd = build_ffmpeg_command("ffmpeg", in_file, "webm", out_file, OutputFormat.OPUS, None, ())
    assert cmd == [
        *_base(in_file),
        "-vn",
        "-c:a",
        "copy",
        str(out_file.resolve()),
    ]


def test_build_command_opus_from_non_webm_forces_libopus(tmp_path: Path) -> None:
    in_file = tmp_path / "in.m4a"
    out_file = tmp_path / "out.opus"
    cmd = build_ffmpeg_command("ffmpeg", in_file, "m4a", out_file, OutputFormat.OPUS, None, ())
    assert cmd == [
        *_base(in_file),
        "-c:a",
        "libopus",
        str(out_file.resolve()),
    ]


def test_build_command_m4a_from_m4a_no_bitrate_is_stream_copy(tmp_path: Path) -> None:
    in_file = tmp_path / "in.m4a"
    out_file = tmp_path / "out.m4a"
    cmd = build_ffmpeg_command("ffmpeg", in_file, "m4a", out_file, OutputFormat.M4A, None, ())
    assert cmd == [
        *_base(in_file),
        "-vn",
        "-c:a",
        "copy",
        str(out_file.resolve()),
    ]


def test_build_command_m4a_from_m4a_with_bitrate_reencodes(tmp_path: Path) -> None:
    in_file = tmp_path / "in.m4a"
    out_file = tmp_path / "out.m4a"
    cmd = build_ffmpeg_command("ffmpeg", in_file, "m4a", out_file, OutputFormat.M4A, "256k", ())
    assert cmd == [
        *_base(in_file),
        "-codec:a",
        "aac",
        "-b:a",
        "256k",
        str(out_file.resolve()),
    ]


def test_build_command_flac_has_sample_fmt(tmp_path: Path) -> None:
    in_file = tmp_path / "in.m4a"
    out_file = tmp_path / "out.flac"
    cmd = build_ffmpeg_command("ffmpeg", in_file, "m4a", out_file, OutputFormat.FLAC, None, ())
    assert cmd == [
        *_base(in_file),
        "-codec:a",
        "flac",
        "-sample_fmt",
        "s16",
        str(out_file.resolve()),
    ]


def test_build_command_cbr_bitrate_uses_b_a(tmp_path: Path) -> None:
    in_file = tmp_path / "in.m4a"
    out_file = tmp_path / "out.mp3"
    cmd = build_ffmpeg_command("ffmpeg", in_file, "m4a", out_file, OutputFormat.MP3, "320k", ())
    assert "-b:a" in cmd and cmd[cmd.index("-b:a") + 1] == "320k"
    assert "-q:a" not in cmd


def test_build_command_vbr_digits_use_q_a(tmp_path: Path) -> None:
    in_file = tmp_path / "in.m4a"
    out_file = tmp_path / "out.mp3"
    cmd = build_ffmpeg_command("ffmpeg", in_file, "m4a", out_file, OutputFormat.MP3, "0", ())
    assert "-q:a" in cmd and cmd[cmd.index("-q:a") + 1] == "0"
    assert "-b:a" not in cmd


def test_build_command_passthrough_args_before_output(tmp_path: Path) -> None:
    in_file = tmp_path / "in.m4a"
    out_file = tmp_path / "out.mp3"
    cmd = build_ffmpeg_command(
        "ffmpeg",
        in_file,
        "m4a",
        out_file,
        OutputFormat.MP3,
        "128k",
        ("-af", "loudnorm"),
    )
    assert cmd == [
        *_base(in_file),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "128k",
        "-af",
        "loudnorm",
        str(out_file.resolve()),
    ]


def test_build_command_uses_custom_ffmpeg_binary(tmp_path: Path) -> None:
    in_file = tmp_path / "in.m4a"
    out_file = tmp_path / "out.mp3"
    cmd = build_ffmpeg_command("/opt/ffmpeg", in_file, "m4a", out_file, OutputFormat.MP3, None, ())
    assert cmd[0] == "/opt/ffmpeg"


# --- ConvertStep (requires ffmpeg) ----------------------------------------


async def test_convert_step_reencodes_m4a_to_mp3(tmp_path: Path, requires_ffmpeg: None) -> None:
    temp = tmp_path / "temp"
    temp.mkdir()
    temp_file = temp / "yt123.m4a"
    shutil.copyfile(FIXTURES / "tiny.m4a", temp_file)

    output_path = tmp_path / "out" / "song.mp3"
    ctx = DownloadContext(
        request=_request(output_format=OutputFormat.MP3),
        temp_path=temp_file,
        output_path=output_path,
        source_abr=129.0,
    )
    step = ConvertStep(_config(tmp_path))
    result = await step(ctx)

    assert result.final_path == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    # temp file is always cleaned up
    assert not temp_file.exists()


async def test_convert_step_move_fast_path_is_byte_identical(
    tmp_path: Path, requires_ffmpeg: None
) -> None:
    temp = tmp_path / "temp"
    temp.mkdir()
    temp_file = temp / "yt123.m4a"
    shutil.copyfile(FIXTURES / "tiny.m4a", temp_file)
    source_hash = _sha(FIXTURES / "tiny.m4a")

    output_path = tmp_path / "out" / "song.m4a"
    ctx = DownloadContext(
        request=_request(output_format=OutputFormat.M4A, bitrate=BITRATE_DISABLE),
        temp_path=temp_file,
        output_path=output_path,
    )
    step = ConvertStep(_config(tmp_path))
    result = await step(ctx)

    assert result.final_path == output_path
    assert output_path.exists()
    # moved, not re-encoded: byte-identical to the source
    assert _sha(output_path) == source_hash
    assert not temp_file.exists()


async def test_convert_step_creates_output_parent_dir(
    tmp_path: Path, requires_ffmpeg: None
) -> None:
    temp = tmp_path / "temp"
    temp.mkdir()
    temp_file = temp / "yt123.m4a"
    shutil.copyfile(FIXTURES / "tiny.m4a", temp_file)

    output_path = tmp_path / "out" / "nested" / "deep" / "song.mp3"
    ctx = DownloadContext(
        request=_request(output_format=OutputFormat.MP3),
        temp_path=temp_file,
        output_path=output_path,
    )
    await ConvertStep(_config(tmp_path))(ctx)
    assert output_path.exists()


async def test_convert_step_emits_convert_progress(tmp_path: Path, requires_ffmpeg: None) -> None:
    temp = tmp_path / "temp"
    temp.mkdir()
    temp_file = temp / "yt123.m4a"
    shutil.copyfile(FIXTURES / "tiny.m4a", temp_file)

    events: list[ProgressEvent] = []
    output_path = tmp_path / "out" / "song.mp3"
    ctx = DownloadContext(
        request=_request(output_format=OutputFormat.MP3),
        temp_path=temp_file,
        output_path=output_path,
    )
    step = ConvertStep(_config(tmp_path), on_progress=events.append)
    await step(ctx)

    assert output_path.exists()
    assert events, "expected at least one CONVERT progress event"
    assert all(e.phase is ProgressPhase.CONVERT for e in events)
    assert events[-1].percent == 100


async def test_convert_step_bogus_ffmpeg_raises_conversion_failed(
    tmp_path: Path,
) -> None:
    temp = tmp_path / "temp"
    temp.mkdir()
    temp_file = temp / "yt123.m4a"
    shutil.copyfile(FIXTURES / "tiny.m4a", temp_file)

    output_path = tmp_path / "out" / "song.mp3"
    ctx = DownloadContext(
        request=_request(output_format=OutputFormat.MP3),
        temp_path=temp_file,
        output_path=output_path,
    )
    step = ConvertStep(_config(tmp_path, ffmpeg_path="/nonexistent/ffmpeg"))

    with pytest.raises(ConversionFailed) as excinfo:
        await step(ctx)
    assert excinfo.value.step == "convert"
    # no partial output left behind
    assert not output_path.exists()


async def test_convert_step_corrupt_input_raises_with_stderr(
    tmp_path: Path, requires_ffmpeg: None
) -> None:
    temp = tmp_path / "temp"
    temp.mkdir()
    temp_file = temp / "yt123.m4a"
    temp_file.write_bytes(b"this is not audio data at all")

    output_path = tmp_path / "out" / "song.mp3"
    ctx = DownloadContext(
        request=_request(output_format=OutputFormat.MP3),
        temp_path=temp_file,
        output_path=output_path,
    )
    step = ConvertStep(_config(tmp_path))

    with pytest.raises(ConversionFailed) as excinfo:
        await step(ctx)
    assert excinfo.value.step == "convert"
    # captured ffmpeg output is surfaced in the message
    assert str(excinfo.value).strip() != ""
    # partial output removed
    assert not output_path.exists()
