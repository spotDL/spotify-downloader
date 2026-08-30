import json
import platform
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

from spotdl.utils.config import get_configured_data_dir, set_configured_data_dir
from spotdl.utils.deno import DENO_RELEASE_LATEST_URL, DenoError
from spotdl.utils.deno import download_deno as deno_download
from spotdl.utils.deno import get_local_deno
from spotdl.utils.ffmpeg import FFMPEG_URLS, FFmpegError
from spotdl.utils.ffmpeg import download_ffmpeg as ffmpeg_download
from spotdl.utils.ffmpeg import get_local_ffmpeg

__all__ = ["run_setup"]

_MANIFEST_NAME = "setup_manifest.json"

_STEP_NONE = 0
_STEP_CHECK = 1
_STEP_DOWNLOAD = 2
_STEP_READY = 3


def _manifest_path(data_dir: Path) -> Path:
    return data_dir / _MANIFEST_NAME


def _read_manifest(data_dir: Path) -> Dict[str, Any]:
    manifest_file = _manifest_path(data_dir)
    if not manifest_file.is_file():
        return {}

    try:
        with open(manifest_file, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except (OSError, json.JSONDecodeError):
        return {}


def _write_manifest(data_dir: Path, manifest: Dict[str, Any]) -> None:
    with open(_manifest_path(data_dir), "w", encoding="utf-8") as file_handle:
        json.dump(manifest, file_handle, indent=2)


def _current_ffmpeg_url() -> str:
    os_name = platform.system().lower()
    os_arch = platform.machine().lower()
    return FFMPEG_URLS.get(os_name, {}).get(os_arch, "")


def _latest_deno_version() -> Optional[str]:
    try:
        response = requests.get(DENO_RELEASE_LATEST_URL, timeout=10)
        response.raise_for_status()
        return response.content.decode("utf-8").strip()
    except requests.RequestException:
        return None


def default_data_dir_choices() -> Tuple[Path, Path]:
    cwd = Path.cwd()
    return cwd, cwd / "spotdl-data"


def resolve_choice(choice: str, custom_path: str) -> Optional[Path]:
    cwd, subfolder = default_data_dir_choices()

    if choice == "2":
        return subfolder
    if choice == "3":
        stripped = custom_path.strip()
        if stripped:
            return Path(stripped).expanduser()
        return None
    return cwd


def apply_data_dir(data_dir: Path) -> None:
    set_configured_data_dir(data_dir)


def ffmpeg_status(manifest: Dict[str, Any]) -> Tuple[int, str]:
    target_url = _current_ffmpeg_url()
    if not target_url:
        return _STEP_NONE, "setup.ffmpeg_unavailable"

    installed_path = get_local_ffmpeg()
    stored_url = manifest.get("ffmpeg_source")

    if installed_path is not None and stored_url == target_url:
        return _STEP_READY, "setup.ffmpeg_uptodate"

    if installed_path is None:
        return _STEP_DOWNLOAD, "setup.ffmpeg_download"
    return _STEP_DOWNLOAD, "setup.ffmpeg_update"


def install_ffmpeg(manifest: Dict[str, Any]) -> Tuple[bool, str, Optional[Path]]:
    target_url = _current_ffmpeg_url()
    if not target_url:
        return False, "setup.ffmpeg_unavailable", None

    try:
        path = ffmpeg_download()
    except FFmpegError:
        return False, "setup.ffmpeg_failed", None

    manifest["ffmpeg_source"] = target_url
    return True, "setup.ffmpeg_ready", path


def deno_status(manifest: Dict[str, Any]) -> Tuple[int, str]:
    latest_version = _latest_deno_version()
    installed_path = get_local_deno()
    stored_version = manifest.get("deno_version")

    if (
        installed_path is not None
        and latest_version
        and stored_version == latest_version
    ):
        return _STEP_READY, "setup.deno_uptodate"
    if installed_path is not None and not latest_version:
        return _STEP_READY, "setup.deno_unknown"
    if installed_path is None:
        return _STEP_DOWNLOAD, "setup.deno_download"
    return _STEP_DOWNLOAD, "setup.deno_update"


def install_deno(manifest: Dict[str, Any]) -> Tuple[bool, str, Optional[Path]]:
    try:
        path = deno_download()
    except DenoError:
        return False, "setup.deno_failed", None

    latest_version = _latest_deno_version()
    if latest_version:
        manifest["deno_version"] = latest_version
    return True, "setup.deno_ready", path


def prepare_data_dir(data_dir: Path) -> Dict[str, Any]:
    data_dir.mkdir(parents=True, exist_ok=True)
    return _read_manifest(data_dir)


def finalize_data_dir(data_dir: Path, manifest: Dict[str, Any]) -> None:
    _write_manifest(data_dir, manifest)


def run_setup() -> None:
    import sys

    if "--setup" in sys.argv:
        idx = sys.argv.index("--setup")
        if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-"):
            path_arg = sys.argv[idx + 1]
            data_dir = Path(path_arg).expanduser()
            run_setup_headless(data_dir)
            return

    from spotdl.console.tui.setup_app import run_setup_ui

    current = get_configured_data_dir()
    run_setup_ui(current)


def run_setup_headless(data_dir: Path) -> None:
    set_configured_data_dir(data_dir)
    manifest = prepare_data_dir(data_dir)

    ok_ff, msg_ff, _ = install_ffmpeg(manifest)
    ok_den, msg_den, _ = install_deno(manifest)

    finalize_data_dir(data_dir, manifest)

    if not ok_ff or not ok_den:
        raise RuntimeError(f"{msg_ff} | {msg_den}")
