"""
Native GTK4 + libadwaita desktop front-end for spotDL.

Run with ``spotdl-gui`` (see ``[project.gui-scripts]`` in ``pyproject.toml``)
or ``python -m spotdl.gui``.
"""

import sys
from typing import List, Optional

__all__ = ["main"]


def main(argv: Optional[List[str]] = None) -> int:
    """
    Entry point for the spotDL desktop GUI.

    ### Arguments
    - argv: Optional argument vector (defaults to ``sys.argv``).

    ### Returns
    - The application's exit code.
    """

    try:
        # pylint: disable=import-outside-toplevel,unused-import
        import gi  # noqa: F401
    except ImportError:
        sys.stderr.write(
            "The spotDL GUI requires PyGObject (GTK4 + libadwaita).\n"
            "Install it with your system package manager, e.g. on Fedora:\n"
            "    sudo dnf install python3-gobject gtk4 libadwaita\n"
            "or run the Flatpak build (see packaging/flatpak/).\n"
        )
        return 1

    # pylint: disable=import-outside-toplevel
    from spotdl.gui.app import SpotdlApplication

    app = SpotdlApplication()
    return app.run(argv if argv is not None else sys.argv)
