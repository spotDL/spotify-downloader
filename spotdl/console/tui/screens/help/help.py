from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Markdown, TabbedContent, TabPane

from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar, VersionFooter, handle_appbar
from spotdl.console.tui.screens.download.builder import CommandBuilder

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
                    with Horizontal(classes="row"):
                        yield Button(TR("common.back"), id="help-back-btn")
            with TabPane(TR("cmdbuilder.tab_label"), id="help-builder"):
                yield CommandBuilder()
        yield VersionFooter()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_command_builder(self) -> None:
        try:
            tabs = self.query_one("#help-tabs", TabbedContent)
            tabs.active = "help-builder"
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if handle_appbar(self, event):
            return
        if event.button.id in ("help-back-btn", "cmd-back"):
            self.action_back()

    def refresh_language(self) -> None:
        try:
            appbar = self.query_one(AppBar)
            appbar.set_title(TR("appbar.title"))
        except Exception:
            pass
        try:
            tabs = self.query_one("#help-tabs", TabbedContent)
            tabs.get_tab("help-reference").label = TR("help.title")
            tabs.get_tab("help-builder").label = TR("cmdbuilder.tab_label")
        except Exception:
            pass
        try:
            self.query_one(Markdown).update(TR("help.body"))
            self.query_one("#help-back-btn", Button).label = TR("common.back")
        except Exception:
            pass
        try:
            self.query_one(CommandBuilder).refresh_language()
        except Exception:
            pass
        try:
            self.query_one(VersionFooter).refresh_language()
        except Exception:
            pass
