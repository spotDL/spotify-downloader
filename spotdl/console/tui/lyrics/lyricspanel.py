import logging
from typing import Any, Optional

from pyperclip import copy as clipboard_copy
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, RichLog, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.lyrics.lrclib import fetch_lyrics

TR = i18n.tr

logger = logging.getLogger(__name__)


class LyricsScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("c", "copy", "copy"),
    ]

    def __init__(self, song: Any) -> None:
        super().__init__()
        self.song = song
        self._text: Optional[str] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="lyrics-box", classes="box"):
            yield Static(TR("lyrics.loading"), id="lyrics-title", classes="menu-title")
            yield RichLog(id="lyrics-body", markup=False, highlight=False, wrap=True)
            with Horizontal(classes="row"):
                yield Button(TR("lyrics.copy"), variant="primary", id="lyrics-copy-btn")
                yield Button(TR("common.back"), id="lyrics-back-btn")
            yield Static("", id="lyrics-status")

    def on_mount(self) -> None:
        screen = self

        def run_fetch() -> None:
            try:
                data = fetch_lyrics(screen.song)
            except Exception as exc:
                logger.debug("lyrics fetch error: %s", exc)
                data = None
            screen.app.call_from_thread(screen._show_lyrics, data)

        self.run_worker(run_fetch, thread=True, exclusive=True, group="lyrics")

    def _show_lyrics(self, data: Optional[dict]) -> None:
        try:
            title = self.query_one("#lyrics-title", Static)
            body = self.query_one("#lyrics-body", RichLog)
        except Exception:
            return
        name = getattr(self.song, "name", "") or ""
        artist = getattr(self.song, "artist", "") or ""
        header = TR("lyrics.title", name=name, artist=artist)
        if data is None:
            title.update(header)
            body.write(TR("lyrics.empty"))
            return
        synced = data.get("synced") or ""
        plain = data.get("plain") or ""
        text = synced or plain
        self._text = text
        title.update(header if text else TR("lyrics.title_no_text", name=name))
        if text:
            body.write(text)
        else:
            body.write(TR("lyrics.empty"))

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_copy(self) -> None:
        self._copy()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "lyrics-back-btn":
            self.action_back()
        elif event.button.id == "lyrics-copy-btn":
            self._copy()

    def _copy(self) -> None:
        status = self.query_one("#lyrics-status", Static)
        if not self._text:
            status.update(TR("lyrics.empty"))
            return
        try:
            clipboard_copy(self._text)
            status.update(TR("lyrics.copied"))
        except Exception:
            status.update(TR("lyrics.copy_failed"))
