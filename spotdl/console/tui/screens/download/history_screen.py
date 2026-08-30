from datetime import datetime
from typing import Any, Dict, List, Optional

from pyperclip import copy as clipboard_copy
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Static
from textual.widgets.data_table import RowKey

from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar, VersionFooter, handle_appbar
from spotdl.console.tui.history import (
    clear_history,
    delete_download_entry,
    load_history,
)
from spotdl.console.tui.screens.download.query import QueryScreen

TR = i18n.tr


def _format_time(timestamp: Optional[float]) -> str:
    if not timestamp:
        return "-"
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "-"


class HistoryScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("r", "redownload", "redownload"),
        Binding("c", "copy_url", "copy_url"),
        Binding("d", "delete_entry", "delete_entry"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._all_entries: List[Dict[str, Any]] = []
        self._filtered_entries: List[Dict[str, Any]] = []
        self._row_map: Dict[RowKey, Dict[str, Any]] = {}
        self._selected_entry: Optional[Dict[str, Any]] = None
        self._sort_mode = 0

    def compose(self) -> ComposeResult:
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
            table.add_column(TR("history.col_date"), key="date", width=17)
            table.add_column(TR("history.col_name"), key="name")
            table.add_column(TR("history.col_tracks"), key="tracks", width=10)
            table.add_column(TR("history.col_status"), key="status", width=16)
            table.add_column(TR("history.col_query"), key="query")
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
        self._reload_data()

    def _reload_data(self) -> None:
        history_data = load_history()
        self._all_entries = history_data.get("downloads", [])

        if not self._all_entries and history_data.get("urls"):
            for u in history_data.get("urls", []):
                self._all_entries.append(
                    {
                        "id": u.get("id") or "",
                        "name": u.get("query", ""),
                        "url": u.get("query", ""),
                        "count": 1,
                        "ok": 0,
                        "err": 0,
                        "skipped": 0,
                        "operation": u.get("operation", "download"),
                        "time": u.get("time"),
                    }
                )
        self._apply_filter_and_sort()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "history-search-input":
            self._apply_filter_and_sort()

    def _apply_filter_and_sort(self) -> None:
        query = ""
        try:
            query = self.query_one("#history-search-input", Input).value.strip().lower()
        except Exception:
            pass

        if query:
            self._filtered_entries = [
                e
                for e in self._all_entries
                if query in str(e.get("name", "")).lower()
                or query in str(e.get("url", "")).lower()
            ]
        else:
            self._filtered_entries = list(self._all_entries)

        if self._sort_mode == 1:
            self._filtered_entries.sort(key=lambda x: str(x.get("name", "")).lower())
        elif self._sort_mode == 2:
            self._filtered_entries.sort(
                key=lambda x: int(x.get("count", 0)), reverse=True
            )
        else:
            self._filtered_entries.sort(
                key=lambda x: float(x.get("time") or 0), reverse=True
            )

        self._render_table()

    def _render_table(self) -> None:
        table = self.query_one("#history-table", DataTable)
        table.clear()
        self._row_map.clear()
        self._selected_entry = None

        for entry in self._filtered_entries:
            date_str = _format_time(entry.get("time"))
            name = entry.get("name") or entry.get("url") or "-"
            count = str(entry.get("count", 0))
            ok = entry.get("ok", 0)
            err = entry.get("err", 0)
            status_badge = f"[green]{ok} OK[/green]"
            if err > 0:
                status_badge += f" [red]{err} err[/red]"
            query_url = entry.get("url", "")
            row_key = table.add_row(
                date_str,
                name,
                count,
                status_badge,
                query_url,
            )
            self._row_map[row_key] = entry

        if self._filtered_entries:
            first_entry = self._filtered_entries[0]
            self._selected_entry = first_entry
            self._update_details(first_entry)
        else:
            self.query_one("#history-details-body", Static).update(TR("history.empty"))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        entry = self._row_map.get(event.row_key)
        if entry:
            self._selected_entry = entry
            self._update_details(entry)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        entry = self._row_map.get(event.row_key)
        if entry:
            self._selected_entry = entry
            self.action_redownload()

    def _update_details(self, entry: Dict[str, Any]) -> None:
        name = entry.get("name") or "-"
        date_str = _format_time(entry.get("time"))
        total = entry.get("count", 0)
        ok = entry.get("ok", 0)
        err = entry.get("err", 0)
        skipped = entry.get("skipped", 0)
        query = entry.get("url") or "-"
        log_snippet = entry.get("log_summary", "")

        lines = [
            f"[bold]{TR('history.details_summary', name=name, date=date_str)}[/bold]",
            TR(
                "history.details_tracks",
                total=str(total),
                ok=str(ok),
                err=str(err),
                skipped=str(skipped),
            ),
            TR("history.details_query", query=query),
        ]
        if log_snippet:
            lines.append(f"[dim]{log_snippet}[/dim]")

        self.query_one("#history-details-body", Static).update("\n".join(lines))

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_redownload(self) -> None:
        if not self._selected_entry:
            return
        query_val = self._selected_entry.get("url") or self._selected_entry.get("name")
        operation = self._selected_entry.get("operation", "download")
        if query_val:
            self.app.push_screen(QueryScreen(operation, prefill=query_val))

    def action_copy_url(self) -> None:
        if not self._selected_entry:
            return
        query_val = self._selected_entry.get("url") or self._selected_entry.get("name")
        if not query_val:
            return
        try:
            clipboard_copy(query_val)
            self.query_one("#history-status", Static).update(TR("history.copied"))
        except Exception:
            self.query_one("#history-status", Static).update(TR("history.copy_failed"))

    def action_delete_entry(self) -> None:
        if not self._selected_entry:
            return
        entry_id = self._selected_entry.get("id")
        if entry_id:
            delete_download_entry(entry_id)
            self._reload_data()
            self.query_one("#history-status", Static).update(TR("history.deleted"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if handle_appbar(self, event):
            return
        btn_id = event.button.id
        if btn_id == "history-back-btn":
            self.action_back()
        elif btn_id == "history-redownload-btn":
            self.action_redownload()
        elif btn_id == "history-copy-btn":
            self.action_copy_url()
        elif btn_id == "history-delete-btn":
            self.action_delete_entry()
        elif btn_id == "history-sort-btn":
            self._sort_mode = (self._sort_mode + 1) % 3
            sort_labels = [
                TR("history.btn_sort_date"),
                TR("history.btn_sort_name"),
                TR("history.btn_sort_tracks"),
            ]
            self.query_one("#history-sort-btn", Button).label = sort_labels[
                self._sort_mode
            ]
            self._apply_filter_and_sort()
        elif btn_id == "history-clear-btn":
            clear_history()
            self._reload_data()
            self.query_one("#history-status", Static).update(TR("history.cleared"))

    def refresh_language(self) -> None:
        try:
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
            self.query_one("#history-copy-btn", Button).label = TR(
                "history.btn_copy_url"
            )
            self.query_one("#history-delete-btn", Button).label = TR(
                "history.btn_delete"
            )
            self.query_one("#history-clear-btn", Button).label = TR("history.btn_clear")
            self.query_one("#history-back-btn", Button).label = TR("history.btn_close")

            sort_labels = [
                TR("history.btn_sort_date"),
                TR("history.btn_sort_name"),
                TR("history.btn_sort_tracks"),
            ]
            self.query_one("#history-sort-btn", Button).label = sort_labels[
                self._sort_mode
            ]

            table = self.query_one(DataTable)
            if "time" in table.columns:
                table.columns["time"].label = Text(TR("history.col_time"))
            if "name" in table.columns:
                table.columns["name"].label = Text(TR("history.col_name"))
            if "count" in table.columns:
                table.columns["count"].label = Text(TR("history.col_count"))
            if "status" in table.columns:
                table.columns["status"].label = Text(TR("history.col_status"))
            if "url" in table.columns:
                table.columns["url"].label = Text(TR("history.col_url"))
            table.refresh()

            self.query_one(VersionFooter).refresh_language()
            self._reload_data()
        except Exception:
            pass
