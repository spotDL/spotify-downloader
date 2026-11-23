"""
Screen to change the interface language.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Header, OptionList, Static
from textual.widgets.option_list import Option

from spotdl.console.tui import i18n
from spotdl.console.tui.navigation import VersionFooter, refresh_all_screens

TR = i18n.tr


class LanguageScreen(Screen):
    """
    List of the available languages.
    """

    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    def compose(self) -> ComposeResult:
        """
        Build the language list.
        """

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
        """
        Go back to the previous screen.
        """

        self.app.pop_screen()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """
        Apply the selected language and go back.
        """

        code = event.option.id or "en"
        i18n.set_language(code)
        self.query_one("#status", Static).update(
            TR("language.saved", lang=i18n.LANGUAGES[code])
        )
        self.app.pop_screen()
        refresh_all_screens(self.app)

    def refresh_language(self) -> None:
        """
        Translate the screen to the current language.
        """

        self.query_one(".menu-title", Static).update(TR("language.title"))
        self.query_one(".menu-hint", Static).update(TR("language.hint"))
        self.query_one(VersionFooter).refresh_language()
