"""
Top application bar shared by the TUI screens.
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.navigation.footer import VersionFooter

TR = i18n.tr


class AppBar(Horizontal):
    """
    Bar with the screen title and the menu and help buttons.
    """

    def __init__(self, title: str = "", classes: str = "") -> None:
        """
        Create the bar.

        ### Arguments
        - title: Text shown on the left side of the bar.
        - classes: CSS classes applied to the bar.
        """

        super().__init__(id="appbar", classes=classes)
        self._title = title

    @property
    def title(self) -> str:
        """
        Title shown in the bar.
        """

        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value

    def compose(self) -> ComposeResult:
        """
        Build the title and the buttons.
        """

        yield Static(self._title, id="appbar-title")
        yield Static("", id="appbar-activity")
        yield Button(
            TR("appbar.settings"), id="appbar-settings", action="app.open_settings"
        )
        yield Button(TR("appbar.menu"), id="appbar-menu", action="app.open_menu")
        yield Button(TR("appbar.help"), id="appbar-help", action="app.open_help")
        yield Button(TR("appbar.quit"), id="appbar-quit", action="app.quit")

    def on_mount(self) -> None:
        """
        Keep the active download summary up to date.
        """

        self.set_interval(0.5, self._refresh_activity)

    def _refresh_activity(self) -> None:
        manager = getattr(self.app, "downloads", None)
        if manager is None:
            return

        widget = self.query_one("#appbar-activity", Static)
        count, percent = manager.aggregate()
        if count:
            widget.update(TR("appbar.activity", count=str(count), percent=str(percent)))
        else:
            widget.update("")

    def set_title(self, title: str) -> None:
        """
        Change the title and update the rendered label.

        ### Arguments
        - title: New title.
        """

        self._title = title
        if self.is_mounted:
            self.query_one("#appbar-title", Static).update(title)

    def refresh_labels(self) -> None:
        """
        Translate the button labels to the current language.
        """

        self.query_one("#appbar-settings", Button).label = TR("appbar.settings")
        self.query_one("#appbar-menu", Button).label = TR("appbar.menu")
        self.query_one("#appbar-help", Button).label = TR("appbar.help")
        self.query_one("#appbar-quit", Button).label = TR("appbar.quit")


def refresh_all_screens(app: App) -> None:
    """
    Translate every screen in the stack to the current language.

    ### Arguments
    - app: The running application.
    """

    for screen in app.screen_stack:
        for app_bar in screen.query(AppBar):
            app_bar.refresh_labels()
        for footer in screen.query(VersionFooter):
            footer.refresh_language()

        refresh_language = getattr(screen, "refresh_language", None)
        if callable(refresh_language):
            refresh_language()
