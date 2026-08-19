from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar, VersionFooter, handle_appbar
from spotdl.console.tui.history import load_history
from spotdl.console.tui.screens.download.query import QueryScreen
from spotdl.console.tui.screens.download.simple_op import SimpleOpScreen
from spotdl.console.tui.screens.web.web import WebScreen
from spotdl.console.tui.versions import (
    fetch_upstream_latest_version,
    get_cached_upstream_latest_version,
    set_cached_upstream_latest_version,
)
from spotdl.utils.ffmpeg import is_ffmpeg_installed

TR = i18n.tr

_CARDS = [
    ("sync", "card-sync", "\u27f3", QueryScreen, "sync"),
    ("save", "card-save", "\u25a4", QueryScreen, "save"),
    ("meta", "card-meta", "\u270e", SimpleOpScreen, "meta"),
    ("url", "card-url", "\u29c9", SimpleOpScreen, "url"),
    ("web", "card-web", "\u2302", WebScreen, None),
]

_HISTORY_LIMIT = 5


def _format_recent(history) -> str:
    urls = history.get("urls", [])[:_HISTORY_LIMIT]
    downloads = history.get("downloads", [])[:_HISTORY_LIMIT]
    if not urls and not downloads:
        return TR("home.recent_empty")

    lines = []
    if urls:
        lines.append(TR("home.recent_urls_title"))
        for entry in urls:
            lines.append(f"  - {entry.get('query', '')}")
    if downloads:
        lines.append(TR("home.recent_downloads_title"))
        for entry in downloads:
            name = entry.get("name", "")
            url = entry.get("url", "")
            ok = entry.get("ok", 0)
            err = entry.get("err", 0)
            if url:
                lines.append(f"  - {name} ({url}) [{ok} OK, {err} err]")
            else:
                lines.append(f"  - {name} [{ok} OK, {err} err]")
    return "\n".join(lines)


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
            yield Static(_format_recent(load_history()), id="home-recent")
            if not is_ffmpeg_installed():
                yield Static(TR("query.no_ffmpeg"), id="ffmpeg-warn")
            yield Static("", id="status")
        yield VersionFooter()

    def on_mount(self) -> None:
        self.refresh_language()
        self.refresh_history()
        self.run_worker(self._check_upstream_version, thread=True, group="version")

    def _check_upstream_version(self) -> None:
        cached = get_cached_upstream_latest_version()
        if cached is None:
            cached = fetch_upstream_latest_version()
            if cached:
                set_cached_upstream_latest_version(cached)
        if cached:
            self.app.call_from_thread(self._apply_upstream_version, cached)

    def _apply_upstream_version(self, upstream_latest: str) -> None:
        try:
            self.query_one(VersionFooter).apply_upstream(upstream_latest)
        except Exception:
            pass

    def on_screen_resume(self) -> None:
        self.refresh_history()

    def refresh_history(self) -> None:
        try:
            self.query_one("#home-recent", Static).update(
                _format_recent(load_history())
            )
        except Exception:
            pass

    def refresh_language(self) -> None:
        try:
            appbar = self.query_one(AppBar)
            appbar.set_title(TR("appbar.title"))
        except Exception:
            pass
        try:
            self.query_one("#home-welcome", Static).update(TR("home.welcome"))
            self.refresh_history()
            for key, card_id, icon, _, _ in _CARDS:
                label = TR(f"menu.{key}")
                button = self.query_one(f"#{card_id}", Button)
                button.label = f"{icon} {label}"
                button.tooltip = label
            self.query_one("#home-new-download", Button).label = TR("home.new_download")
            self.query_one(VersionFooter).refresh_language()
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
