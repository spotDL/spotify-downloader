"""
Settings and presets management screen.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Switch, TabbedContent, TabPane

from spotdl.console.tui import i18n
from spotdl.console.tui.constants import (
    AUDIO_PROVIDERS,
    BITRATES,
    FORMATS,
    LYRICS_PROVIDERS,
)
from spotdl.console.tui.navigation import AppBar, VersionFooter
from spotdl.console.tui.user_presets import (
    delete_custom_preset,
    load_presets,
    reset_presets_to_default,
    save_single_preset,
)
from spotdl.console.tui.user_settings import (
    load_user_settings,
    reset_user_settings,
    save_user_settings,
)
from spotdl.console.tui.widgets import DirModal

TR = i18n.tr

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]


class SettingsScreen(Screen):
    """
    Comprehensive settings screen for all download defaults and presets.
    """

    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._presets = load_presets()
        self._current_preset_name = "balanced"
        self._settings = load_user_settings()

    def compose(self) -> ComposeResult:
        """
        Build the settings tabs and action buttons.
        """
        yield AppBar(TR("settings.title"))
        with TabbedContent(id="settings-tabs"):
            with TabPane(TR("settings.tab_general"), id="tab-general"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label(TR("settings.threads_label"))
                    yield Input(
                        value=str(self._settings.get("threads", 4)),
                        id="set-threads-input",
                    )

                    yield Label(TR("settings.audio_provider_label"))
                    yield Select(
                        [(p, p) for p in AUDIO_PROVIDERS],
                        value=self._settings.get("audio_provider", "youtube-music"),
                        allow_blank=False,
                        id="set-audio-select",
                    )

                    yield Label(TR("settings.fallback_audio_label"))
                    yield Select(
                        [(TR("query.none"), "none")]
                        + [(p, p) for p in AUDIO_PROVIDERS],
                        value=self._settings.get("fallback_audio_provider", "youtube"),
                        allow_blank=False,
                        id="set-fallback-audio-select",
                    )

                    yield Label(TR("settings.format_label"))
                    yield Select(
                        [(f.upper(), f) for f in FORMATS],
                        value=self._settings.get("format", "mp3"),
                        allow_blank=False,
                        id="set-format-select",
                    )

                    yield Label(TR("settings.bitrate_label"))
                    yield Select(
                        [(b, b) for b in BITRATES],
                        value=self._settings.get("bitrate", "128k"),
                        allow_blank=False,
                        id="set-bitrate-select",
                    )

                    yield Label(TR("settings.lyrics_provider_label"))
                    yield Select(
                        [(p, p) for p in LYRICS_PROVIDERS],
                        value=self._settings.get("lyrics_provider", "genius"),
                        allow_blank=False,
                        id="set-lyrics-select",
                    )

                    yield Label(TR("settings.preload_label"))
                    yield Switch(
                        value=bool(self._settings.get("preload", False)),
                        id="set-preload-switch",
                    )

            with TabPane(TR("settings.tab_output"), id="tab-output"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label(TR("settings.output_dir_label"))
                    with Horizontal(classes="dir-browse-row"):
                        yield Input(
                            value=str(self._settings.get("output_dir", "")),
                            id="set-dir-input",
                        )
                        yield Button("...", id="set-dir-browse")

                    yield Label(TR("settings.output_template_label"))
                    yield Input(
                        value=str(
                            self._settings.get(
                                "output_template", "{artists} - {title}.{output-ext}"
                            )
                        ),
                        id="set-template-input",
                    )

                    yield Label(TR("settings.overwrite_label"))
                    yield Select(
                        [
                            (TR("query.overwrite_skip"), "skip"),
                            (TR("query.overwrite_force"), "force"),
                            (TR("query.overwrite_metadata"), "metadata"),
                        ],
                        value=self._settings.get("overwrite", "skip"),
                        allow_blank=False,
                        id="set-overwrite-select",
                    )

                    yield Label(TR("settings.restrict_label"))
                    yield Select(
                        [
                            (TR("query.restrict_none"), "none"),
                            (TR("query.restrict_ascii"), "ascii"),
                            (TR("query.restrict_strict"), "strict"),
                        ],
                        value=self._settings.get("restrict", "none"),
                        allow_blank=False,
                        id="set-restrict-select",
                    )

                    yield Label(TR("settings.m3u_label"))
                    yield Switch(
                        value=bool(self._settings.get("m3u", False)),
                        id="set-m3u-switch",
                    )

                    yield Label(TR("settings.playlist_numbering_label"))
                    yield Switch(
                        value=bool(self._settings.get("playlist_numbering", False)),
                        id="set-numbering-switch",
                    )

                    yield Label(TR("settings.retain_cover_label"))
                    yield Switch(
                        value=bool(
                            self._settings.get("playlist_retain_track_cover", False)
                        ),
                        id="set-retain-cover-switch",
                    )

            with TabPane(TR("settings.tab_filters"), id="tab-filters"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label(TR("settings.sponsor_block_label"))
                    yield Switch(
                        value=bool(self._settings.get("sponsor_block", False)),
                        id="set-sponsor-switch",
                    )

                    yield Label(TR("settings.generate_lrc_label"))
                    yield Switch(
                        value=bool(self._settings.get("generate_lrc", False)),
                        id="set-lrc-switch",
                    )

                    yield Label(TR("settings.verified_only_label"))
                    yield Switch(
                        value=bool(self._settings.get("only_verified_results", False)),
                        id="set-verified-switch",
                    )

                    yield Label(TR("settings.dont_filter_label"))
                    yield Switch(
                        value=bool(self._settings.get("dont_filter_results", False)),
                        id="set-dont-filter-switch",
                    )

                    yield Label(TR("settings.skip_explicit_label"))
                    yield Switch(
                        value=bool(self._settings.get("skip_explicit", False)),
                        id="set-explicit-switch",
                    )

                    yield Label(TR("settings.skip_album_art_label"))
                    yield Switch(
                        value=bool(self._settings.get("skip_album_art", False)),
                        id="set-art-switch",
                    )

                    yield Label(TR("settings.force_update_label"))
                    yield Switch(
                        value=bool(self._settings.get("force_update_metadata", False)),
                        id="set-force-meta-switch",
                    )

                    yield Label(TR("settings.log_level_label"))
                    yield Select(
                        [(lvl, lvl) for lvl in LOG_LEVELS],
                        value=self._settings.get("log_level", "INFO"),
                        allow_blank=False,
                        id="set-log-select",
                    )

            with TabPane(TR("settings.tab_presets"), id="tab-presets"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label(TR("settings.select_preset_label"))
                    yield Select(
                        [(name.capitalize(), name) for name in self._presets],
                        value=self._current_preset_name,
                        allow_blank=False,
                        id="preset-chooser-select",
                    )

                    with Vertical(id="preset-editor-box"):
                        yield Label(TR("settings.preset_format"))
                        yield Select(
                            [(f.upper(), f) for f in FORMATS],
                            value=self._get_preset_val("format", "mp3"),
                            allow_blank=False,
                            id="pe-format-select",
                        )

                        yield Label(TR("settings.preset_bitrate"))
                        yield Select(
                            [(b, b) for b in BITRATES],
                            value=self._get_preset_val("bitrate", "128k"),
                            allow_blank=False,
                            id="pe-bitrate-select",
                        )

                        yield Label(TR("settings.preset_threads"))
                        yield Input(
                            value=str(self._get_preset_val("threads", "4")),
                            id="pe-threads-input",
                        )

                        yield Label(TR("settings.preset_preload"))
                        yield Switch(
                            value=bool(self._get_preset_val("preload", False)),
                            id="pe-preload-switch",
                        )

                        yield Label(TR("settings.preset_verified_only"))
                        yield Switch(
                            value=bool(
                                self._get_preset_val("only_verified_results", False)
                            ),
                            id="pe-verified-switch",
                        )

                        yield Label(TR("settings.preset_dont_filter"))
                        yield Switch(
                            value=bool(
                                self._get_preset_val("dont_filter_results", False)
                            ),
                            id="pe-dont-filter-switch",
                        )

                        yield Label(TR("settings.preset_lrc"))
                        yield Switch(
                            value=bool(self._get_preset_val("generate_lrc", False)),
                            id="pe-lrc-switch",
                        )

                        yield Label(TR("settings.preset_sponsor"))
                        yield Switch(
                            value=bool(self._get_preset_val("sponsor_block", False)),
                            id="pe-sponsor-switch",
                        )

                        with Horizontal(classes="row"):
                            yield Button(
                                TR("settings.btn_save_preset"),
                                id="btn-save-current-preset",
                                variant="primary",
                            )
                            yield Button(
                                TR("settings.btn_delete_preset"),
                                id="btn-delete-current-preset",
                                variant="error",
                            )

                    yield Label(TR("settings.new_preset_label"))
                    with Horizontal(classes="dir-browse-row"):
                        yield Input(
                            placeholder=TR("settings.new_preset_ph"),
                            id="new-preset-name-input",
                        )
                        yield Button(
                            TR("settings.btn_create_preset"),
                            id="btn-create-new-preset",
                        )

                    with Horizontal(classes="row"):
                        yield Button(
                            TR("settings.btn_reset_presets"),
                            id="btn-reset-all-presets",
                        )

        with Horizontal(id="settings-footer-actions"):
            yield Button(
                TR("settings.btn_save_all"),
                id="btn-save-all-settings",
                variant="primary",
            )
            yield Button(TR("settings.btn_reset_defaults"), id="btn-reset-all-settings")
            yield Button(TR("common.back"), id="btn-settings-back")

        yield VersionFooter()

    def _get_preset_val(self, key: str, fallback: Any) -> Any:
        preset = self._presets.get(self._current_preset_name, {})
        return preset.get(key, fallback)

    def on_select_changed(self, event: Select.Changed) -> None:
        """
        Update the preset editor when a preset is chosen.
        """
        if event.select.id == "preset-chooser-select" and event.value:
            self._current_preset_name = str(event.value)
            self._update_preset_editor_values()

    def _update_preset_editor_values(self) -> None:
        preset = self._presets.get(self._current_preset_name, {})
        self.query_one("#pe-format-select", Select).value = preset.get("format", "mp3")
        self.query_one("#pe-bitrate-select", Select).value = preset.get(
            "bitrate", "128k"
        )
        self.query_one("#pe-threads-input", Input).value = str(
            preset.get("threads", "4")
        )
        self.query_one("#pe-preload-switch", Switch).value = bool(
            preset.get("preload", False)
        )
        self.query_one("#pe-verified-switch", Switch).value = bool(
            preset.get("only_verified_results", False)
        )
        self.query_one("#pe-dont-filter-switch", Switch).value = bool(
            preset.get("dont_filter_results", False)
        )
        self.query_one("#pe-lrc-switch", Switch).value = bool(
            preset.get("generate_lrc", False)
        )
        self.query_one("#pe-sponsor-switch", Switch).value = bool(
            preset.get("sponsor_block", False)
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle all settings action button clicks.
        """
        btn_id = event.button.id
        if btn_id == "btn-settings-back":
            self.app.pop_screen()
        elif btn_id == "set-dir-browse":
            typed = self.query_one("#set-dir-input", Input).value.strip() or "."
            start_path = Path(typed).expanduser()
            if not start_path.is_dir():
                start_path = Path.cwd()
            self.app.push_screen(
                DirModal(start_path.resolve()),
                self._apply_chosen_dir,
            )
        elif btn_id == "btn-save-current-preset":
            self._save_active_preset()
        elif btn_id == "btn-delete-current-preset":
            self._delete_active_preset()
        elif btn_id == "btn-create-new-preset":
            self._create_new_preset()
        elif btn_id == "btn-reset-all-presets":
            self._reset_presets()
        elif btn_id == "btn-save-all-settings":
            self._save_all_settings()
        elif btn_id == "btn-reset-all-settings":
            self._reset_all_settings()

    def _apply_chosen_dir(self, result: Any) -> None:
        if result:
            self.query_one("#set-dir-input", Input).value = str(result)

    def _save_active_preset(self) -> None:
        threads_raw = self.query_one("#pe-threads-input", Input).value.strip()
        threads = threads_raw if threads_raw.isdigit() and int(threads_raw) > 0 else "4"

        options = {
            "format": self.query_one("#pe-format-select", Select).value,
            "bitrate": self.query_one("#pe-bitrate-select", Select).value,
            "threads": threads,
            "preload": self.query_one("#pe-preload-switch", Switch).value,
            "only_verified_results": self.query_one(
                "#pe-verified-switch", Switch
            ).value,
            "dont_filter_results": self.query_one(
                "#pe-dont-filter-switch", Switch
            ).value,
            "generate_lrc": self.query_one("#pe-lrc-switch", Switch).value,
            "sponsor_block": self.query_one("#pe-sponsor-switch", Switch).value,
        }
        save_single_preset(self._current_preset_name, options)
        self._presets = load_presets()
        self.notify(
            TR("settings.preset_saved", name=self._current_preset_name),
            title="spotDL",
            severity="information",
        )

    def _delete_active_preset(self) -> None:
        delete_custom_preset(self._current_preset_name)
        self._presets = load_presets()
        self._current_preset_name = "balanced"
        self._refresh_presets_dropdown()
        self._update_preset_editor_values()
        self.notify(
            TR("settings.preset_deleted"),
            title="spotDL",
            severity="warning",
        )

    def _create_new_preset(self) -> None:
        name_input = self.query_one("#new-preset-name-input", Input)
        name = name_input.value.strip().lower().replace(" ", "_")
        if not name:
            self.notify(
                TR("settings.preset_name_empty"),
                title="spotDL",
                severity="error",
            )
            return

        threads_raw = self.query_one("#pe-threads-input", Input).value.strip()
        threads = threads_raw if threads_raw.isdigit() and int(threads_raw) > 0 else "4"

        options = {
            "format": self.query_one("#pe-format-select", Select).value,
            "bitrate": self.query_one("#pe-bitrate-select", Select).value,
            "threads": threads,
            "preload": self.query_one("#pe-preload-switch", Switch).value,
            "only_verified_results": self.query_one(
                "#pe-verified-switch", Switch
            ).value,
            "dont_filter_results": self.query_one(
                "#pe-dont-filter-switch", Switch
            ).value,
            "generate_lrc": self.query_one("#pe-lrc-switch", Switch).value,
            "sponsor_block": self.query_one("#pe-sponsor-switch", Switch).value,
        }
        save_single_preset(name, options)
        name_input.value = ""
        self._presets = load_presets()
        self._current_preset_name = name
        self._refresh_presets_dropdown()
        self._update_preset_editor_values()
        self.notify(
            TR("settings.preset_created", name=name),
            title="spotDL",
            severity="information",
        )

    def _reset_presets(self) -> None:
        reset_presets_to_default()
        self._presets = load_presets()
        self._current_preset_name = "balanced"
        self._refresh_presets_dropdown()
        self._update_preset_editor_values()
        self.notify(
            TR("settings.presets_reset"),
            title="spotDL",
            severity="warning",
        )

    def _refresh_presets_dropdown(self) -> None:
        select = self.query_one("#preset-chooser-select", Select)
        options: List[Tuple[str, str]] = [
            (name.capitalize(), name) for name in self._presets
        ]
        select.set_options(options)
        select.value = self._current_preset_name

    def _save_all_settings(self) -> None:
        threads_raw = self.query_one("#set-threads-input", Input).value.strip()
        threads = (
            threads_raw
            if threads_raw.isdigit() and 1 <= int(threads_raw) <= 32
            else "4"
        )

        settings: Dict[str, Any] = {
            "threads": threads,
            "audio_provider": self.query_one("#set-audio-select", Select).value,
            "fallback_audio_provider": self.query_one(
                "#set-fallback-audio-select", Select
            ).value,
            "format": self.query_one("#set-format-select", Select).value,
            "bitrate": self.query_one("#set-bitrate-select", Select).value,
            "lyrics_provider": self.query_one("#set-lyrics-select", Select).value,
            "preload": self.query_one("#set-preload-switch", Switch).value,
            "output_dir": self.query_one("#set-dir-input", Input).value.strip(),
            "output_template": self.query_one(
                "#set-template-input", Input
            ).value.strip(),
            "overwrite": self.query_one("#set-overwrite-select", Select).value,
            "restrict": self.query_one("#set-restrict-select", Select).value,
            "m3u": self.query_one("#set-m3u-switch", Switch).value,
            "playlist_numbering": self.query_one("#set-numbering-switch", Switch).value,
            "playlist_retain_track_cover": self.query_one(
                "#set-retain-cover-switch", Switch
            ).value,
            "sponsor_block": self.query_one("#set-sponsor-switch", Switch).value,
            "generate_lrc": self.query_one("#set-lrc-switch", Switch).value,
            "only_verified_results": self.query_one(
                "#set-verified-switch", Switch
            ).value,
            "dont_filter_results": self.query_one(
                "#set-dont-filter-switch", Switch
            ).value,
            "skip_explicit": self.query_one("#set-explicit-switch", Switch).value,
            "skip_album_art": self.query_one("#set-art-switch", Switch).value,
            "force_update_metadata": self.query_one(
                "#set-force-meta-switch", Switch
            ).value,
            "log_level": self.query_one("#set-log-select", Select).value,
        }

        save_user_settings(settings)
        self._settings = settings
        self.notify(
            TR("settings.saved_all"),
            title="spotDL",
            severity="information",
        )

    def _reset_all_settings(self) -> None:
        reset_user_settings()
        self._settings = load_user_settings()
        self.notify(
            TR("settings.reset_all"),
            title="spotDL",
            severity="warning",
        )
        self.app.pop_screen()
        self.app.push_screen(SettingsScreen())

    def action_back(self) -> None:
        """
        Pop the settings screen and return to the previous screen.
        """
        self.app.pop_screen()
