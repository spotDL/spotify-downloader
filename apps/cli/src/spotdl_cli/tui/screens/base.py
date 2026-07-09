"""``SpotdlScreen`` — the base every screen extends (CONTRACT §1).

It nails down the frame shared by all screens — a :class:`NavRail` sidebar left of a
``#content-region`` that fills, with a :class:`StatusBar` + ``Footer`` docked below
(nothing floats) — plus the global ``escape`` back-binding, a typed ``vm_factory``
accessor, and a ``show_error`` shortcut onto the app's toast. Screens therefore hold
no wiring of their own — they implement :meth:`compose_content` (which fills the
content region) and delegate everything else to a view-model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Static

from spotdl_cli.tui.widgets.nav_rail import NavRail
from spotdl_cli.tui.widgets.status_bar import StatusBar
from spotdl_cli.viewmodels.base import ErrorDisplay

if TYPE_CHECKING:
    from spotdl_cli.tui.app import SpotdlApp
    from spotdl_cli.viewmodels.factory import ViewModelFactory


class SpotdlScreen(Screen[None]):
    """Common frame + global bindings for every spotDL screen."""

    BINDINGS = [
        Binding("escape", "back", "Back", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal(id="app-body"):
            yield NavRail(id="nav-rail")
            with Vertical(id="content-region"):
                yield from self.compose_content()
        yield StatusBar(id="status-bar")
        yield Footer()

    def compose_content(self) -> ComposeResult:
        """Screen body inside ``#content-region`` (subclasses override)."""
        return iter(())

    def on_mount(self) -> None:
        # The session is loaded before any section screen mounts, so the status bar
        # renders populated on first paint; refreshed later via ``AuthChanged``.
        self.query_one(StatusBar).update_session(self.spotdl_app.session)

    @property
    def spotdl_app(self) -> SpotdlApp:
        return cast("SpotdlApp", self.app)

    @property
    def vm_factory(self) -> ViewModelFactory:
        """The app's single wired factory — the only way a screen reaches a VM."""
        return self.spotdl_app.vm_factory

    def show_error(self, error: ErrorDisplay) -> None:
        """Surface a view-model ``ErrorDisplay`` as the app's toast (CONTRACT G)."""
        self.spotdl_app.show_error(error)

    def action_back(self) -> None:
        """Pop this screen if it was pushed; never pop a section's base screen."""
        if len(self.app.screen_stack) > 1:
            self.app.pop_screen()


class PlaceholderScreen(SpotdlScreen):
    """A titled stand-in for a section/entity screen not yet built.

    Task 4 ships the shell before the feature screens (Tasks 5–10); every section
    mode and every router target resolves to one of these until its real screen is
    registered, so navigation is exercisable end-to-end from day one.
    """

    def __init__(self, name: str, title: str) -> None:
        super().__init__(name=name)
        self._title = title

    def compose_content(self) -> ComposeResult:
        yield Static(f"{self._title}\n\n(coming soon)", classes="placeholder")
