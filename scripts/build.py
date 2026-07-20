import ctypes
import os
import sys
from importlib.metadata import metadata
from importlib.util import find_spec
from pathlib import Path
from platform import machine

import PyInstaller.__main__  # type: ignore
import pykakasi
import yt_dlp
import ytmusicapi

from spotdl._version import __version__

LOCALES_PATH = str((Path(ytmusicapi.__file__).parent / "locales"))
PYKAKASI_PATH = str((Path(pykakasi.__file__).parent / "data"))
YTDLP_PATH = str(Path(yt_dlp.__file__).parent / "__pyinstaller")

# Read modules from pyproject.toml
modules = set(
    module.split(" ")[0] for module in metadata("spotdl").get_all("Requires-Dist", [])
)
modules.update(
    {
        "spotapi",
    }
)

tls_client_spec = find_spec("tls_client")
if tls_client_spec is None or tls_client_spec.origin is None:
    raise RuntimeError("Could not find tls_client package")

tls_client_path = Path(tls_client_spec.origin).parent
if sys.platform == "darwin":
    tls_client_file_ext = "-arm64.dylib" if machine() == "arm64" else "-x86.dylib"
elif sys.platform in ("win32", "cygwin"):
    tls_client_file_ext = "-64.dll" if ctypes.sizeof(ctypes.c_voidp) == 8 else "-32.dll"
else:
    if machine() == "aarch64":
        tls_client_file_ext = "-arm64.so"
    elif "x86" in machine():
        tls_client_file_ext = "-x86.so"
    else:
        tls_client_file_ext = "-amd64.so"

TLS_CLIENT_BINARY = str(
    tls_client_path / "dependencies" / f"tls-client{tls_client_file_ext}"
)

PyInstaller.__main__.run(
    [
        "spotdl/__main__.py",
        "--onefile",
        "--add-data",
        f"{LOCALES_PATH}{os.pathsep}ytmusicapi/locales",
        "--add-data",
        f"{PYKAKASI_PATH}{os.pathsep}pykakasi/data",
        "--add-binary",
        f"{TLS_CLIENT_BINARY}{os.pathsep}tls_client/dependencies",
        f"--additional-hooks-dir={YTDLP_PATH}",
        "--name",
        f"spotdl-{__version__}-{sys.platform}",
        "--console",
        *(f"--collect-all={module}" for module in modules),
    ]
)
