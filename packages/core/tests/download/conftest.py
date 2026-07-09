import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _ffmpeg_present() -> bool:
    return shutil.which("ffmpeg") is not None


@pytest.fixture
def requires_ffmpeg() -> None:
    """Skip a test when no ffmpeg binary is on PATH (CI installs one)."""
    if not _ffmpeg_present():
        pytest.skip("ffmpeg binary not available")


@pytest.fixture(scope="session")
def silent_audio(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Generate 1s silent files per output format with ffmpeg, once per session.

    Skips the whole group when ffmpeg is absent. Used by tag tests (real mutagen).
    """
    if not _ffmpeg_present():
        pytest.skip("ffmpeg binary not available")
    import subprocess

    out = tmp_path_factory.mktemp("silent")
    made: dict[str, Path] = {}
    # Each format lists candidate encoder arg-sets, tried in order. The ogg
    # fallback covers ffmpeg builds compiled without libvorbis (e.g. some
    # Homebrew builds), which still ship the native experimental encoder.
    formats: list[tuple[str, list[list[str]]]] = [
        ("mp3", [["-codec:a", "libmp3lame"]]),
        ("m4a", [["-codec:a", "aac"]]),
        ("flac", [["-codec:a", "flac"]]),
        ("ogg", [["-codec:a", "libvorbis"], ["-codec:a", "vorbis", "-strict", "-2"]]),
        ("opus", [["-codec:a", "libopus"]]),
        ("wav", [["-codec:a", "pcm_s16le"]]),
    ]
    for fmt, candidates in formats:
        path = out / f"silent.{fmt}"
        last: subprocess.CalledProcessError | None = None
        for codec in candidates:
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        "anullsrc=r=44100:cl=stereo",
                        "-t",
                        "1",
                        *codec,
                        str(path),
                    ],
                    check=True,
                    capture_output=True,
                )
                break
            except subprocess.CalledProcessError as exc:
                last = exc
        else:
            raise last if last is not None else RuntimeError(f"no encoder for {fmt}")
        made[fmt] = path
    return made
