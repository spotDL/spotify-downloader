import os
import sys
from pathlib import Path

import PyInstaller.__main__  # type: ignore
import ytmusicapi

from spotdl._version import __version__

locales_path = str((Path(ytmusicapi.__file__).parent / "locales"))

PyInstaller.__main__.run(
    [
        "spotdl/__main__.py",
        "--onefile",
        "--add-data",
        f"{locales_path}{os.pathsep}ytmusicapi/locales",
        "--name",
        f"spotdl-{__version__}-{sys.platform}",
        "--console",
    ]
)
