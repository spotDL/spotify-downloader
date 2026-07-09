"""``spotdl ffmpeg download`` — bootstrap a static ffmpeg into the data dir.

ffmpeg is a hard runtime dependency of the download engine, but which binary and
where is a CLI/UX concern (core just takes a path). This mirrors v4's
``--download-ffmpeg``: fetch a platform-appropriate static build into
``<data_dir>/ffmpeg/`` and point the download command's default ``ffmpeg_path``
at it, falling back to a ``ffmpeg`` already on ``PATH``.

The real fetch is network-bound and only exercised by a ``network``-marked test;
the default suite drives the injected :func:`_fetch` seam.
"""

from __future__ import annotations

import platform
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

import httpx
import platformdirs
import typer

from spotdl_cli.commands import _support

ffmpeg_app = typer.Typer(no_args_is_help=True, help="Manage the bundled ffmpeg binary.")

# Platform/arch → static-build archive URL. Keys are ``(system, machine)`` from
# :func:`platform.system` / :func:`platform.machine`, normalized in ``_build_url``.
_STATIC_BUILD_URLS: dict[tuple[str, str], str] = {
    ("linux", "x86_64"): (
        "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    ),
    ("linux", "aarch64"): (
        "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
    ),
    ("darwin", "x86_64"): "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip",
    ("darwin", "arm64"): "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip",
    ("windows", "amd64"): "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
}

_ARCH_ALIASES = {"x64": "x86_64", "amd64": "amd64", "arm64": "arm64", "aarch64": "aarch64"}


def _binary_name() -> str:
    """The ffmpeg executable filename for the current OS."""
    return "ffmpeg.exe" if platform.system().lower() == "windows" else "ffmpeg"


def default_data_dir() -> Path:
    """The platformdirs data dir spotdl stores its binary/DB under."""
    return platformdirs.user_data_path("spotdl")


def ffmpeg_dir(data_dir: Path | None = None) -> Path:
    """The directory the bootstrapped ffmpeg lives in."""
    return (data_dir or default_data_dir()) / "ffmpeg"


def resolve_ffmpeg_path(data_dir: Path | None = None) -> str:
    """The ffmpeg path the download command should default to.

    The bootstrapped binary when present (and executable), else the bare name
    ``ffmpeg`` — resolved off ``PATH`` by the engine like any other command.
    """
    target = ffmpeg_dir(data_dir) / _binary_name()
    if target.exists():
        return str(target)
    return "ffmpeg"


def _build_url() -> str:
    """The static-build URL for the current platform, or a usage error."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    machine = _ARCH_ALIASES.get(machine, machine)
    url = _STATIC_BUILD_URLS.get((system, machine))
    if url is None:
        raise typer.BadParameter(
            f"no prebuilt ffmpeg for {system}/{machine}; install ffmpeg from your package manager"
        )
    return url


def _extract_binary(archive: Path, dest: Path) -> None:
    """Find the ffmpeg executable inside ``archive`` and write it to ``dest``."""
    name = _binary_name()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(tmp_dir)
        else:
            with tarfile.open(archive) as tf:
                tf.extractall(tmp_dir)  # noqa: S202  (trusted static build)
        found = next((p for p in tmp_dir.rglob(name) if p.is_file()), None)
        if found is None:
            raise RuntimeError(f"{name} not found inside {archive.name}")
        shutil.copy2(found, dest)


def _fetch(url: str, dest: Path) -> None:
    """Download ``url`` and place the ffmpeg binary at ``dest`` (network seam).

    Streamed with a Rich progress bar. Patched out in the default test suite; the
    real path is covered by a ``network``-marked test only.
    """
    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        TextColumn,
    )

    suffix = ".zip" if url.endswith("zip") else ".tar.xz"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        archive = Path(handle.name)
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0)) or None
            with (
                archive.open("wb") as out,
                Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    DownloadColumn(),
                    console=_support.console,
                ) as progress,
            ):
                task = progress.add_task("downloading ffmpeg", total=total)
                for chunk in resp.iter_bytes():
                    out.write(chunk)
                    progress.update(task, advance=len(chunk))
        _extract_binary(archive, dest)
    finally:
        archive.unlink(missing_ok=True)


@ffmpeg_app.command("download")
def download(
    directory: Path = typer.Option(
        None, "--dir", help="Install into this directory instead of the data dir."
    ),
    force: bool = typer.Option(False, "--force", help="Re-download even if present."),
) -> None:
    """Download a static ffmpeg build into the data dir and print its path."""
    target_dir = directory if directory is not None else ffmpeg_dir()
    dest = target_dir / _binary_name()

    if dest.exists() and not force:
        _support.console.print(f"ffmpeg already present at {dest}", soft_wrap=True)
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    _fetch(_build_url(), dest)
    dest.chmod(0o755)
    _support.console.print(f"ffmpeg installed at {dest}", soft_wrap=True)


def register(app: typer.Typer) -> None:
    """Attach the ``ffmpeg`` command group to the root Typer app."""
    app.add_typer(ffmpeg_app, name="ffmpeg")
