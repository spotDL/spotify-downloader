from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar, handle_appbar
from spotdl.console.tui.screens.query import QueryScreen
from spotdl.console.tui.screens.simple_op import SimpleOpScreen
from spotdl.console.tui.screens.web import WebScreen
from spotdl.utils.ffmpeg import is_ffmpeg_installed

TR = i18n.tr

_CARDS = [
    ("sync", "card-sync", "\u27f3", QueryScreen, "sync"),
    ("save", "card-save", "\u25a4", QueryScreen, "save"),
    ("meta", "card-meta", "\u270e", SimpleOpScreen, "meta"),
    ("url", "card-url", "\u29c9", SimpleOpScreen, "url"),
    ("web", "card-web", "\u2302", WebScreen, None),
]


class MainMenuScreen(Screen):
    BINDINGS = [
        Binding("escape", "quit_app", "quit"),
    ]

    MENU_OPTIONS = [
        ("download", "download"),
        ("sync", "sync"),
        ("save", "save"),
        ("meta", "meta"),
        ("url", "url"),
        ("web", "web"),
        ("help", "help"),
        ("language", "language"),
        ("quit", "quit"),
    ]

    def compose(self) -> ComposeResult:
        yield AppBar(TR("appbar.title"))
        with Vertical(id="home"):
            yield Static(TR("home.welcome"), id="home-welcome")
            with Horizontal(classes="home-cards"):
                for _, card_id, icon, _, _ in _CARDS:
                    yield Button(icon, id=card_id, classes="card")
            yield Button(
                TR("home.new_download"),
                variant="primary",
                id="home-new-download",
                classes="primary-action",
            )
            yield Static(TR("home.recent_empty"), id="home-recent")
            if not is_ffmpeg_installed():
                yield Static(TR("query.no_ffmpeg"), id="ffmpeg-warn")
            yield Static("", id="status")

    def on_mount(self) -> None:
        self.refresh_language()

    def refresh_language(self) -> None:
        try:
            appbar = self.query_one(AppBar)
            appbar.set_title(TR("appbar.title"))
        except Exception:
            pass
        try:
            self.query_one("#home-welcome", Static).update(TR("home.welcome"))
            self.query_one("#home-recent", Static).update(TR("home.recent_empty"))
            for key, card_id, icon, _, _ in _CARDS:
                label = TR(f"menu.{key}")
                button = self.query_one(f"#{card_id}", Button)
                button.label = f"{icon} {label}"
                button.tooltip = label
            self.query_one("#home-new-download", Button).label = TR("home.new_download")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if handle_appbar(self, event):
            return
        button_id = event.button.id
        if button_id == "home-new-download":
            self.app.push_screen(QueryScreen("download"))
            return
        for _, card_id, _, screen_cls, arg in _CARDS:
            if button_id == card_id:
                if arg is not None:
                    self.app.push_screen(screen_cls(arg))
                else:
                    self.app.push_screen(screen_cls())
                return

    def action_quit_app(self) -> None:
        self.app.exit()
