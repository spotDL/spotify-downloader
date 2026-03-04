"""NavRail — Vertical navigation sidebar widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from spotdl_cli.theme import Theme


class NavItem(Widget):
    """A single navigation item with icon and label."""

    DEFAULT_CSS = """
    NavItem {
        height: 3;
        width: 100%;
        padding: 0 1;
        content-align: left middle;
    }
    NavItem:hover {
        background: #2c2e32;
    }
    NavItem.active {
        background: #1c1e20;
    }
    NavItem.active .nav-accent {
        color: #e8764b;
    }
    """

    is_active: reactive[bool] = reactive(False)

    def __init__(
        self,
        icon: str,
        label: str,
        screen_name: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._icon = icon
        self._label = label
        self.screen_name = screen_name

    def compose(self) -> ComposeResult:
        yield Static(
            f" {self._icon}  {self._label}",
            classes="nav-item-text",
        )

    def watch_is_active(self, value: bool) -> None:
        if value:
            self.add_class("active")
        else:
            self.remove_class("active")


class NavRail(Widget):
    """Vertical navigation sidebar, always visible."""

    DEFAULT_CSS = """
    NavRail {
        dock: left;
        width: 22;
        background: #161819;
        border-right: solid #232326;
        padding: 1 0;
    }
    NavRail.collapsed {
        width: 5;
    }
    NavRail .nav-brand {
        height: 3;
        width: 100%;
        content-align: center middle;
        color: #e8764b;
        text-style: bold;
        margin-bottom: 1;
    }
    NavRail .nav-separator {
        height: 1;
        width: 100%;
        margin: 1 0;
        color: #232326;
    }
    """

    collapsed: reactive[bool] = reactive(False)
    active_screen: reactive[str] = reactive("search")

    NAV_ITEMS = [
        (Theme.ICON_SEARCH, "Search", "search"),
        (Theme.ICON_DOWNLOAD, "Downloads", "queue"),
        (Theme.ICON_SETTINGS, "Settings", "settings"),
        (Theme.ICON_ACCOUNT, "Account", "account"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("spotdl", classes="nav-brand")
        yield Static("─" * 20, classes="nav-separator")
        with Vertical(id="nav-items"):
            for icon, label, screen in self.NAV_ITEMS:
                yield NavItem(
                    icon,
                    label,
                    screen,
                    id=f"nav-{screen}",
                )

    def watch_collapsed(self, value: bool) -> None:
        if value:
            self.add_class("collapsed")
        else:
            self.remove_class("collapsed")

    def watch_active_screen(self, screen_name: str) -> None:
        for item in self.query(NavItem):
            item.is_active = item.screen_name == screen_name

    def on_click(self, event) -> None:
        for item in self.query(NavItem):
            if item is event.widget or item in event.widget.ancestors:
                self.active_screen = item.screen_name
                self.app.push_screen(item.screen_name)
                break

    def toggle(self) -> None:
        self.collapsed = not self.collapsed
