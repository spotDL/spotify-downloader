import os
import sys
from importlib.metadata import metadata
from pathlib import Path

import PyInstaller.__main__  # type: ignore
import pykakasi
import yt_dlp
import ytmusicapi

import spotdl
from spotdl._version import __version__

LOCALES_PATH = str((Path(ytmusicapi.__file__).parent / "locales"))
PYKAKASI_PATH = str((Path(pykakasi.__file__).parent / "data"))
YTDLP_PATH = str(Path(yt_dlp.__file__).parent / "__pyinstaller")
WEB_STATIC_PATH = str(Path(spotdl.__file__).parent / "web" / "static")
WEB_COMPONENTS_PATH = str(Path(spotdl.__file__).parent / "web" / "components")

# Read modules from pyproject.toml
modules = set(
    module.split(" ")[0] for module in metadata("spotdl").get_all("Requires-Dist", [])
)
# spotapi is a transitive dependency (via spotipyFree), so it is not in
# Requires-Dist; curl_cffi is spotapi's HTTP backend and ships a compiled
# extension with no pyinstaller-hooks-contrib hook, so collect it explicitly
modules.update(
    {
        "spotapi",
        "curl_cffi",
    }
)

PyInstaller.__main__.run(
    [
        "spotdl/__main__.py",
        "--onefile",
        "--add-data",
        f"{LOCALES_PATH}{os.pathsep}ytmusicapi/locales",
        "--add-data",
        f"{PYKAKASI_PATH}{os.pathsep}pykakasi/data",
        "--add-data",
        f"{WEB_STATIC_PATH}{os.pathsep}spotdl/web/static",
        "--add-data",
        f"{WEB_COMPONENTS_PATH}{os.pathsep}spotdl/web/components",
        f"--additional-hooks-dir={YTDLP_PATH}",
        "--name",
        f"spotdl-{__version__}-{sys.platform}",
        "--console",
        *(f"--collect-all={module}" for module in modules),
    ]
)
