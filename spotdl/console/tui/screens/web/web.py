import threading
from typing import cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar, VersionFooter, handle_appbar
from spotdl.console.tui.settings import build_downloader_settings
from spotdl.console.web import web
from spotdl.types.options import DownloaderOptions, WebOptions

TR = i18n.tr


class WebScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    def compose(self) -> ComposeResult:
        yield AppBar(TR("appbar.title"))
        with Center():
            with Vertical(classes="box"):
                yield Static(TR("web.title"), id="web-title", classes="menu-title")
                yield Static(TR("web.info"), id="web-info")
                yield Static(
                    TR("web.starting", host="127.0.0.1", port="8080"),
                    id="web-starting",
                )
                with Horizontal(classes="row"):
                    yield Button(TR("common.back"), id="back-btn")
                yield Static("", id="status")
        yield VersionFooter()

    def on_mount(self) -> None:
        def run_web() -> None:
            web_settings: WebOptions = {
                "host": "127.0.0.1",
                "port": 8080,
                "keep_alive": False,
                "enable_tls": False,
                "allowed_origins": None,
                "key_file": None,
                "cert_file": None,
                "ca_file": None,
                "keep_sessions": False,
                "web_use_output_dir": False,
            }
            downloader_settings = build_downloader_settings(
                {
                    "audio_providers": ["youtube-music"],
                    "lyrics_providers": ["genius"],
                    "format": "mp3",
                    "bitrate": "auto",
                    "threads": 4,
                    "output_dir": None,
                    "save_file": None,
                }
            )
            web(web_settings, cast(DownloaderOptions, downloader_settings))

        threading.Thread(target=run_web, daemon=True).start()

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if handle_appbar(self, event):
            return
        if event.button.id == "back-btn":
            self.action_back()

    def refresh_language(self) -> None:
        try:
            appbar = self.query_one(AppBar)
            appbar.set_title(TR("appbar.title"))
        except Exception:
            pass
        try:
            self.query_one("#web-title", Static).update(TR("web.title"))
            self.query_one("#web-info", Static).update(TR("web.info"))
            self.query_one("#web-starting", Static).update(
                TR("web.starting", host="127.0.0.1", port="8080")
            )
            self.query_one("#back-btn", Button).label = TR("common.back")
        except Exception:
            pass
        try:
            self.query_one(VersionFooter).refresh_language()
        except Exception:
            pass
