"""``spotdl tui`` — placeholder for the Plan 9 interactive TUI.

Plan 9 owns the real Textual TUI; it consumes the ``SpotdlClient`` façade and the
``*View`` presentation models this plan defines (spec §7). Until it ships, ``tui``
(and a bare ``spotdl`` invoked from a terminal — see ``__main__._dispatch``) print
a one-line pointer at the working commands, so the command name is stable now and
gains behavior in Plan 9 without a CLI change.
"""

from __future__ import annotations

import typer

TUI_STUB_MESSAGE = (
    "the interactive TUI ships in a later release; use `spotdl download`/`search` for now"
)


def tui() -> None:
    """Launch the interactive TUI (ships in a later release)."""
    typer.echo(TUI_STUB_MESSAGE)


def register(app: typer.Typer) -> None:
    """Attach ``tui`` to the root Typer app."""
    app.command("tui")(tui)


__all__ = ["TUI_STUB_MESSAGE", "register", "tui"]
