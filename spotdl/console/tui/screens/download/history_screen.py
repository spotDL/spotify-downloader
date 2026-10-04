"""
Screen with the download history, searchable and sortable.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pyperclip import PyperclipException
from pyperclip import copy as clipboard_copy
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Static
from textual.widgets.data_table import ColumnKey, RowKey

from spotdl.console.tui import i18n
from spotdl.console.tui.history import (
    clear_history,
    delete_download_entry,
    load_history,
)
from spotdl.console.tui.navigation import AppBar, VersionFooter
from spotdl.console.tui.screens.download.query import QueryScreen

TR = i18n.tr

_COLUMNS = [
    ("date", "history.col_date", 17),
    ("name", "history.col_name", None),
    ("tracks", "history.col_tracks", 10),
    ("status", "history.col_status", 16),
    ("query", "history.col_query", None),
]

_SORT_LABELS = [
    "history.btn_sort_date",
    "history.btn_sort_name",
    "history.btn_sort_tracks",
]


def _format_time(timestamp: Optional[float]) -> str:
    if not timestamp:
        return "-"
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    except (OverflowError, OSError, ValueError):
        return "-"


def _status_badge(entry: Dict[str, Any]) -> str:
    badge = f"[green]✓ {entry.get('ok', 0)}[/green]"
    if entry.get("err", 0) > 0:
        badge += f" [red]✗ {entry['err']}[/red]"
    return badge


class HistoryScreen(Screen):
    """
    Table of past downloads with details, search, sorting and actions.
    """

    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("r", "redownload", "redownload"),
        Binding("c", "copy_url", "copy_url"),
        Binding("d", "delete_entry", "delete_entry"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._all_entries: List[Dict[str, Any]] = []
        self._row_map: Dict[RowKey, Dict[str, Any]] = {}
        self._selected_entry: Optional[Dict[str, Any]] = None
        self._sort_mode = 0

    def compose(self) -> ComposeResult:
        """
        Build the toolbar, the history table, the details box and the buttons.
        """

        yield AppBar(TR("appbar.title"))
        with Vertical(id="history-container", classes="box"):
            yield Static(TR("history.title"), id="history-title", classes="menu-title")

            with Horizontal(id="history-toolbar"):
                yield Input(
                    placeholder=TR("history.search_placeholder"),
                    id="history-search-input",
                )
                yield Button(TR("history.btn_sort"), id="history-sort-btn")
                yield Button(TR("history.btn_clear"), id="history-clear-btn")

            table: DataTable = DataTable(
                zebra_stripes=True, cursor_type="row", id="history-table"
            )
            for key, label_key, width in _COLUMNS:
                table.add_column(TR(label_key), key=key, width=width)
            yield table

            with Vertical(id="history-details-box"):
                yield Static(
                    TR("history.details_title"),
                    id="history-details-title",
                    classes="section-title",
                )
                yield Static("", id="history-details-body")

            with Horizontal(classes="row"):
                yield Button(
                    TR("history.btn_redownload"),
                    variant="primary",
                    id="history-redownload-btn",
                )
                yield Button(TR("history.btn_copy_url"), id="history-copy-btn")
                yield Button(TR("history.btn_delete"), id="history-delete-btn")
                yield Button(TR("history.btn_close"), id="history-back-btn")
            yield Static("", id="history-status")
        yield VersionFooter()

    def on_mount(self) -> None:
        """
        Load the history into the table.
        """

        self._reload_data()

    def _reload_data(self) -> None:
        history_data = load_history()
        self._all_entries = history_data.get("downloads", [])

        if not self._all_entries:
            self._all_entries = [
                {
                    "id": entry.get("id") or "",
                    "name": entry.get("query", ""),
                    "url": entry.get("query", ""),
                    "count": 1,
                    "ok": 0,
                    "err": 0,
                    "skipped": 0,
                    "operation": entry.get("operation", "download"),
                    "time": entry.get("time"),
                }
                for entry in history_data.get("urls", [])
            ]
        self._apply_filter_and_sort()

    def on_input_changed(self, event: Input.Changed) -> None:
        """
        Filter the table while typing in the search box.
        """

        if event.input.id == "history-search-input":
            self._apply_filter_and_sort()

    def _apply_filter_and_sort(self) -> None:
        search = self.query_one("#history-search-input", Input).value.strip().lower()
        entries = [
            entry
            for entry in self._all_entries
            if not search
            or search in str(entry.get("name", "")).lower()
            or search in str(entry.get("url", "")).lower()
        ]

        if self._sort_mode == 1:
            entries.sort(key=lambda entry: str(entry.get("name", "")).lower())
        elif self._sort_mode == 2:
            entries.sort(key=lambda entry: int(entry.get("count", 0)), reverse=True)
        else:
            entries.sort(key=lambda entry: float(entry.get("time") or 0), reverse=True)

        self._render_table(entries)

    def _render_table(self, entries: List[Dict[str, Any]]) -> None:
        table = self.query_one("#history-table", DataTable)
        table.clear()
        self._row_map.clear()
        self._selected_entry = None

        for entry in entries:
            row_key = table.add_row(
                _format_time(entry.get("time")),
                entry.get("name") or entry.get("url") or "-",
                str(entry.get("count", 0)),
                _status_badge(entry),
                entry.get("url", ""),
            )
            self._row_map[row_key] = entry

        if entries:
            self._selected_entry = entries[0]
            self._update_details(entries[0])
        else:
            self.query_one("#history-details-body", Static).update(TR("history.empty"))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """
        Show the details of the highlighted entry.
        """

        entry = self._row_map.get(event.row_key)
        if entry:
            self._selected_entry = entry
            self._update_details(entry)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        Open the selected entry again in the download screen.
        """

        entry = self._row_map.get(event.row_key)
        if entry:
            self._selected_entry = entry
            self.action_redownload()

    def _update_details(self, entry: Dict[str, Any]) -> None:
        summary = TR(
            "history.details_summary",
            name=entry.get("name") or "-",
            date=_format_time(entry.get("time")),
        )
        lines = [
            f"[bold]{summary}[/bold]",
            TR(
                "history.details_tracks",
                total=str(entry.get("count", 0)),
                ok=str(entry.get("ok", 0)),
                err=str(entry.get("err", 0)),
                skipped=str(entry.get("skipped", 0)),
            ),
            TR("history.details_query", query=entry.get("url") or "-"),
        ]
        if entry.get("log_summary"):
            lines.append(f"[dim]{entry['log_summary']}[/dim]")

        self.query_one("#history-details-body", Static).update("\n".join(lines))

    def _selected_query(self) -> Optional[str]:
        if not self._selected_entry:
            return None
        return self._selected_entry.get("url") or self._selected_entry.get("name")

    def action_back(self) -> None:
        """
        Go back to the previous screen.
        """

        self.app.pop_screen()

    def action_redownload(self) -> None:
        """
        Open the selected entry in the query screen.
        """

        query = self._selected_query()
        if query and self._selected_entry:
            operation = self._selected_entry.get("operation", "download")
            self.app.push_screen(QueryScreen(operation, prefill=query))

    def action_copy_url(self) -> None:
        """
        Copy the query of the selected entry to the clipboard.
        """

        query = self._selected_query()
        if not query:
            return
        status = self.query_one("#history-status", Static)
        try:
            clipboard_copy(query)
        except PyperclipException:
            status.update(TR("history.copy_failed"))
            return
        status.update(TR("history.copied"))

    def action_delete_entry(self) -> None:
        """
        Delete the selected entry from the history.
        """

        entry_id = self._selected_entry.get("id") if self._selected_entry else None
        if entry_id:
            delete_download_entry(entry_id)
            self._reload_data()
            self.query_one("#history-status", Static).update(TR("history.deleted"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Run the action of the pressed button.
        """

        button_id = event.button.id
        if button_id == "history-back-btn":
            self.action_back()
        elif button_id == "history-redownload-btn":
            self.action_redownload()
        elif button_id == "history-copy-btn":
            self.action_copy_url()
        elif button_id == "history-delete-btn":
            self.action_delete_entry()
        elif button_id == "history-sort-btn":
            self._sort_mode = (self._sort_mode + 1) % len(_SORT_LABELS)
            event.button.label = TR(_SORT_LABELS[self._sort_mode])
            self._apply_filter_and_sort()
        elif button_id == "history-clear-btn":
            clear_history()
            self._reload_data()
            self.query_one("#history-status", Static).update(TR("history.cleared"))

    def refresh_language(self) -> None:
        """
        Translate the screen to the current language.
        """

        self.query_one(AppBar).set_title(TR("appbar.title"))
        self.query_one("#history-title", Static).update(TR("history.title"))
        self.query_one("#history-details-title", Static).update(
            TR("history.details_title")
        )
        self.query_one("#history-search-input", Input).placeholder = TR(
            "history.search_placeholder"
        )
        self.query_one("#history-redownload-btn", Button).label = TR(
            "history.btn_redownload"
        )
        self.query_one("#history-copy-btn", Button).label = TR("history.btn_copy_url")
        self.query_one("#history-delete-btn", Button).label = TR("history.btn_delete")
        self.query_one("#history-clear-btn", Button).label = TR("history.btn_clear")
        self.query_one("#history-back-btn", Button).label = TR("history.btn_close")
        self.query_one("#history-sort-btn", Button).label = TR(
            _SORT_LABELS[self._sort_mode]
        )

        table = self.query_one(DataTable)
        for key, label_key, _ in _COLUMNS:
            table.columns[ColumnKey(key)].label = Text(TR(label_key))
        table.refresh()

        self.query_one(VersionFooter).refresh_language()
        self._reload_data()
