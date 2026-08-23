from pathlib import Path

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Input, Static

from spotdl.console.tui import i18n

TR = i18n.tr


class DirTreeSelectable(DirectoryTree):
    ALLOW_SELECT = True


class DirModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
        Binding("enter", "confirm", "confirm"),
    ]

    def __init__(self, start: Path) -> None:
        super().__init__()
        self.start = start

    def compose(self):
        with Vertical(id="dir-modal"):
            yield Static(TR("query.dir_label"), classes="menu-title")
            yield Input(
                str(self.start),
                placeholder=TR("query.ph_dir"),
                id="dir-input",
            )
            yield DirTreeSelectable(str(self.start), id="dir-tree")
            with Horizontal(classes="bottom-buttons"):
                yield Button(TR("common.ok"), variant="primary", id="ok-btn")
                yield Button(TR("common.cancel"), id="cancel-btn")

    def action_cancel(self) -> None:
        self.app.pop_screen()

    def action_confirm(self) -> None:
        self._confirm()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "ok-btn":
            self._confirm()

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self.query_one("#dir-input", Input).value = str(event.path)

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        self.query_one("#dir-input", Input).value = str(event.path)

    def on_tree_node_highlighted(self, event: DirectoryTree.NodeHighlighted) -> None:
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
        try:
            self.query_one(".menu-title", Static).update(TR("query.dir_label"))
            self.query_one("#dir-input", Input).placeholder = TR("query.ph_dir")
            self.query_one("#ok-btn", Button).label = TR("common.ok")
            self.query_one("#cancel-btn", Button).label = TR("common.cancel")
        except Exception:
            pass
