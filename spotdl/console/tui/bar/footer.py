from typing import Optional

from textual.widgets import Static

from spotdl._version import __version__ as SPOTDL_VERSION
from spotdl.console.tui import i18n
from spotdl.console.tui.versions import parse_version

TR = i18n.tr


def format_version_line(latest_version: Optional[str] = None) -> str:
    line = TR(
        "home.version_line",
        version=SPOTDL_VERSION,
    )
    if latest_version and parse_version(latest_version) > parse_version(SPOTDL_VERSION):
        line += " " + TR("home.upstream_update_available", version=latest_version)
    return line


class VersionFooter(Static):
    def __init__(self, initial_text: Optional[str] = None) -> None:
        super().__init__(initial_text or format_version_line(), id="version-footer")
        self._upstream_latest: Optional[str] = None

    def apply_upstream(self, upstream_latest: str) -> None:
        self._upstream_latest = upstream_latest
        self.update(format_version_line(upstream_latest))

    def refresh_language(self) -> None:
        self.update(format_version_line(self._upstream_latest))
