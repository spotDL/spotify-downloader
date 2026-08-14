from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Click
from textual.screen import ModalScreen
from textual.widgets import Button, OptionList, Rule, Static
from textual.widgets.option_list import Option

from spotdl.console.tui import i18n

TR = i18n.tr


class MenuPopover(ModalScreen[Any]):
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
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    #popover-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #popover-title-row {
        height: auto;
        align: center middle;
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
    }
    #popover-actions Button {
        width: 100%;
        margin: 0 0 1 0;
    }
    """

    def compose(self) -> ComposeResult:
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
                yield Button(TR("popover.quit"), id="popover-quit-btn")

    @staticmethod
    def _build_lang_options() -> list:
        current = i18n.get_language()
        options = []
        for code, name in i18n.available_languages().items():
            prefix = "[*] " if code == current else "[ ] "
            options.append(Option(prefix + name, id=code))
        return options

    def on_mount(self) -> None:
        langs = self.query_one("#popover-langs", OptionList)
        for index, option in enumerate(langs.options):
            if option.id == i18n.get_language():
                langs.highlighted = index
                break

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        code = event.option.id or "en"
        if code in i18n.available_languages():
            i18n.set_language(code)
            self._refresh_home()
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "popover-close-btn":
            self.dismiss(None)
        elif button_id == "popover-help-btn":
            self._open_screen("help-reference")
        elif button_id == "popover-builder-btn":
            self._open_screen("help-builder")
        elif button_id == "popover-quit-btn":
            self.app.exit()

    def on_click(self, event: Click) -> None:
        if event.widget is self:
            self.dismiss(None)

    def _open_screen(self, tab: str) -> None:
        from spotdl.console.tui.screens.help import HelpScreen

        self.app.pop_screen()
        self.app.push_screen(HelpScreen(initial_tab=tab))

    def action_back(self) -> None:
        self.dismiss(None)

    def _refresh_home(self) -> None:
        from spotdl.console.tui.screens.menu import MainMenuScreen

        for screen in self.app.screen_stack:
            if isinstance(screen, MainMenuScreen) and hasattr(
                screen, "refresh_language"
            ):
                screen.refresh_language()
                break
