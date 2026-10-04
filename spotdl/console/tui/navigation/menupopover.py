"""
Modal menu opened from the application bar.
"""

from typing import Any, List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Click
from textual.screen import ModalScreen
from textual.widgets import Button, OptionList, Rule, Static
from textual.widgets.option_list import Option

from spotdl.console.tui import i18n
from spotdl.console.tui.navigation.appbar import refresh_all_screens

TR = i18n.tr


class MenuPopover(ModalScreen[Any]):
    """
    Menu with the language selector and shortcuts to help, setup and quit.
    """

    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    CSS = """
    MenuPopover {
        align: right top;
        padding: 1 1 0 0;
    }
    #popover-card {
        width: auto;
        min-width: 36;
        max-width: 60;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    #popover-title {
        text-style: bold;
        color: $accent;
    }
    #popover-title-row {
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    #popover-title-row #popover-title {
        width: 1fr;
    }
    #popover-close-btn {
        width: auto;
        min-width: 8;
        margin-left: 1;
    }
    #popover-langs {
        height: auto;
        max-height: 8;
        margin-bottom: 1;
    }
    #popover-actions {
        height: auto;
        width: 100%;
    }
    #popover-actions Button {
        width: 1fr;
        margin: 0 0 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        """
        Build the language list and the action buttons.
        """

        with Vertical(id="popover-card"):
            with Horizontal(id="popover-title-row"):
                yield Static(TR("appbar.menu"), id="popover-title")
                yield Button(TR("popover.close"), id="popover-close-btn")
            yield Static(TR("popover.language"))
            yield OptionList(*self._build_lang_options(), id="popover-langs")
            yield Rule()
            yield Static(TR("popover.actions"))
            with Vertical(id="popover-actions"):
                yield Button(TR("popover.help"), id="popover-help-btn")
                yield Button(TR("popover.builder"), id="popover-builder-btn")
                yield Button(TR("popover.setup"), id="popover-setup-btn")
                yield Button(TR("popover.quit"), id="popover-quit-btn")

    @staticmethod
    def _build_lang_options() -> List[Option]:
        current = i18n.get_language()
        options = []
        for code, name in i18n.available_languages().items():
            prefix = "[*] " if code == current else "[ ] "
            options.append(Option(prefix + name, id=code))
        return options

    def on_mount(self) -> None:
        """
        Highlight the active language.
        """

        langs = self.query_one("#popover-langs", OptionList)
        for index, option in enumerate(langs.options):
            if option.id == i18n.get_language():
                langs.highlighted = index
                break

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """
        Apply the selected language and close the menu.
        """

        code = event.option.id or "en"
        if code in i18n.available_languages():
            i18n.set_language(code)
            refresh_all_screens(self.app)
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Run the action of the pressed button.
        """

        button_id = event.button.id
        if button_id == "popover-close-btn":
            self.dismiss(None)
        elif button_id == "popover-help-btn":
            self._run_app_action("open_help('help-reference')")
        elif button_id == "popover-builder-btn":
            self._run_app_action("open_help('help-builder')")
        elif button_id == "popover-setup-btn":
            self._run_app_action("open_setup")
        elif button_id == "popover-quit-btn":
            self.app.exit()

    def on_click(self, event: Click) -> None:
        """
        Close the menu when clicking outside of it.
        """

        if event.widget is self:
            self.dismiss(None)

    def _run_app_action(self, action: str) -> None:
        self.dismiss(None)
        self.app.call_later(self.app.run_action, action)

    def action_back(self) -> None:
        """
        Close the menu.
        """

        self.dismiss(None)

    def refresh_language(self) -> None:
        """
        Translate the menu to the current language.
        """

        self.query_one("#popover-title", Static).update(TR("appbar.menu"))
        self.query_one("#popover-close-btn", Button).label = TR("popover.close")
        self.query_one("#popover-help-btn", Button).label = TR("popover.help")
        self.query_one("#popover-builder-btn", Button).label = TR("popover.builder")
        self.query_one("#popover-setup-btn", Button).label = TR("popover.setup")
        self.query_one("#popover-quit-btn", Button).label = TR("popover.quit")
        langs = self.query_one("#popover-langs", OptionList)
        langs.clear_options()
        langs.add_options(self._build_lang_options())
