"""
Footer that shows the installed spotDL version.
"""

from typing import Optional

from textual.widgets import Static

from spotdl._version import __version__ as SPOTDL_VERSION
from spotdl.console.tui import i18n
from spotdl.console.tui.versions import parse_version

TR = i18n.tr


def format_version_line(latest_version: Optional[str] = None) -> str:
    """
    Build the version text shown in the footer.

    ### Arguments
    - latest_version: Latest published version, if known.

    ### Returns
    - The translated version line, with an update notice when a newer
    version is available.
    """

    line = TR(
        "home.version_line",
        version=SPOTDL_VERSION,
    )
    if latest_version and parse_version(latest_version) > parse_version(SPOTDL_VERSION):
        line += " " + TR("home.upstream_update_available", version=latest_version)
    return line


class VersionFooter(Static):
    """
    Static footer with the version line.
    """

    def __init__(self, initial_text: Optional[str] = None) -> None:
        """
        Create the footer.

        ### Arguments
        - initial_text: Text to show before the version line is built.
        """

        super().__init__(initial_text or format_version_line(), id="version-footer")
        self._upstream_latest: Optional[str] = None

    def apply_upstream(self, upstream_latest: str) -> None:
        """
        Show the latest published version next to the installed one.

        ### Arguments
        - upstream_latest: Latest published version.
        """

        self._upstream_latest = upstream_latest
        self.update(format_version_line(upstream_latest))

    def refresh_language(self) -> None:
        """
        Translate the footer to the current language.
        """

        self.update(format_version_line(self._upstream_latest))
