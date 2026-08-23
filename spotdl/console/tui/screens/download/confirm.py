from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar, VersionFooter, handle_appbar

if TYPE_CHECKING:
    from spotdl.console.tui.screens.download.download import DownloadScreen

TR = i18n.tr

_YES = "confirm.yes"
_NO = "confirm.no"


def _bool_label(value: bool) -> str:
    return TR(_YES) if value else TR(_NO)


@dataclass
class OptionCardData:
    label: str
    value: str
    sub: str = ""


def build_option_cards(options: Dict[str, Any]) -> List[OptionCardData]:
    audio_providers = options.get("audio_providers") or ["youtube-music"]
    lyrics_providers = options.get("lyrics_providers") or []
    lrc_status = _bool_label(bool(options.get("generate_lrc")))

    cards = [
        OptionCardData(
            label=TR("confirm.card_format"),
            value=f"{str(options.get('format', 'mp3')).upper()} @ {str(options.get('bitrate', 'auto'))}",
            sub=TR(
                "confirm.sub_output",
                template=str(
                    options.get("output_template", "{artists} - {title}.{output-ext}")
                ),
            ),
        ),
        OptionCardData(
            label=TR("confirm.card_audio"),
            value=", ".join(audio_providers),
            sub=TR("confirm.sub_audio_provider"),
        ),
        OptionCardData(
            label=TR("confirm.card_lyrics"),
            value=", ".join(lyrics_providers) if lyrics_providers else TR(_NO),
            sub=f"LRC: {lrc_status}",
        ),
        OptionCardData(
            label=TR("confirm.card_threads"),
            value=TR("confirm.val_threads", count=str(options.get("threads", 4))),
            sub=TR(
                "confirm.sub_overwrite",
                mode=str(options.get("overwrite", "skip")),
            ),
        ),
        OptionCardData(
            label=TR("confirm.card_output"),
            value=str(options.get("output_dir", "")),
        ),
    ]

    extras = []
    if options.get("m3u"):
        extras.append(f"M3U: {options['m3u']}")
    if options.get("sponsor_block"):
        extras.append("SponsorBlock")
    if options.get("only_verified_results"):
        extras.append(TR("confirm.extra_verified"))

    if extras:
        cards.append(
            OptionCardData(
                label=TR("confirm.card_filters"),
                value=" | ".join(extras),
            )
        )

    return cards


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
                with VerticalScroll():
                    with Vertical(id="confirm-grid"):
                        for card in build_option_cards(self.options):
                            with Vertical(classes="confirm-card"):
                                yield Label(card.label, classes="confirm-card-label")
                                yield Static(card.value, classes="confirm-card-val")
                                if card.sub:
                                    yield Static(card.sub, classes="confirm-card-sub")
                yield Static(TR("confirm.hint"), classes="menu-hint")
                with Center(classes="row"):
                    yield Button(
                        TR("confirm.btn_download"),
                        variant="primary",
                        id="confirm-download-btn",
                    )
                    yield Button(TR("confirm.btn_modify"), id="confirm-modify-btn")
        yield VersionFooter()

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
        from spotdl.console.tui.screens.download.download import DownloadScreen

        self.app.switch_screen(DownloadScreen(self.operation, self.songs, self.options))

    def refresh_language(self) -> None:
        try:
            self.query_one(AppBar).set_title(TR("appbar.title"))
            self.query_one(".menu-title", Static).update(
                TR("confirm.title", count=str(len(self.songs)))
            )
            self.query_one(".menu-hint", Static).update(TR("confirm.hint"))
            self.query_one("#confirm-download-btn", Button).label = TR(
                "confirm.btn_download"
            )
            self.query_one("#confirm-modify-btn", Button).label = TR(
                "confirm.btn_modify"
            )
            grid = self.query_one("#confirm-grid", Vertical)
            grid.remove_children()
            for card in build_option_cards(self.options):
                card_box = Vertical(classes="confirm-card")
                card_box.mount(Label(card.label, classes="confirm-card-label"))
                card_box.mount(Static(card.value, classes="confirm-card-val"))
                if card.sub:
                    card_box.mount(Static(card.sub, classes="confirm-card-sub"))
                grid.mount(card_box)
            self.query_one(VersionFooter).refresh_language()
        except Exception:
            pass
