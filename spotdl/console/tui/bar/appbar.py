from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.bar.footer import VersionFooter

TR = i18n.tr


class AppBar(Horizontal):
    def __init__(self, title: str = "", classes: str = "") -> None:
        super().__init__(id="appbar", classes=classes)
        self._title = title

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value

    def compose(self) -> ComposeResult:
        yield Static(self._title, id="appbar-title")
        yield Button(TR("appbar.menu"), id="appbar-menu")
        yield Button(TR("appbar.help"), id="appbar-help")

    def set_title(self, title: str) -> None:
        self._title = title
        try:
            self.query_one("#appbar-title", Static).update(title)
        except Exception:
            pass

    def refresh_labels(self) -> None:
        try:
            self.query_one("#appbar-menu", Button).label = TR("appbar.menu")
            self.query_one("#appbar-help", Button).label = TR("appbar.help")
        except Exception:
            pass


def refresh_all_screens(app: Any) -> None:
    for screen in app.screen_stack:
        try:
            screen.query_one(AppBar).refresh_labels()
        except Exception:
            pass
        refresh_language = getattr(screen, "refresh_language", None)
        if callable(refresh_language):
            try:
                refresh_language()
            except Exception:
                pass
        try:
            screen.query_one(VersionFooter).refresh_language()
        except Exception:
            pass


def handle_appbar(screen: Any, event: Button.Pressed) -> bool:
    button_id = event.button.id
    if button_id == "appbar-menu":
        from spotdl.console.tui.bar.menupopover import MenuPopover

        screen.app.push_screen(MenuPopover())
        return True
    if button_id == "appbar-help":
        from spotdl.console.tui.screens.help import HelpScreen

        screen.app.push_screen(HelpScreen())
        return True
    return False
