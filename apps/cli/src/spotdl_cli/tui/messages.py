"""Textual messages that cross the screen ↔ app boundary (CONTRACT C/D).

Screens stay dumb: instead of reaching into the app or a client, they post one of
these and let :class:`~spotdl_cli.tui.app.SpotdlApp` react. Keeping the message
types here (importing only ``textual`` + the view-model ``types``) means a screen
never imports the app, so there is no import cycle and the presentation contract
(CONTRACT I) holds.
"""

from __future__ import annotations

from textual.message import Message

from spotdl_cli.viewmodels.types import EntityRef


class NavigateTo(Message):
    """Request that the app open an entity screen for ``ref`` (CONTRACT C).

    Posted by any screen that resolves a row/URL to an :class:`EntityRef` (search
    results, a collection's track list); the app routes it through
    :func:`spotdl_cli.tui.router.open_entity`.
    """

    def __init__(self, ref: EntityRef) -> None:
        self.ref = ref
        super().__init__()


class AuthChanged(Message):
    """Signal that a login/logout/register happened (CONTRACT F).

    The auth screen posts this; the app re-runs ``AppStateViewModel.refresh_auth``
    and re-evaluates which feature sections are reachable. Wired here in Task 4 so
    the seam exists before the auth screen lands (Task 10).
    """


class DegradedChanged(Message):
    """Report the degraded state of the latest search/resolve (CONTRACT F, spec §10).

    The search screen posts this whenever a search or paste-resolve completes with
    (or without) ``degraded_sources``; the app folds ``degraded`` into the session so
    the status bar's degraded badge tracks the most recent resolution.
    """

    def __init__(self, degraded: bool) -> None:
        self.degraded = degraded
        super().__init__()
