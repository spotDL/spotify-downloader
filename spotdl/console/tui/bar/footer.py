from typing import Optional

from textual.widgets import Static

from spotdl._version import __version__ as UPSTREAM_BASE_VERSION
from spotdl.console.tui import i18n
from spotdl.console.tui.versions import (
    FORK_VERSION,
    get_latest_fork_changelog_version,
    parse_version,
)

TR = i18n.tr


def format_version_line(upstream_latest: Optional[str] = None) -> str:
    fork_version = get_latest_fork_changelog_version() or FORK_VERSION
    line = TR(
        "home.version_line",
        upstream=UPSTREAM_BASE_VERSION,
        fork=fork_version,
    )
    if upstream_latest and parse_version(upstream_latest) > parse_version(
        UPSTREAM_BASE_VERSION
    ):
        line += " " + TR("home.upstream_update_available", version=upstream_latest)
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
