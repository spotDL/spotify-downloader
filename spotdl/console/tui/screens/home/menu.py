"""
Home screen with the main actions and the latest activity.
"""

from typing import Any, Dict, List, Optional, Tuple

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.history import load_history
from spotdl.console.tui.navigation import AppBar, VersionFooter
from spotdl.console.tui.screens.download.history_screen import HistoryScreen
from spotdl.console.tui.screens.download.query import QueryScreen
from spotdl.console.tui.screens.download.simple_op import SimpleOpScreen
from spotdl.console.tui.screens.help import HelpScreen
from spotdl.console.tui.screens.web.web import WebScreen
from spotdl.console.tui.versions import (
    fetch_upstream_latest_version,
    get_cached_upstream_latest_version,
    set_cached_upstream_latest_version,
)
from spotdl.utils.ffmpeg import is_ffmpeg_installed

TR = i18n.tr

_CARDS = [
    ("history", "card-history", "\U0001f553", HistoryScreen, None),
    ("sync", "card-sync", "⟳", QueryScreen, "sync"),
    ("save", "card-save", "▤", QueryScreen, "save"),
    ("builder", "card-builder", "⚙", HelpScreen, "help-builder"),
    ("meta", "card-meta", "✎", SimpleOpScreen, "meta"),
    ("url", "card-url", "⧉", SimpleOpScreen, "url"),
    ("web", "card-web", "⌂", WebScreen, None),
]


def _get_recent_summary(
    history: Dict[str, List[Dict[str, Any]]],
) -> Tuple[str, Optional[str]]:
    downloads = history.get("downloads", [])
    if downloads:
        last = downloads[0]
        name = last.get("name") or "-"
        counts = TR("download.summary_ok", ok=last.get("ok", 0), err=last.get("err", 0))
        return f"[bold]{name}[/bold]  [dim]({counts})[/dim]", last.get("url") or None
    urls = history.get("urls", [])
    if urls:
        last_url = urls[0].get("query", "")
        return f"[bold]{last_url}[/bold]", last_url
    return TR("home.recent_empty"), None


class MainMenuScreen(Screen):
    """
    First screen of the interface.
    """

    BINDINGS = [
        Binding("escape", "quit_app", "quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._last_recent_url: Optional[str] = None

    def compose(self) -> ComposeResult:
        """
        Build the main action, the shortcut cards and the recent activity box.
        """

        yield AppBar(TR("appbar.title"))
        with Vertical(id="home"):
            yield Static(TR("home.hero_title"), id="home-hero-title")
            yield Static(TR("home.subtitle"), id="home-subtitle")

            yield Button(
                TR("home.btn_add_download"),
                variant="primary",
                id="home-new-download",
                classes="primary-action",
            )

            with Horizontal(classes="home-cards"):
                for key, card_id, icon, _, _ in _CARDS:
                    yield Button(
                        f"{icon} {TR(f'home.card_{key}')}", id=card_id, classes="card"
                    )

            with Vertical(id="home-recent-box"):
                yield Static(TR("home.recent_downloads_title"), id="home-recent-title")
                yield Static("", id="home-recent-summary")
                with Horizontal(id="home-recent-actions"):
                    yield Button(TR("home.view_history"), id="home-view-history")
                    yield Button(
                        TR("history.btn_redownload"),
                        variant="primary",
                        id="home-recent-redownload",
                    )

            if not is_ffmpeg_installed():
                yield Static(TR("query.no_ffmpeg"), id="ffmpeg-warn")
            yield Static("", id="status")
        yield VersionFooter()

    def on_mount(self) -> None:
        """
        Fill the texts and check for a newer release in the background.
        """

        self.refresh_language()
        self.run_worker(self._check_upstream_version, thread=True, group="version")

    def _check_upstream_version(self) -> None:
        latest = get_cached_upstream_latest_version()
        if latest is None:
            latest = fetch_upstream_latest_version()
            if latest:
                set_cached_upstream_latest_version(latest)
        if latest:
            self.app.call_from_thread(self._apply_upstream_version, latest)

    def _apply_upstream_version(self, upstream_latest: str) -> None:
        for footer in self.query(VersionFooter):
            footer.apply_upstream(upstream_latest)

    def on_screen_resume(self) -> None:
        """
        Update the recent activity when coming back to this screen.
        """

        self.refresh_history()

    def refresh_history(self) -> None:
        """
        Show the latest download or query from the history.
        """

        history = load_history()
        summary_text, last_url = _get_recent_summary(history)
        self._last_recent_url = last_url
        self.query_one("#home-recent-summary", Static).update(summary_text)
        has_history = bool(history.get("downloads") or history.get("urls"))
        self.query_one("#home-recent-redownload", Button).display = bool(last_url)
        self.query_one("#home-view-history", Button).display = has_history

    def refresh_language(self) -> None:
        """
        Translate the screen to the current language.
        """

        self.query_one(AppBar).set_title(TR("appbar.title"))
        self.query_one("#home-hero-title", Static).update(TR("home.hero_title"))
        self.query_one("#home-subtitle", Static).update(TR("home.subtitle"))
        self.query_one("#home-new-download", Button).label = TR("home.btn_add_download")
        self.query_one("#home-recent-title", Static).update(
            TR("home.recent_downloads_title")
        )
        self.query_one("#home-view-history", Button).label = TR("home.view_history")
        self.query_one("#home-recent-redownload", Button).label = TR(
            "history.btn_redownload"
        )
        self.refresh_history()
        for key, card_id, icon, _, _ in _CARDS:
            button = self.query_one(f"#{card_id}", Button)
            button.label = f"{icon} {TR(f'home.card_{key}')}"
            button.tooltip = TR(f"menu.{key}")
        self.query_one(VersionFooter).refresh_language()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Open the screen that belongs to the pressed button.
        """

        button_id = event.button.id
        if button_id == "home-new-download":
            self.app.push_screen(QueryScreen("download"))
            return
        if button_id == "home-view-history":
            self.app.push_screen(HistoryScreen())
            return
        if button_id == "home-recent-redownload":
            if self._last_recent_url:
                self.app.push_screen(
                    QueryScreen("download", prefill=self._last_recent_url)
                )
            else:
                self.app.push_screen(HistoryScreen())
            return
        for _, card_id, _, screen_cls, arg in _CARDS:
            if button_id == card_id:
                self.app.push_screen(screen_cls() if arg is None else screen_cls(arg))
                return

    def action_quit_app(self) -> None:
        """
        Exit the application.
        """

        self.app.exit()
