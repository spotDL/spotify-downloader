"""Main Textual application for SpotDL CLI."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static


class SpotDLApp(App):
    """SpotDL TUI Application."""

    TITLE = "SpotDL"
    SUB_TITLE = "Multi-platform Music Downloader"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "search", "Search"),
        ("d", "downloads", "Downloads"),
        ("?", "help", "Help"),
    ]

    CSS = """
    Screen {
        background: $surface;
    }

    #main-content {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Static(
            "Welcome to SpotDL!\n\n"
            "Press 's' to search for songs\n"
            "Press 'd' to view downloads\n"
            "Press '?' for help",
            id="main-content",
        )
        yield Footer()

    def action_search(self) -> None:
        """Open search screen."""
        self.notify("Search coming soon!")

    def action_downloads(self) -> None:
        """Open downloads screen."""
        self.notify("Downloads coming soon!")

    def action_help(self) -> None:
        """Show help."""
        self.notify("Help coming soon!")
