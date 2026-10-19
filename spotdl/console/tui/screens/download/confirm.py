"""
Screen that summarizes the chosen options before downloading.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.navigation import AppBar, VersionFooter
from spotdl.console.tui.screens.download.download import DownloadScreen

TR = i18n.tr


def _bool_label(value: bool) -> str:
    return TR("confirm.yes") if value else TR("confirm.no")


@dataclass
class OptionCardData:
    """
    Content of one summary card.

    ### Attributes
    - label: Card title.
    - value: Main value shown in the card.
    - sub: Optional secondary line.
    """

    label: str
    value: str
    sub: str = ""


def build_option_cards(options: Dict[str, Any]) -> List[OptionCardData]:
    """
    Build the summary cards for the chosen options.

    ### Arguments
    - options: Options chosen in the query screen.

    ### Returns
    - The cards to show, the extras card only when some extra is enabled.
    """

    audio_providers = options.get("audio_providers") or ["youtube-music"]
    lyrics_providers = options.get("lyrics_providers") or []
    audio_format = str(options.get("format", "mp3")).upper()
    bitrate = str(options.get("bitrate", "auto"))
    output_template = options.get("output_template", "{artists} - {title}.{output-ext}")

    cards = [
        OptionCardData(
            label=TR("confirm.card_format"),
            value=f"{audio_format} @ {bitrate}",
            sub=TR("confirm.sub_output", template=str(output_template)),
        ),
        OptionCardData(
            label=TR("confirm.card_audio"),
            value=", ".join(audio_providers),
            sub=TR("confirm.sub_audio_provider"),
        ),
        OptionCardData(
            label=TR("confirm.card_lyrics"),
            value=(
                ", ".join(lyrics_providers) if lyrics_providers else TR("confirm.no")
            ),
            sub=f"LRC: {_bool_label(bool(options.get('generate_lrc')))}",
        ),
        OptionCardData(
            label=TR("confirm.card_threads"),
            value=TR("confirm.val_threads", count=str(options.get("threads", 4))),
            sub=TR("confirm.sub_overwrite", mode=str(options.get("overwrite", "skip"))),
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


def _card_widget(card: OptionCardData) -> Vertical:
    children = [
        Label(card.label, classes="confirm-card-label"),
        Static(card.value, classes="confirm-card-val"),
    ]
    if card.sub:
        children.append(Static(card.sub, classes="confirm-card-sub"))
    return Vertical(*children, classes="confirm-card")


class ConfirmScreen(Screen):
    """
    Shows the chosen options and starts the download or goes back to change them.
    """

    BINDINGS = [
        Binding("escape", "modify", "modify"),
    ]

    def __init__(
        self, operation: str, songs: List[Any], options: Dict[str, Any]
    ) -> None:
        """
        Create the screen.

        ### Arguments
        - operation: Operation that will run, such as "download".
        - songs: Songs selected in the track list.
        - options: Options chosen in the query screen.
        """

        super().__init__()
        self.operation = operation
        self.songs = songs
        self.options = options

    def compose(self) -> ComposeResult:
        """
        Build the summary cards and the buttons.
        """

        yield AppBar(TR("appbar.title"))
        with Center():
            with Vertical(id="confirm-box", classes="box"):
                yield Static(
                    TR("confirm.title", count=str(len(self.songs))),
                    classes="menu-title",
                )
                with VerticalScroll():
                    yield Vertical(
                        *(
                            _card_widget(card)
                            for card in build_option_cards(self.options)
                        ),
                        id="confirm-grid",
                    )
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
        """
        Go back to the query screen to change the options.
        """

        self._modify()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Start the download or go back to change the options.
        """

        if event.button.id == "confirm-modify-btn":
            self._modify()
        elif event.button.id == "confirm-download-btn":
            self.app.switch_screen(
                DownloadScreen(self.operation, self.songs, self.options)
            )

    def _modify(self) -> None:
        self.app.pop_screen()
        self.app.pop_screen()

    def refresh_language(self) -> None:
        """
        Translate the screen to the current language.
        """

        self.query_one(AppBar).set_title(TR("appbar.title"))
        self.query_one(".menu-title", Static).update(
            TR("confirm.title", count=str(len(self.songs)))
        )
        self.query_one(".menu-hint", Static).update(TR("confirm.hint"))
        self.query_one("#confirm-download-btn", Button).label = TR(
            "confirm.btn_download"
        )
        self.query_one("#confirm-modify-btn", Button).label = TR("confirm.btn_modify")
        grid = self.query_one("#confirm-grid", Vertical)
        grid.remove_children()
        grid.mount_all(
            [_card_widget(card) for card in build_option_cards(self.options)]
        )
        self.query_one(VersionFooter).refresh_language()
