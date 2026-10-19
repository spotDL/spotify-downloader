"""
Screen for the single input operations `meta` and `url`.
"""

import asyncio
import io
import logging
import sys
from typing import TYPE_CHECKING, Callable, Tuple, cast

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RichLog, Static

from spotdl.console.meta import meta
from spotdl.console.tui import i18n
from spotdl.console.tui.log_handler import BufferLogHandler
from spotdl.console.tui.navigation import AppBar, VersionFooter
from spotdl.console.url import url

if TYPE_CHECKING:
    from spotdl.console.tui.app import SpotdlApp

TR = i18n.tr


class LiveStreamWriter(io.TextIOBase):
    """
    Text stream that passes every non empty line to a callback.
    """

    def __init__(self, callback: Callable[[str], None]) -> None:
        """
        Create the stream.

        ### Arguments
        - callback: Function that receives each line.
        """

        super().__init__()
        self.callback = callback

    def write(self, s: str) -> int:
        """
        Pass every non empty line of `s` to the callback.
        """

        for line in s.splitlines():
            if line.strip():
                self.callback(line.strip())
        return len(s)


class SimpleOpScreen(Screen):
    """
    Runs `spotdl meta` on a path or `spotdl url` on a query and shows the output.
    """

    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    def __init__(self, operation: str) -> None:
        """
        Create the screen.

        ### Arguments
        - operation: Either "meta" or "url".
        """

        super().__init__()
        self.operation = operation

    def _texts(self) -> Tuple[str, str, str, str]:
        if self.operation == "meta":
            return (
                TR("meta.title"),
                TR("meta.path_label"),
                TR("meta.ph_path"),
                TR("meta.btn_run"),
            )
        return (
            TR("url.title"),
            TR("query.url_label"),
            TR("url.ph_query"),
            TR("url.btn_run"),
        )

    def compose(self) -> ComposeResult:
        """
        Build the input, the buttons and the output log.
        """

        title, label, placeholder, run_label = self._texts()
        yield AppBar(TR("appbar.title"))
        with Center():
            with Vertical(id="simple-box", classes="box"):
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
        """
        Go back to the previous screen.
        """

        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Run the operation or go back.
        """

        if event.button.id == "back-btn":
            self.action_back()
        elif event.button.id == "run-btn":
            self.run_operation()

    def _stream_message(self, message: str) -> None:
        if not self.is_attached:
            return
        self.query_one("#op-log", RichLog).write(message)
        self.query_one("#status", Static).update(message[:80])

    def run_operation(self) -> None:
        """
        Validate the input and start the operation in a worker thread.
        """

        value = self.query_one("#op-input", Input).value.strip()
        if not value:
            self.query_one("#status", Static).update(
                TR("meta.no_path" if self.operation == "meta" else "url.no_query")
            )
            return

        self.query_one("#op-log", RichLog).clear()
        self.query_one("#run-btn", Button).disabled = True
        self.query_one("#status", Static).update(
            TR("meta.running" if self.operation == "meta" else "url.running")
        )
        self._run_in_thread(value)

    @work(thread=True, exclusive=True, group="simple")
    def _run_in_thread(self, value: str) -> None:
        app = cast("SpotdlApp", self.app)

        def log_callback(message: str) -> None:
            app.call_from_thread(self._stream_message, message)

        log_handler = BufferLogHandler(log_callback)
        log_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        spotdl_logger = logging.getLogger("spotdl")
        spotdl_logger.addHandler(log_handler)
        old_stdout = sys.stdout

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

            sys.stdout = LiveStreamWriter(log_callback)
            try:
                if self.operation == "meta":
                    meta(query=[value], downloader=downloader)
                else:
                    url(query=[value], downloader=downloader)
            finally:
                sys.stdout = old_stdout
        except Exception as exc:
            log_callback(TR("query.error", message=exc))
        finally:
            spotdl_logger.removeHandler(log_handler)
            app.call_from_thread(self._op_done)

    def _op_done(self) -> None:
        if not self.is_attached:
            return
        self.query_one("#run-btn", Button).disabled = False
        self.query_one("#status", Static).update(
            TR("meta.done" if self.operation == "meta" else "url.done")
        )

    def refresh_language(self) -> None:
        """
        Translate the screen to the current language.
        """

        title, label, placeholder, run_label = self._texts()
        self.query_one(AppBar).set_title(TR("appbar.title"))
        self.query_one("#simple-title", Static).update(title)
        self.query_one("#simple-label", Label).update(label)
        self.query_one("#op-input", Input).placeholder = placeholder
        self.query_one("#run-btn", Button).label = run_label
        self.query_one("#back-btn", Button).label = TR("query.btn_back")
        self.query_one(VersionFooter).refresh_language()
