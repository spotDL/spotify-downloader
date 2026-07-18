"""
Main application window for the spotDL GUI.
"""

import logging
from typing import Any, Callable, Dict, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# pylint: disable=wrong-import-position
from gi.repository import Adw, Gio, GLib, GObject, Gtk, Pango  # noqa: E402

from spotdl.gui import history  # noqa: E402
from spotdl.gui.backend import (  # noqa: E402
    EVENT_ERROR,
    EVENT_JOB_DONE,
    EVENT_PROGRESS,
    EVENT_SEARCH_DONE,
    EVENT_SONG_DONE,
    EVENT_STATUS,
    DownloadManager,
)
from spotdl.gui.settings import build_downloader_settings, load_settings  # noqa: E402

logger = logging.getLogger(__name__)

__all__ = ["SpotdlWindow", "SongRow", "HistoryRow"]


def _open_location(parent: Gtk.Widget, path: str, containing: bool = True) -> None:
    """Open a file's containing folder (or a folder directly) via the portal."""

    launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(path))
    if containing:
        launcher.open_containing_folder(parent.get_root(), None, None)
    else:
        launcher.launch(parent.get_root(), None, None)


class SongRow(Gtk.ListBoxRow):
    """A single download row: title, status, progress bar, retry on failure."""

    def __init__(self, name: str, url: str, on_retry: Callable[[str], None]) -> None:
        super().__init__()
        self.set_selectable(False)
        self.set_activatable(False)

        self.url = url
        self._on_retry = on_retry
        self.path: Optional[str] = None

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(12)
        box.set_margin_end(12)
        self.set_child(box)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.title = Gtk.Label(label=name, xalign=0, hexpand=True)
        self.title.set_ellipsize(Pango.EllipsizeMode.END)
        header.append(self.title)

        self.status = Gtk.Label(xalign=1)
        self.status.add_css_class("dim-label")
        self.status.add_css_class("caption")
        header.append(self.status)

        self.retry_button = Gtk.Button()
        self.retry_button.set_icon_name("view-refresh-symbolic")
        self.retry_button.set_tooltip_text("Retry download")
        self.retry_button.add_css_class("flat")
        self.retry_button.set_valign(Gtk.Align.CENTER)
        self.retry_button.set_visible(False)
        self.retry_button.connect("clicked", self._on_retry_clicked)
        header.append(self.retry_button)

        box.append(header)

        self.progress = Gtk.ProgressBar()
        self.progress.set_fraction(0.0)
        box.append(self.progress)

        # Hidden until a failure gives us a reason to show.
        self.error_label = Gtk.Label(xalign=0)
        self.error_label.add_css_class("caption")
        self.error_label.add_css_class("error")
        self.error_label.set_wrap(True)
        self.error_label.set_visible(False)
        box.append(self.error_label)

    def _on_retry_clicked(self, _button: Gtk.Button) -> None:
        self._on_retry(self.url)

    def update(self, progress: int, message: str) -> None:
        """Update progress fraction and status text for an in-flight song."""

        self.retry_button.set_visible(False)
        self.error_label.set_visible(False)
        self.status.remove_css_class("error")
        self.progress.set_fraction(max(0.0, min(1.0, progress / 100.0)))
        self.status.set_text(message)

    def set_done(self, path: Optional[str]) -> None:
        """Mark the row as finished successfully."""

        self.path = path
        self.retry_button.set_visible(False)
        self.error_label.set_visible(False)
        self.status.remove_css_class("error")
        self.progress.set_fraction(1.0)
        self.status.set_text("Done")

    def set_failed(self, reason: Optional[str]) -> None:
        """Mark the row as failed and show a reason + retry button."""

        self.status.set_text("Failed")
        self.status.add_css_class("error")
        self.retry_button.set_visible(True)
        if reason:
            self.error_label.set_text(reason)
            self.error_label.set_visible(True)
            self.set_tooltip_text(reason)

    def set_retrying(self) -> None:
        """Reset the row to a pending state before a retry."""

        self.update(0, "Retrying\u2026")


class HistoryRow(Adw.ActionRow):
    """A history sidebar entry that remembers the downloaded file path."""

    def __init__(self, entry: Dict[str, Any]) -> None:
        super().__init__()
        self.path: Optional[str] = entry.get("path")
        self.set_title(GLib.markup_escape_text(entry.get("name", "Unknown")))
        subtitle = entry.get("artist") or entry.get("album") or ""
        if subtitle:
            self.set_subtitle(GLib.markup_escape_text(subtitle))
        if self.path:
            self.set_activatable(True)
            self.add_suffix(Gtk.Image.new_from_icon_name("folder-symbolic"))


class SpotdlWindow(Adw.ApplicationWindow):
    """The primary spotDL window."""

    # Widgets are created in _build_ui() helpers invoked from __init__.
    # pylint: disable=attribute-defined-outside-init

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.set_title("spotDL")
        self.set_default_size(900, 720)

        self.manager = DownloadManager()
        self.settings: Dict[str, Any] = load_settings()
        self._rows: Dict[str, SongRow] = {}
        self._output_dir: Optional[str] = None
        self._busy = False
        self._suppress_loading = False

        self._install_actions()
        self._build_ui()
        self._load_history()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        self.split_view = Adw.OverlaySplitView()
        self.split_view.set_max_sidebar_width(320)
        self.split_view.set_show_sidebar(False)
        self.toast_overlay.set_child(self.split_view)

        self.split_view.set_sidebar(self._build_sidebar())
        self.split_view.set_content(self._build_content())

    def _build_sidebar(self) -> Gtk.Widget:
        toolbar = Adw.ToolbarView()

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        title = Adw.WindowTitle.new("History", "")
        header.set_title_widget(title)

        clear_history_button = Gtk.Button()
        clear_history_button.set_icon_name("user-trash-symbolic")
        clear_history_button.set_tooltip_text("Clear history")
        clear_history_button.connect("clicked", self._on_clear_history)
        header.pack_end(clear_history_button)
        toolbar.add_top_bar(header)

        self.history_stack = Gtk.Stack()

        empty = Adw.StatusPage()
        empty.set_icon_name("document-open-recent-symbolic")
        empty.set_title("No downloads yet")
        empty.add_css_class("compact")
        self.history_stack.add_named(empty, "empty")

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        self.history_listbox = Gtk.ListBox()
        self.history_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.history_listbox.add_css_class("navigation-sidebar")
        self.history_listbox.connect("row-activated", self._on_history_activated)
        scroller.set_child(self.history_listbox)
        self.history_stack.add_named(scroller, "list")

        toolbar.set_content(self.history_stack)
        return toolbar

    def _build_content(self) -> Gtk.Widget:
        toolbar_view = Adw.ToolbarView()

        header = Adw.HeaderBar()

        self.sidebar_toggle = Gtk.ToggleButton()
        self.sidebar_toggle.set_icon_name("sidebar-show-symbolic")
        self.sidebar_toggle.set_tooltip_text("Toggle history sidebar")
        self.sidebar_toggle.bind_property(
            "active",
            self.split_view,
            "show-sidebar",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )
        header.pack_start(self.sidebar_toggle)

        self.clear_button = Gtk.Button(label="Clear")
        self.clear_button.set_tooltip_text("Clear results and start over")
        self.clear_button.connect("clicked", lambda *_: self._reset_to_home())
        self.clear_button.set_visible(False)
        header.pack_start(self.clear_button)

        menu = Gio.Menu()
        menu.append("Preferences", "app.preferences")
        menu.append("About spotDL", "app.about")
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(menu)
        menu_button.set_tooltip_text("Main Menu")
        header.pack_end(menu_button)

        toolbar_view.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        toolbar_view.set_content(content)

        search_clamp = Adw.Clamp(maximum_size=820)
        search_clamp.set_margin_top(18)
        search_clamp.set_margin_bottom(6)
        search_clamp.set_margin_start(12)
        search_clamp.set_margin_end(12)
        content.append(search_clamp)

        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_clamp.set_child(search_box)

        self.entry = Gtk.Entry(hexpand=True)
        self.entry.set_placeholder_text(
            "Paste a Spotify link, or search for a song\u2026"
        )
        self.entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.PRIMARY, "system-search-symbolic"
        )
        self.entry.connect("activate", self._on_download_clicked)
        search_box.append(self.entry)

        self.download_button = Gtk.Button(label="Download")
        self.download_button.add_css_class("suggested-action")
        self.download_button.connect("clicked", self._on_download_clicked)
        search_box.append(self.download_button)

        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        content.append(self.stack)

        self.stack.add_named(self._build_empty_state(), "empty")
        self.stack.add_named(self._build_loading_state(), "loading")
        self.stack.add_named(self._build_list_state(), "list")
        self.stack.set_visible_child_name("empty")

        return toolbar_view

    def _build_empty_state(self) -> Gtk.Widget:
        status_page = Adw.StatusPage()
        status_page.set_icon_name("folder-music-symbolic")
        status_page.set_title("Download music from Spotify")
        status_page.set_description(
            "Paste a Spotify track, album, or playlist link \u2014 "
            "or search by name \u2014 then press Download."
        )
        return status_page

    def _build_loading_state(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        box.set_vexpand(True)

        if hasattr(Adw, "Spinner"):
            spinner: Gtk.Widget = Adw.Spinner()
            spinner.set_size_request(48, 48)
        else:  # pragma: no cover - fallback for older libadwaita
            spinner = Gtk.Spinner()
            spinner.set_size_request(48, 48)
            spinner.start()
        box.append(spinner)

        self.loading_label = Gtk.Label(label="Starting\u2026")
        self.loading_label.add_css_class("title-2")
        box.append(self.loading_label)

        self.loading_sublabel = Gtk.Label(
            label="This can take a moment on the first download."
        )
        self.loading_sublabel.add_css_class("dim-label")
        box.append(self.loading_sublabel)

        return box

    def _build_list_state(self) -> Gtk.Widget:
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)

        list_clamp = Adw.Clamp(maximum_size=820)
        list_clamp.set_margin_top(6)
        list_clamp.set_margin_bottom(18)
        list_clamp.set_margin_start(12)
        list_clamp.set_margin_end(12)
        scroller.set_child(list_clamp)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.add_css_class("boxed-list")
        self.listbox.set_valign(Gtk.Align.START)
        list_clamp.set_child(self.listbox)

        return scroller

    def _install_actions(self) -> None:
        open_folder = Gio.SimpleAction.new("open-folder", None)
        open_folder.connect("activate", self._on_open_folder)
        self.add_action(open_folder)

    # ------------------------------------------------------------- handlers

    def _on_download_clicked(self, *_args: Any) -> None:
        if self._busy:
            return

        text = self.entry.get_text().strip()
        if not text:
            return

        self.entry.set_text("")
        self._clear_rows()
        self._suppress_loading = False
        self.loading_label.set_text("Starting\u2026")
        self.stack.set_visible_child_name("loading")
        self.clear_button.set_visible(True)
        self._set_busy(True)

        settings = build_downloader_settings(self.settings)
        self.manager.submit(
            [text], settings, self._emit_event, self.settings.get("fallback", True)
        )

    def _on_retry_song(self, url: str) -> None:
        if self._busy:
            return

        row = self._rows.get(url)
        if row is not None:
            row.set_retrying()

        # Keep the list visible during a retry instead of the loading screen.
        self._suppress_loading = True
        self._set_busy(True)

        settings = build_downloader_settings(self.settings)
        self.manager.submit(
            [url], settings, self._emit_event, self.settings.get("fallback", True)
        )

    def _on_open_folder(self, *_args: Any) -> None:
        if self._output_dir:
            _open_location(self, self._output_dir, containing=False)

    def _reset_to_home(self) -> None:
        self._clear_rows()
        self.clear_button.set_visible(False)
        self.stack.set_visible_child_name("empty")

    # -------------------------------------------------------------- history

    def _load_history(self) -> None:
        # Stored newest-first, so appending preserves order.
        for entry in history.load_history():
            self.history_listbox.append(HistoryRow(entry))
        self._update_history_stack()

    def _on_history_activated(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        path = getattr(row, "path", None)
        if path:
            _open_location(self, path, containing=True)

    def _on_clear_history(self, _button: Gtk.Button) -> None:
        history.clear_history()
        child = self.history_listbox.get_first_child()
        while child is not None:
            self.history_listbox.remove(child)
            child = self.history_listbox.get_first_child()
        self._update_history_stack()

    def _update_history_stack(self) -> None:
        has_items = self.history_listbox.get_first_child() is not None
        self.history_stack.set_visible_child_name("list" if has_items else "empty")

    # -------------------------------------------------------------- events

    def _emit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Called from the worker thread; hop onto the GTK main loop."""

        GLib.idle_add(self._handle_event, event_type, payload)

    def _handle_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        if event_type == EVENT_STATUS:
            if not self._suppress_loading:
                self.stack.set_visible_child_name("loading")
                self.loading_label.set_text(payload["message"])
        elif event_type == EVENT_SEARCH_DONE:
            for song in payload["songs"]:
                self._ensure_row(song["url"], song["name"])
            self.stack.set_visible_child_name("list")
        elif event_type == EVENT_PROGRESS:
            row = self._ensure_row(payload["url"], payload["name"])
            self.stack.set_visible_child_name("list")
            row.update(payload["progress"], payload["message"])
        elif event_type == EVENT_SONG_DONE:
            self._handle_song_done(payload)
        elif event_type == EVENT_JOB_DONE:
            self._handle_job_done(payload)
        elif event_type == EVENT_ERROR:
            self._set_busy(False)
            self.toast_overlay.add_toast(Adw.Toast.new(payload["message"]))
            if not self._rows:
                self._reset_to_home()

        # Returning False removes this one-shot idle source.
        return False

    def _handle_song_done(self, payload: Dict[str, Any]) -> None:
        row = self._rows.get(payload["url"])
        if row is None:
            return

        if payload["path"]:
            row.set_done(payload["path"])
            entry = history.add_entry(
                name=payload.get("name", "Unknown"),
                path=payload["path"],
                artist=payload.get("artist", ""),
                album=payload.get("album", ""),
            )
            self.history_listbox.prepend(HistoryRow(entry))
            self._update_history_stack()
        else:
            row.set_failed(payload.get("error"))

    def _handle_job_done(self, payload: Dict[str, Any]) -> None:
        self._set_busy(False)
        self._suppress_loading = False
        self._output_dir = payload["output_dir"]
        downloaded = payload["downloaded"]
        total = payload["total"]

        if downloaded:
            toast = Adw.Toast.new(f"Downloaded {downloaded} of {total} songs")
            toast.set_button_label("Open Folder")
            toast.set_action_name("win.open-folder")
            toast.set_timeout(6)
        else:
            toast = Adw.Toast.new("No songs were downloaded")
        self.toast_overlay.add_toast(toast)

    # -------------------------------------------------------------- helpers

    def _ensure_row(self, url: str, name: str) -> SongRow:
        row = self._rows.get(url)
        if row is None:
            row = SongRow(name, url, self._on_retry_song)
            self._rows[url] = row
            self.listbox.append(row)
        return row

    def _clear_rows(self) -> None:
        for row in self._rows.values():
            self.listbox.remove(row)
        self._rows.clear()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.download_button.set_sensitive(not busy)
        self.entry.set_sensitive(not busy)
