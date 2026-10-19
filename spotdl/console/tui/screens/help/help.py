"""
Help screen with the usage reference and the command builder.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Markdown, TabbedContent, TabPane

from spotdl.console.tui import i18n
from spotdl.console.tui.navigation import AppBar, VersionFooter
from spotdl.console.tui.screens.download.builder import CommandBuilder

TR = i18n.tr


class HelpScreen(Screen):
    """
    Screen with a reference tab and a command builder tab.
    """

    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("c", "command_builder", "command builder"),
    ]

    def __init__(self, initial_tab: str = "help-reference") -> None:
        """
        Create the screen.

        ### Arguments
        - initial_tab: Id of the tab shown first.
        """

        super().__init__()
        self.initial_tab = initial_tab

    def compose(self) -> ComposeResult:
        """
        Build the tabs.
        """

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
        """
        Go back to the previous screen.
        """

        self.app.pop_screen()

    def action_command_builder(self) -> None:
        """
        Switch to the command builder tab.
        """

        self.query_one("#help-tabs", TabbedContent).active = "help-builder"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Go back when a back button is pressed.
        """

        if event.button.id in ("help-back-btn", "cmd-back"):
            self.action_back()

    def refresh_language(self) -> None:
        """
        Translate the screen to the current language.
        """

        self.query_one(AppBar).set_title(TR("appbar.title"))
        tabs = self.query_one("#help-tabs", TabbedContent)
        tabs.get_tab("help-reference").label = TR("help.title")
        tabs.get_tab("help-builder").label = TR("cmdbuilder.tab_label")
        self.query_one(Markdown).update(TR("help.body"))
        self.query_one("#help-back-btn", Button).label = TR("common.back")
        self.query_one(CommandBuilder).refresh_language()
        self.query_one(VersionFooter).refresh_language()
