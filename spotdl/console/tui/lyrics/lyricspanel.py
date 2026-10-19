"""
Screen that shows the lyrics of a song and can save them as an LRC file.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from pyperclip import PyperclipException
from pyperclip import copy as clipboard_copy
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, RichLog, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.lyrics.lrclib import fetch_lyrics

TR = i18n.tr


class LyricsScreen(Screen):
    """
    Lyrics viewer for a single song.
    """

    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("c", "copy", "copy"),
        Binding("s", "save_lrc", "save"),
    ]

    def __init__(
        self, song: Any, output_dir: Optional[Union[str, Path]] = None
    ) -> None:
        """
        Create the screen.

        ### Arguments
        - song: Song whose lyrics are shown.
        - output_dir: Directory where the LRC file is saved, the current
        directory when not given.
        """

        super().__init__()
        self.song = song
        self.output_dir = Path(output_dir) if output_dir else None
        self._text: Optional[str] = None

    def compose(self) -> ComposeResult:
        """
        Build the title, the lyrics area and the buttons.
        """

        with Vertical(id="lyrics-box", classes="box"):
            yield Static(TR("lyrics.loading"), id="lyrics-title", classes="menu-title")
            yield RichLog(id="lyrics-body", markup=False, highlight=False, wrap=True)
            with Horizontal(classes="row"):
                yield Button(TR("lyrics.copy"), variant="primary", id="lyrics-copy-btn")
                yield Button(TR("lyrics.save_lrc"), id="lyrics-save-btn")
                yield Button(TR("common.back"), id="lyrics-back-btn")
            yield Static("", id="lyrics-status")

    def on_mount(self) -> None:
        """
        Start fetching the lyrics.
        """

        self._fetch_lyrics()

    @work(thread=True, exclusive=True, group="lyrics")
    def _fetch_lyrics(self) -> None:
        data = fetch_lyrics(self.song)
        self.app.call_from_thread(self._show_lyrics, data)

    def _show_lyrics(self, data: Optional[Dict[str, Any]]) -> None:
        if not self.is_attached:
            return
        title = self.query_one("#lyrics-title", Static)
        body = self.query_one("#lyrics-body", RichLog)
        name = getattr(self.song, "name", "") or ""
        artist = getattr(self.song, "artist", "") or ""
        text = (data.get("synced") or data.get("plain")) if data else None
        self._text = text
        if text:
            title.update(TR("lyrics.title", name=name, artist=artist))
            body.write(text)
        else:
            title.update(TR("lyrics.title_no_text", name=name))
            body.write(TR("lyrics.empty"))

    def action_back(self) -> None:
        """
        Go back to the previous screen.
        """

        self.app.pop_screen()

    def action_copy(self) -> None:
        """
        Copy the lyrics to the clipboard.
        """

        self._copy()

    def action_save_lrc(self) -> None:
        """
        Save the lyrics as an LRC file.
        """

        self._save_lrc()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Run the action of the pressed button.
        """

        if event.button.id == "lyrics-back-btn":
            self.action_back()
        elif event.button.id == "lyrics-copy-btn":
            self._copy()
        elif event.button.id == "lyrics-save-btn":
            self._save_lrc()

    def _copy(self) -> None:
        status = self.query_one("#lyrics-status", Static)
        if not self._text:
            status.update(TR("lyrics.empty"))
            return
        try:
            clipboard_copy(self._text)
        except PyperclipException:
            status.update(TR("lyrics.copy_failed"))
            return
        status.update(TR("lyrics.copied"))

    def _save_lrc(self) -> None:
        status = self.query_one("#lyrics-status", Static)
        if not self._text:
            status.update(TR("lyrics.empty"))
            return
        name = getattr(self.song, "name", "track")
        artist = getattr(self.song, "artist", "artist")
        filename = "".join(c for c in f"{artist} - {name}.lrc" if c not in '<>:"/\\|?*')
        target_dir = self.output_dir or Path.cwd()
        out_path = target_dir / filename
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(self._text, encoding="utf-8")
        except OSError as exc:
            status.update(TR("lyrics.save_failed", error=exc))
            return
        status.update(TR("lyrics.saved", path=out_path.name))

    def refresh_language(self) -> None:
        """
        Translate the screen to the current language.
        """

        name = getattr(self.song, "name", "") or ""
        artist = getattr(self.song, "artist", "") or ""
        if self._text:
            self.query_one("#lyrics-title", Static).update(
                TR("lyrics.title", name=name, artist=artist)
            )
        self.query_one("#lyrics-copy-btn", Button).label = TR("lyrics.copy")
        self.query_one("#lyrics-save-btn", Button).label = TR("lyrics.save_lrc")
        self.query_one("#lyrics-back-btn", Button).label = TR("common.back")
