from typing import TYPE_CHECKING, Any, Dict, List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar, handle_appbar

if TYPE_CHECKING:
    from spotdl.console.tui.screens.download import DownloadScreen

TR = i18n.tr

_YES = "confirm.yes"
_NO = "confirm.no"


def _bool_label(value: bool) -> str:
    return TR(_YES) if value else TR(_NO)


def build_summary_lines(options: Dict[str, Any]) -> List[str]:
    audio_providers = options.get("audio_providers") or ["youtube-music"]
    lyrics_providers = options.get("lyrics_providers") or []

    lines = [
        TR(
            "confirm.line_format",
            format=str(options.get("format", "mp3")).upper(),
            bitrate=str(options.get("bitrate", "auto")),
        ),
        TR("confirm.line_audio", provider=", ".join(audio_providers)),
        TR(
            "confirm.line_lyrics",
            enabled=_bool_label(bool(lyrics_providers)),
            provider=", ".join(lyrics_providers) if lyrics_providers else "-",
        ),
        TR(
            "confirm.line_lrc",
            enabled=_bool_label(bool(options.get("generate_lrc"))),
        ),
        TR("confirm.line_threads", threads=str(options.get("threads", 4))),
        TR("confirm.line_overwrite", overwrite=str(options.get("overwrite", "skip"))),
        TR("confirm.line_output", dir=str(options.get("output_dir", ""))),
    ]

    if options.get("m3u"):
        lines.append(TR("confirm.line_m3u", path=str(options["m3u"])))
    if options.get("sponsor_block"):
        lines.append(TR("confirm.line_sponsor_block"))
    if options.get("only_verified_results"):
        lines.append(TR("confirm.line_verified_only"))

    return lines


class ConfirmScreen(Screen):
    BINDINGS = [
        Binding("escape", "modify", "modify"),
    ]

    def __init__(
        self, operation: str, songs: List[Any], options: Dict[str, Any]
    ) -> None:
        super().__init__()
        self.operation = operation
        self.songs = songs
        self.options = options

    def compose(self) -> ComposeResult:
        yield AppBar(TR("appbar.title"))
        with Center():
            with Vertical(id="confirm-box", classes="box"):
                yield Static(
                    TR("confirm.title", count=str(len(self.songs))),
                    classes="menu-title",
                )
                for line in build_summary_lines(self.options):
                    yield Static(f"- {line}", classes="menu-hint")
                yield Static(TR("confirm.hint"), classes="menu-hint")
                with Center(classes="row"):
                    yield Button(
                        TR("confirm.btn_download"),
                        variant="primary",
                        id="confirm-download-btn",
                    )
                    yield Button(TR("confirm.btn_modify"), id="confirm-modify-btn")

    def action_modify(self) -> None:
        self._modify()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if handle_appbar(self, event):
            return
        if event.button.id == "confirm-modify-btn":
            self._modify()
        elif event.button.id == "confirm-download-btn":
            self._download()

    def _modify(self) -> None:
        self.app.pop_screen()
        self.app.pop_screen()

    def _download(self) -> None:
        from spotdl.console.tui.screens.download import DownloadScreen

        self.app.switch_screen(
            DownloadScreen(self.operation, self.songs, self.options)
        )
