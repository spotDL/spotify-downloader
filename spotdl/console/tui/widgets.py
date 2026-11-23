"""
Reusable widgets of the interface.
"""

from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Input, Static

from spotdl.console.tui import i18n
from spotdl.types.song import Song

TR = i18n.tr


class ConfirmQuitModal(ModalScreen[bool]):
    """
    Dialog that asks before quitting while downloads are still running.
    """

    BINDINGS = [
        Binding("escape", "stay", "cancel"),
    ]

    def __init__(self, active: int) -> None:
        """
        Create the dialog.

        ### Arguments
        - active: Number of downloads that are still running.
        """

        super().__init__()
        self.active = active

    def compose(self) -> ComposeResult:
        """
        Build the warning and the buttons.
        """

        with Vertical(id="quit-modal"):
            yield Static(TR("quit.title"), classes="menu-title")
            yield Static(TR("quit.active", count=str(self.active)))
            with Horizontal(classes="bottom-buttons"):
                yield Button(TR("quit.confirm"), variant="error", id="quit-yes-btn")
                yield Button(TR("common.cancel"), id="quit-no-btn")

    def action_stay(self) -> None:
        """
        Close the dialog and keep the application running.
        """

        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Quit or keep running.
        """

        self.dismiss(event.button.id == "quit-yes-btn")


def is_download_link(value: str) -> bool:
    """
    Check whether a typed value is an http or https link.

    ### Arguments
    - value: Text typed by the user.
    """

    parsed = urlparse(value.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


class FailedLinksModal(ModalScreen[Optional[Dict[str, str]]]):
    """
    Dialog to give a download link for each song that could not be found.
    """

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
    ]

    def __init__(self, songs: List[Song]) -> None:
        """
        Create the dialog.

        ### Arguments
        - songs: Songs that failed.
        """

        super().__init__()
        self.songs = songs

    def compose(self) -> ComposeResult:
        """
        Build one link input per failed song.
        """

        with Vertical(id="links-modal"):
            yield Static(TR("links.title"), classes="menu-title")
            yield Static(TR("links.hint"), classes="hint")
            with VerticalScroll(id="links-list"):
                for index, song in enumerate(self.songs):
                    yield Static(song.display_name, classes="links-song")
                    yield Input(placeholder=TR("links.ph"), id=f"link-{index}")
            with Horizontal(classes="bottom-buttons"):
                yield Button(TR("links.retry"), variant="primary", id="links-ok-btn")
                yield Button(TR("common.cancel"), id="links-cancel-btn")

    def action_cancel(self) -> None:
        """
        Close the dialog without retrying.
        """

        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Retry with the typed links or cancel.
        """

        if event.button.id == "links-cancel-btn":
            self.dismiss(None)
            return

        links: Dict[str, str] = {}
        for index, song in enumerate(self.songs):
            value = self.query_one(f"#link-{index}", Input).value.strip()
            if not value:
                continue
            if not is_download_link(value):
                self.app.notify(
                    TR("links.invalid", name=song.display_name), severity="error"
                )
                return
            links[song.url] = value
        self.dismiss(links)


class DirModal(ModalScreen[Path]):
    """
    Dialog to pick an output directory, typed or chosen from a tree.
    """

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
        Binding("enter", "confirm", "confirm"),
    ]

    def __init__(self, start: Path) -> None:
        """
        Create the dialog.

        ### Arguments
        - start: Directory shown when the dialog opens.
        """

        super().__init__()
        self.start = start

    def compose(self) -> ComposeResult:
        """
        Build the path input, the directory tree and the buttons.
        """

        with Vertical(id="dir-modal"):
            yield Static(TR("query.dir_label"), classes="menu-title")
            yield Input(
                str(self.start),
                placeholder=TR("query.ph_dir"),
                id="dir-input",
            )
            yield DirectoryTree(str(self.start), id="dir-tree")
            with Horizontal(classes="bottom-buttons"):
                yield Button(TR("common.ok"), variant="primary", id="ok-btn")
                yield Button(TR("common.cancel"), id="cancel-btn")

    def action_cancel(self) -> None:
        """
        Close the dialog without choosing a directory.
        """

        self.app.pop_screen()

    def action_confirm(self) -> None:
        """
        Close the dialog with the typed directory.
        """

        self._confirm()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Confirm or cancel the dialog.
        """

        if event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "ok-btn":
            self._confirm()

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """
        Copy the selected directory into the input.
        """

        self.query_one("#dir-input", Input).value = str(event.path)

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """
        Copy the selected file path into the input.
        """

        self.query_one("#dir-input", Input).value = str(event.path)

    def on_tree_node_highlighted(self, event: DirectoryTree.NodeHighlighted) -> None:
        """
        Copy the highlighted path into the input.
        """

        node = event.node
        if node is not None and node.data is not None:
            self.query_one("#dir-input", Input).value = str(node.data.path)

    def _confirm(self) -> None:
        path = Path(self.query_one("#dir-input", Input).value.strip() or ".")
        try:
            path = path.expanduser().resolve()
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.app.notify(str(exc), severity="error")
            return
        self.dismiss(path)

    def refresh_language(self) -> None:
        """
        Translate the dialog to the current language.
        """

        self.query_one(".menu-title", Static).update(TR("query.dir_label"))
        self.query_one("#dir-input", Input).placeholder = TR("query.ph_dir")
        self.query_one("#ok-btn", Button).label = TR("common.ok")
        self.query_one("#cancel-btn", Button).label = TR("common.cancel")
