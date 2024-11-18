import os
import sys
from pathlib import Path
from importlib.metadata import metadata

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

PyInstaller.__main__.run(
    [
        "spotdl/__main__.py",
        "--onefile",
        "--add-data",
        f"{LOCALES_PATH}{os.pathsep}ytmusicapi/locales",
        "--add-data",
        f"{PYKAKASI_PATH}{os.pathsep}pykakasi/data",
        f"--additional-hooks-dir={YTDLP_PATH}",
        "--name",
        f"spotdl-{__version__}-{sys.platform}",
        "--console",
        *(f"--collect-all={module}" for module in modules),
    ]
)
