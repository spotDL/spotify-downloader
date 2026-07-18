"""
Preferences dialog for the spotDL GUI.

Changes are persisted immediately to the shared spotDL config file and mirrored
onto the owning window's ``settings`` dict so the next download picks them up.
"""

import logging
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# pylint: disable=wrong-import-position
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from spotdl.gui.settings import (  # noqa: E402
    BITRATES,
    FOLDER_STRUCTURE_LABELS,
    FORMATS,
    save_settings,
)

logger = logging.getLogger(__name__)

__all__ = ["SpotdlPreferences"]


class SpotdlPreferences(Adw.PreferencesDialog):
    """Preferences dialog covering the core download options."""

    def __init__(self, window: Any) -> None:
        super().__init__()
        self.set_title("Preferences")

        self.window = window
        self.values = dict(window.settings)

        page = Adw.PreferencesPage()
        page.set_icon_name("emblem-downloads-symbolic")
        page.set_title("Downloads")
        self.add(page)

        group = Adw.PreferencesGroup()
        group.set_title("Downloads")
        group.set_description("These settings are shared with the spotDL command line.")
        page.add(group)

        # Output folder.
        self.folder_row = Adw.ActionRow()
        self.folder_row.set_title("Output folder")
        self.folder_row.set_subtitle(self.values["output_dir"])
        choose = Gtk.Button(label="Choose\u2026")
        choose.set_valign(Gtk.Align.CENTER)
        choose.connect("clicked", self._on_choose_folder)
        self.folder_row.add_suffix(choose)
        self.folder_row.set_activatable_widget(choose)
        group.add(self.folder_row)

        # Folder structure (how downloads are grouped into subfolders).
        self._structure_keys = [key for key, _ in FOLDER_STRUCTURE_LABELS]
        self.structure_row = Adw.ComboRow()
        self.structure_row.set_title("Organize into folders")
        self.structure_row.set_subtitle("How downloads are grouped on disk")
        self.structure_row.set_model(
            Gtk.StringList.new([label for _, label in FOLDER_STRUCTURE_LABELS])
        )
        current_structure = self.values.get("folder_structure", self._structure_keys[0])
        self.structure_row.set_selected(
            self._structure_keys.index(current_structure)
            if current_structure in self._structure_keys
            else 0
        )
        self.structure_row.connect("notify::selected", self._on_structure)
        group.add(self.structure_row)

        # Output format.
        self.format_row = Adw.ComboRow()
        self.format_row.set_title("Format")
        self.format_row.set_model(Gtk.StringList.new(FORMATS))
        self.format_row.set_selected(
            FORMATS.index(self.values["format"])
            if self.values["format"] in FORMATS
            else 0
        )
        self.format_row.connect("notify::selected", self._on_format)
        group.add(self.format_row)

        # Bitrate.
        self.bitrate_row = Adw.ComboRow()
        self.bitrate_row.set_title("Bitrate")
        self.bitrate_row.set_model(Gtk.StringList.new(BITRATES))
        self.bitrate_row.set_selected(
            BITRATES.index(self.values["bitrate"])
            if self.values["bitrate"] in BITRATES
            else 0
        )
        self.bitrate_row.connect("notify::selected", self._on_bitrate)
        group.add(self.bitrate_row)

        # Threads.
        self.threads_row = Adw.SpinRow.new_with_range(1, 16, 1)
        self.threads_row.set_title("Download threads")
        self.threads_row.set_value(self.values["threads"])
        self.threads_row.connect("notify::value", self._on_threads)
        group.add(self.threads_row)

        # Lyrics.
        self.lrc_row = Adw.SwitchRow()
        self.lrc_row.set_title("Download synced lyrics")
        self.lrc_row.set_subtitle("Save a matching .lrc file next to each song")
        self.lrc_row.set_active(self.values["generate_lrc"])
        self.lrc_row.connect("notify::active", self._on_lrc)
        group.add(self.lrc_row)

        # Fallback sources.
        self.fallback_row = Adw.SwitchRow()
        self.fallback_row.set_title("Try other sources on failure")
        self.fallback_row.set_subtitle(
            "If a song fails, retry it from YouTube, SoundCloud, then Bandcamp"
        )
        self.fallback_row.set_active(self.values.get("fallback", True))
        self.fallback_row.connect("notify::active", self._on_fallback)
        group.add(self.fallback_row)

    # ------------------------------------------------------------- handlers

    def _on_choose_folder(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Select output folder")
        try:
            dialog.set_initial_folder(Gio.File.new_for_path(self.values["output_dir"]))
        except GLib.Error:
            pass
        dialog.select_folder(self.window, None, self._on_folder_selected)

    def _on_folder_selected(
        self, dialog: Gtk.FileDialog, result: Gio.AsyncResult
    ) -> None:
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return

        if folder is None:
            return

        path = folder.get_path()
        if not path:
            return

        self.values["output_dir"] = path
        self.folder_row.set_subtitle(path)
        self._persist()

    def _on_structure(self, row: Adw.ComboRow, _param: Any) -> None:
        self.values["folder_structure"] = self._structure_keys[row.get_selected()]
        self._persist()

    def _on_format(self, row: Adw.ComboRow, _param: Any) -> None:
        self.values["format"] = FORMATS[row.get_selected()]
        self._persist()

    def _on_bitrate(self, row: Adw.ComboRow, _param: Any) -> None:
        self.values["bitrate"] = BITRATES[row.get_selected()]
        self._persist()

    def _on_threads(self, row: Adw.SpinRow, _param: Any) -> None:
        self.values["threads"] = int(row.get_value())
        self._persist()

    def _on_lrc(self, row: Adw.SwitchRow, _param: Any) -> None:
        self.values["generate_lrc"] = row.get_active()
        self._persist()

    def _on_fallback(self, row: Adw.SwitchRow, _param: Any) -> None:
        self.values["fallback"] = row.get_active()
        self._persist()

    def _persist(self) -> None:
        save_settings(self.values)
        self.window.settings = dict(self.values)
