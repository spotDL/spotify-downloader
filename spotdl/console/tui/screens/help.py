from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Markdown, TabbedContent, TabPane

from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar
from spotdl.console.tui.screens.builder import CommandBuilder

TR = i18n.tr


class HelpScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("c", "command_builder", "command builder"),
    ]

    def __init__(self, initial_tab: str = "help-reference") -> None:
        super().__init__()
        self.initial_tab = initial_tab

    def compose(self) -> ComposeResult:
        yield AppBar(TR("appbar.title"))
        with TabbedContent(id="help-tabs", initial=self.initial_tab):
            with TabPane(TR("help.title"), id="help-reference"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Markdown(TR("help.body"))
            with TabPane(TR("cmdbuilder.tab_label"), id="help-builder"):
                with VerticalScroll(classes="tab-scroll"):
                    yield CommandBuilder()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_command_builder(self) -> None:
        try:
            tabs = self.query_one("#help-tabs", TabbedContent)
            tabs.active = "help-builder"
        except Exception:
            pass
