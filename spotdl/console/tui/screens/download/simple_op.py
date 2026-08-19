import asyncio
import io
import logging
import sys
from typing import TYPE_CHECKING, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RichLog, Static

from spotdl.console.meta import meta
from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar, VersionFooter, handle_appbar
from spotdl.console.url import url

if TYPE_CHECKING:
    from spotdl.console.tui.app import SpotdlApp

TR = i18n.tr


class SimpleOpScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    def __init__(self, operation: str) -> None:
        super().__init__()
        self.operation = operation

    def compose(self) -> ComposeResult:
        yield AppBar(TR("appbar.title"))
        with Center():
            with Vertical(id="simple-box", classes="box"):
                if self.operation == "meta":
                    title = TR("meta.title")
                    label = TR("meta.path_label")
                    placeholder = TR("meta.ph_path")
                    run_label = TR("meta.btn_run")
                else:
                    title = TR("url.title")
                    label = TR("query.url_label")
                    placeholder = TR("url.ph_query")
                    run_label = TR("url.btn_run")

                yield Static(title, id="simple-title", classes="menu-title")
                yield Label(label, id="simple-label")
                yield Input(placeholder=placeholder, id="op-input")
                with Horizontal(classes="row"):
                    yield Button(run_label, variant="primary", id="run-btn")
                    yield Button(TR("query.btn_back"), id="back-btn")
                yield RichLog(highlight=True, id="op-log", wrap=True)
                yield Static("", id="status")
        yield VersionFooter()

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if handle_appbar(self, event):
            return
        if event.button.id == "back-btn":
            self.action_back()
        elif event.button.id == "run-btn":
            self.run_operation()

    def run_operation(self) -> None:
        value = self.query_one("#op-input", Input).value.strip()
        if not value:
            self.query_one("#status", Static).update(
                TR("meta.no_path" if self.operation == "meta" else "url.no_query")
            )
            return

        log = self.query_one("#op-log", RichLog)
        log.clear()
        self.query_one("#run-btn", Button).disabled = True
        self.query_one("#status", Static).update(
            TR("meta.running" if self.operation == "meta" else "url.running")
        )

        screen = self
        operation = self.operation

        def run_operation() -> None:
            app = cast("SpotdlApp", screen.app)
            buffer = io.StringIO()
            stream_handler = logging.StreamHandler(buffer)
            logging.getLogger("spotdl").addHandler(stream_handler)

            try:
                app.state.ensure_spotify(user_auth=False)
                downloader = app.state.ensure_downloader(
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
                asyncio.set_event_loop(downloader.loop)

                old_stdout = sys.stdout
                sys.stdout = buffer
                try:
                    if operation == "meta":
                        meta(query=[value], downloader=downloader)
                    else:
                        url(query=[value], downloader=downloader)
                finally:
                    sys.stdout = old_stdout
            except Exception as exc:
                buffer.write(f"{type(exc).__name__}: {exc}\n")
            finally:
                logging.getLogger("spotdl").removeHandler(stream_handler)
                output = buffer.getvalue()
                app.call_from_thread(screen._op_done, output)

        self.run_worker(run_operation, thread=True, exclusive=True, group="simple")

    def _op_done(self, output: str) -> None:
        log = self.query_one("#op-log", RichLog)
        for line in output.splitlines():
            log.write(line)
        self.query_one("#run-btn", Button).disabled = False
        self.query_one("#status", Static).update(
            TR("meta.done" if self.operation == "meta" else "url.done")
        )

    def refresh_language(self) -> None:
        try:
            appbar = self.query_one(AppBar)
            appbar.set_title(TR("appbar.title"))
        except Exception:
            pass

        if self.operation == "meta":
            title = TR("meta.title")
            label = TR("meta.path_label")
            placeholder = TR("meta.ph_path")
            run_label = TR("meta.btn_run")
        else:
            title = TR("url.title")
            label = TR("query.url_label")
            placeholder = TR("url.ph_query")
            run_label = TR("url.btn_run")

        try:
            self.query_one("#simple-title", Static).update(title)
            self.query_one("#simple-label", Label).update(label)
            self.query_one("#op-input", Input).placeholder = placeholder
            self.query_one("#run-btn", Button).label = run_label
            self.query_one("#back-btn", Button).label = TR("query.btn_back")
        except Exception:
            pass
        try:
            self.query_one(VersionFooter).refresh_language()
        except Exception:
            pass
