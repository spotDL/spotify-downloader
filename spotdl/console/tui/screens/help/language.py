from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Header, OptionList, Static
from textual.widgets.option_list import Option

from spotdl.console.tui import i18n
from spotdl.console.tui.bar import VersionFooter

TR = i18n.tr


class LanguageScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Center():
            with Vertical(id="menu-box", classes="box"):
                yield Static(TR("language.title"), classes="menu-title")
                options = [
                    Option(name, id=code)
                    for code, name in i18n.available_languages().items()
                ]
                yield OptionList(*options)
                yield Static(TR("language.hint"), classes="menu-hint")
                yield Static("", id="status")
        yield VersionFooter()

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        code = event.option.id or "en"
        i18n.set_language(code)
        self.query_one("#status", Static).update(
            TR("language.saved", lang=i18n.LANGUAGES[code])
        )
        self.app.pop_screen()
        from spotdl.console.tui.bar.appbar import refresh_all_screens

        refresh_all_screens(self.app)
