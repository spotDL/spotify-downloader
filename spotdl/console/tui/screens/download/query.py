"""
Screen where the user enters a query and picks the download options.
"""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Collapsible, Input, Label, Select, Static, Switch

from spotdl.console.tui import i18n
from spotdl.console.tui.constants import (
    AUDIO_PROVIDERS,
    BITRATES,
    FORMATS,
    LYRICS_PROVIDERS,
)
from spotdl.console.tui.history import add_url_entry
from spotdl.console.tui.navigation import AppBar, VersionFooter
from spotdl.console.tui.screens.download.tracklist import TrackListScreen
from spotdl.console.tui.user_presets import load_presets, save_single_preset
from spotdl.console.tui.user_settings import load_user_settings
from spotdl.console.tui.widgets import DirModal
from spotdl.utils.search import get_simple_songs

if TYPE_CHECKING:
    from spotdl.console.tui.app import SpotdlApp

TR = i18n.tr

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_TEMPLATE = "{artists} - {title}.{output-ext}"
DEFAULT_M3U_NAME = "{list[0]}.m3u8"


def _get_template_select_options() -> List[Tuple[str, str]]:
    options: List[Tuple[str, str]] = [(TR("query.template_custom"), "custom")]
    presets = load_presets()
    for name in presets:
        if name in ("light", "efficient", "balanced", "studio"):
            label = TR(f"query.template_{name}")
        else:
            label = name.capitalize()
        options.append((label, name))
    return options


_TRANSLATED_SELECTS: Dict[str, List[Tuple[str, str]]] = {
    "album-type-select": [
        ("query.album_type_album", "album"),
        ("query.album_type_single", "single"),
        ("query.album_type_compilation", "compilation"),
    ],
    "overwrite-select": [
        ("query.overwrite_force", "force"),
        ("query.overwrite_skip", "skip"),
        ("query.overwrite_metadata", "metadata"),
    ],
    "restrict-select": [
        ("query.restrict_none", "none"),
        ("query.restrict_ascii", "ascii"),
        ("query.restrict_strict", "strict"),
    ],
}

_SECTIONS = {
    "section-audio": "section.audio_format",
    "section-filtering": "section.filtering",
    "section-output": "section.output_playlist",
    "section-network": "section.network_auth",
    "section-finetuning": "section.finetuning",
}

_QUERY_LABELS = {
    "lbl-query-url": "query.url_label",
    "lbl-query-dir": "query.dir_label",
    "lbl-query-save-file": "query.save_file_label",
    "lbl-query-template": "query.template",
    "lbl-query-format": "query.format",
    "lbl-query-bitrate": "query.bitrate",
    "lbl-query-audio-provider": "query.audio_provider",
    "lbl-query-fallback-audio": "query.fallback_audio_provider",
    "lbl-query-threads": "query.threads",
    "lbl-query-preload": "query.preload",
    "lbl-query-generate-lrc": "query.generate_lrc",
    "lbl-query-lyrics-provider": "query.lyrics_provider",
    "lbl-query-search-query": "query.search_query",
    "lbl-query-force-update": "query.force_update_metadata",
    "lbl-query-skip-album-art": "query.skip_album_art",
    "lbl-query-skip-explicit": "query.skip_explicit",
    "lbl-query-only-verified": "query.only_verified_results",
    "lbl-query-dont-filter": "query.dont_filter_results",
    "lbl-query-album-type": "query.album_type",
    "lbl-query-ignore-albums": "query.ignore_albums",
    "lbl-query-output-template": "query.output_template",
    "lbl-query-overwrite": "query.overwrite",
    "lbl-query-m3u": "query.m3u",
    "lbl-query-playlist-folder": "query.playlist_folder",
    "lbl-query-playlist-numbering": "query.playlist_numbering",
    "lbl-query-retain-cover": "query.playlist_retain_track_cover",
    "lbl-query-fetch-albums": "query.fetch_albums",
    "lbl-query-archive": "query.archive",
    "lbl-query-sponsor-block": "query.sponsor_block",
    "lbl-query-cookie-file": "query.cookie_file",
    "lbl-query-proxy": "query.proxy",
    "lbl-query-ytdlp-args": "query.yt_dlp_args",
    "lbl-query-restrict": "query.restrict",
    "lbl-query-max-filename": "query.max_filename_length",
    "lbl-query-scan-songs": "query.scan_for_songs",
    "lbl-query-detect-formats": "query.detect_formats",
    "lbl-query-id3-sep": "query.id3_separator",
    "lbl-query-ytm-data": "query.ytm_data",
    "lbl-query-create-skip": "query.create_skip_file",
    "lbl-query-respect-skip": "query.respect_skip_file",
    "lbl-query-log-level": "query.log_level",
    "lbl-query-print-errors": "query.print_errors",
    "lbl-query-save-errors": "query.save_errors",
    "lbl-query-log-format": "query.log_format",
    "lbl-query-simple-tui": "query.simple_tui",
}

_QUERY_PLACEHOLDERS = {
    "query-input": "query.url_placeholder",
    "save-file-input": "query.ph_save_file",
    "threads-input": "query.ph_threads",
    "search-query-input": "query.ph_lyrics_template",
    "ignore-albums-input": "query.ph_ignore_albums",
    "output-template-input": "query.ph_output_template",
    "m3u-input": "query.ph_m3u",
    "archive-input": "query.ph_archive",
    "cookie-file-input": "query.ph_cookie",
    "proxy-input": "query.ph_proxy",
    "yt-dlp-args-input": "query.ph_ytdlp_args",
    "max-filename-length-input": "query.ph_max_filename",
    "id3-separator-input": "query.ph_separator",
    "save-errors-input": "query.ph_errors",
    "log-format-input": "query.ph_log_format",
}

_SWITCH_OPTIONS = {
    "preload": "preload-checkbox",
    "sponsor_block": "sponsor-block-checkbox",
    "only_verified_results": "only-verified-results-checkbox",
    "scan_for_songs": "scan-for-songs-checkbox",
    "generate_lrc": "generate-lrc-checkbox",
    "playlist_folder": "playlist-folder-checkbox",
    "playlist_numbering": "playlist-numbering-checkbox",
    "playlist_retain_track_cover": "playlist-retain-track-cover-checkbox",
    "fetch_albums": "fetch-albums-checkbox",
    "ytm_data": "ytm-data-checkbox",
    "force_update_metadata": "force-update-metadata-checkbox",
    "skip_album_art": "skip-album-art-checkbox",
    "skip_explicit": "skip-explicit-checkbox",
    "create_skip_file": "create-skip-file-checkbox",
    "respect_skip_file": "respect-skip-file-checkbox",
    "print_errors": "print-errors-checkbox",
    "simple_tui": "simple-tui-checkbox",
}

_INPUT_OPTIONS = {
    "archive": "archive-input",
    "cookie_file": "cookie-file-input",
    "proxy": "proxy-input",
    "yt_dlp_args": "yt-dlp-args-input",
    "search_query": "search-query-input",
    "ignore_albums": "ignore-albums-input",
    "save_errors": "save-errors-input",
    "log_format": "log-format-input",
}


def _translated(options: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    return [(TR(key), value) for key, value in options]


class QueryScreen(Screen):
    """
    Form with the query and every download option, grouped in sections.
    """

    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    def __init__(self, operation: str, prefill: Optional[str] = None) -> None:
        """
        Create the screen.

        ### Arguments
        - operation: "download", "save" or "sync".
        - prefill: Query written in the input when the screen opens.
        """

        super().__init__()
        self.operation = operation
        self.prefill = prefill
        self._cached_query: Optional[str] = None
        self._cached_songs: Optional[List[Any]] = None

    def _get_title(self) -> str:
        titles = {
            "save": "query.title_save",
            "sync": "query.title_sync",
            "download": "query.title_download",
        }
        return TR(titles.get(self.operation, "query.title"))

    def _label(self, widget_id: str) -> Label:
        return Label(TR(_QUERY_LABELS[widget_id]), id=widget_id)

    def _input(self, widget_id: str, value: str = "", **kwargs) -> Input:
        return Input(
            value=value,
            placeholder=TR(_QUERY_PLACEHOLDERS[widget_id]),
            id=widget_id,
            **kwargs,
        )

    def _translated_select(self, widget_id: str, value: str, **kwargs) -> Select:
        return Select(
            _translated(_TRANSLATED_SELECTS[widget_id]),
            value=value,
            id=widget_id,
            **kwargs,
        )

    def _section(self, section_id: str) -> Collapsible:
        return Collapsible(
            title=TR(_SECTIONS[section_id]), collapsed=False, id=section_id
        )

    def compose(self) -> ComposeResult:
        """
        Build the query input and the option sections.
        """

        user_settings = load_user_settings()
        default_dir = user_settings.get("output_dir") or str(Path.cwd())
        default_threads = str(user_settings.get("threads", "4"))
        default_format = user_settings.get("format", "mp3")
        default_bitrate = user_settings.get("bitrate", "auto")
        default_audio = user_settings.get("audio_provider", "youtube-music")
        default_fallback = user_settings.get("fallback_audio_provider", "youtube")
        default_preload = bool(user_settings.get("preload", False))
        default_lrc = bool(user_settings.get("generate_lrc", False))
        default_lyrics = user_settings.get("lyrics_provider", "genius")
        default_force_meta = bool(user_settings.get("force_update_metadata", False))
        default_skip_art = bool(user_settings.get("skip_album_art", False))
        default_skip_explicit = bool(user_settings.get("skip_explicit", False))
        default_verified = bool(user_settings.get("only_verified_results", False))
        default_dont_filter = bool(user_settings.get("dont_filter_results", False))
        default_output_template = user_settings.get(
            "output_template", DEFAULT_OUTPUT_TEMPLATE
        )
        default_overwrite = user_settings.get("overwrite", "skip")
        default_m3u = bool(user_settings.get("m3u", False))
        default_playlist_folder = bool(user_settings.get("playlist_folder", False))
        default_numbering = bool(user_settings.get("playlist_numbering", False))
        default_retain_cover = bool(
            user_settings.get("playlist_retain_track_cover", False)
        )
        default_sponsor = bool(user_settings.get("sponsor_block", False))
        default_restrict = user_settings.get("restrict", "none")
        default_log_level = user_settings.get("log_level", "INFO")

        yield AppBar(TR("appbar.title"))
        with Vertical(id="add-download"):
            with VerticalScroll(id="ad-scroll"):
                yield Static(self._get_title(), id="query-title", classes="menu-title")
                yield self._label("lbl-query-url")
                yield self._input("query-input", value=self.prefill or "")
                yield self._label("lbl-query-dir")
                with Horizontal(classes="dir-browse-row"):
                    yield Input(value=default_dir, id="dir-input")
                    yield Button("...", id="dir-browse")
                if self.operation in ("save", "sync"):
                    yield self._label("lbl-query-save-file")
                    yield self._input("save-file-input")

                with self._section("section-audio"):
                    yield self._label("lbl-query-template")
                    with Horizontal(classes="dir-browse-row"):
                        yield Select(
                            _get_template_select_options(),
                            value="custom",
                            allow_blank=False,
                            id="template-select",
                        )
                        yield Button(
                            TR("query.btn_save_preset"),
                            id="btn-save-query-preset",
                        )
                    yield self._label("lbl-query-format")
                    yield Select(
                        [(f.upper(), f) for f in FORMATS],
                        value=default_format,
                        allow_blank=False,
                        id="format-select",
                    )
                    yield self._label("lbl-query-bitrate")
                    yield Select(
                        [(b, b) for b in BITRATES],
                        value=default_bitrate,
                        allow_blank=False,
                        id="bitrate-select",
                    )
                    yield self._label("lbl-query-audio-provider")
                    yield Select(
                        [(p, p) for p in AUDIO_PROVIDERS],
                        value=default_audio,
                        allow_blank=False,
                        id="audio-select",
                    )
                    yield self._label("lbl-query-fallback-audio")
                    yield Select(
                        [(TR("query.none"), "none")]
                        + [(p, p) for p in AUDIO_PROVIDERS],
                        value=default_fallback,
                        allow_blank=False,
                        id="fallback-audio-select",
                    )
                    yield self._label("lbl-query-threads")
                    yield self._input("threads-input", value=default_threads)
                    yield self._label("lbl-query-preload")
                    yield Switch(value=default_preload, id="preload-checkbox")

                with self._section("section-filtering"):
                    yield self._label("lbl-query-generate-lrc")
                    yield Switch(value=default_lrc, id="generate-lrc-checkbox")
                    yield self._label("lbl-query-lyrics-provider")
                    yield Select(
                        [(p, p) for p in LYRICS_PROVIDERS],
                        value=default_lyrics,
                        allow_blank=False,
                        id="lyrics-select",
                    )
                    yield self._label("lbl-query-search-query")
                    yield self._input("search-query-input")
                    yield self._label("lbl-query-force-update")
                    yield Switch(
                        value=default_force_meta, id="force-update-metadata-checkbox"
                    )
                    yield self._label("lbl-query-skip-album-art")
                    yield Switch(value=default_skip_art, id="skip-album-art-checkbox")
                    yield self._label("lbl-query-skip-explicit")
                    yield Switch(
                        value=default_skip_explicit, id="skip-explicit-checkbox"
                    )
                    yield self._label("lbl-query-only-verified")
                    yield Switch(
                        value=default_verified, id="only-verified-results-checkbox"
                    )
                    yield self._label("lbl-query-dont-filter")
                    yield Switch(
                        value=default_dont_filter, id="dont-filter-results-checkbox"
                    )
                    yield self._label("lbl-query-album-type")
                    yield self._translated_select(
                        "album-type-select", "album", allow_blank=True
                    )
                    yield self._label("lbl-query-ignore-albums")
                    yield self._input("ignore-albums-input")

                with self._section("section-output"):
                    yield self._label("lbl-query-output-template")
                    yield self._input(
                        "output-template-input", value=default_output_template
                    )
                    yield self._label("lbl-query-playlist-folder")
                    yield Switch(
                        value=default_playlist_folder, id="playlist-folder-checkbox"
                    )
                    yield self._label("lbl-query-overwrite")
                    yield self._translated_select(
                        "overwrite-select", default_overwrite, allow_blank=False
                    )
                    yield self._label("lbl-query-m3u")
                    yield Switch(value=default_m3u, id="m3u-checkbox")
                    yield self._input("m3u-input", disabled=not default_m3u)
                    yield self._label("lbl-query-playlist-numbering")
                    yield Switch(
                        value=default_numbering, id="playlist-numbering-checkbox"
                    )
                    yield self._label("lbl-query-retain-cover")
                    yield Switch(
                        value=default_retain_cover,
                        id="playlist-retain-track-cover-checkbox",
                    )
                    yield self._label("lbl-query-fetch-albums")
                    yield Switch(id="fetch-albums-checkbox")
                    yield self._label("lbl-query-archive")
                    yield self._input("archive-input")

                with self._section("section-network"):
                    yield self._label("lbl-query-sponsor-block")
                    yield Switch(value=default_sponsor, id="sponsor-block-checkbox")
                    yield self._label("lbl-query-cookie-file")
                    yield self._input("cookie-file-input")
                    yield self._label("lbl-query-proxy")
                    yield self._input("proxy-input")
                    yield self._label("lbl-query-ytdlp-args")
                    yield self._input("yt-dlp-args-input")
                    yield self._label("lbl-query-restrict")
                    yield self._translated_select(
                        "restrict-select", default_restrict, allow_blank=False
                    )
                    yield self._label("lbl-query-max-filename")
                    yield self._input("max-filename-length-input")
                    yield self._label("lbl-query-scan-songs")
                    yield Switch(id="scan-for-songs-checkbox")
                    yield self._label("lbl-query-detect-formats")
                    yield Select(
                        [(f, f) for f in FORMATS],
                        value="mp3",
                        allow_blank=True,
                        id="detect-formats-select",
                    )
                    yield self._label("lbl-query-id3-sep")
                    yield self._input("id3-separator-input", value="/")
                    yield self._label("lbl-query-ytm-data")
                    yield Switch(id="ytm-data-checkbox")
                    yield self._label("lbl-query-create-skip")
                    yield Switch(id="create-skip-file-checkbox")
                    yield self._label("lbl-query-respect-skip")
                    yield Switch(id="respect-skip-file-checkbox")

                with self._section("section-finetuning"):
                    yield self._label("lbl-query-log-level")
                    yield Select(
                        [
                            (level, level)
                            for level in ("DEBUG", "INFO", "WARNING", "ERROR")
                        ],
                        value=default_log_level,
                        allow_blank=False,
                        id="log-level-select",
                    )
                    yield self._label("lbl-query-print-errors")
                    yield Switch(id="print-errors-checkbox")
                    yield self._label("lbl-query-save-errors")
                    yield self._input("save-errors-input")
                    yield self._label("lbl-query-log-format")
                    yield self._input("log-format-input")
                    yield self._label("lbl-query-simple-tui")
                    yield Switch(id="simple-tui-checkbox")

            with Vertical(id="ad-bottom"):
                yield Static("", id="status")
                with Horizontal(classes="bottom-buttons"):
                    yield Button(TR("query.btn_back"), id="back-btn")
                    yield Button(
                        TR("query.btn_search"),
                        variant="primary",
                        id="search-btn",
                    )

        yield VersionFooter()

    def action_back(self) -> None:
        """
        Go back to the previous screen.
        """

        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Go back, browse for a directory or start the search.
        """

        if event.button.id == "back-btn":
            self.action_back()
        elif event.button.id == "dir-browse":
            typed = self.query_one("#dir-input", Input).value.strip() or "."
            start_path = Path(typed).expanduser()
            if not start_path.is_dir():
                start_path = Path.cwd()
            self.app.push_screen(
                DirModal(start_path.resolve()), callback=self._dir_chosen
            )
        elif event.button.id == "btn-save-query-preset":
            self._save_current_as_preset()
        elif event.button.id == "search-btn":
            self.start_search()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """
        Enable the M3U name input when the M3U switch is turned on.
        """

        if event.switch.id == "m3u-checkbox":
            m3u_input = self.query_one("#m3u-input", Input)
            m3u_input.disabled = not event.switch.value
            if event.switch.value and not m3u_input.value.strip():
                m3u_input.value = DEFAULT_M3U_NAME

    def on_select_changed(self, event: Select.Changed) -> None:
        """
        Apply the chosen preset to the related options.
        """

        if event.select.id != "template-select":
            return

        if event.value == "custom" or event.value is None or event.value is Select.NULL:
            return

        presets = load_presets()
        preset = presets.get(cast(str, event.value))
        if preset is not None:
            self._apply_preset_dict(preset)

    def apply_preset_by_name(self, preset_name: str) -> None:
        """
        Apply a preset by its name to the form controls.
        """

        presets = load_presets()
        preset = presets.get(preset_name)
        if preset is None:
            return

        try:
            template_select = self.query_one("#template-select", Select)
            template_select.value = preset_name
        except Exception:
            pass

        self._apply_preset_dict(preset)

    def _apply_preset_dict(self, preset: Dict[str, Any]) -> None:
        """
        Apply dictionary of preset options to the widgets.
        """

        if "format" in preset:
            self.query_one("#format-select", Select).value = preset["format"]
        if "bitrate" in preset:
            self.query_one("#bitrate-select", Select).value = preset["bitrate"]
        if "threads" in preset:
            self.query_one("#threads-input", Input).value = str(preset["threads"])
        if "preload" in preset:
            self.query_one("#preload-checkbox", Switch).value = bool(preset["preload"])
        if "generate_lrc" in preset:
            self.query_one("#generate-lrc-checkbox", Switch).value = bool(
                preset["generate_lrc"]
            )
        if "sponsor_block" in preset:
            self.query_one("#sponsor-block-checkbox", Switch).value = bool(
                preset["sponsor_block"]
            )
        if "only_verified_results" in preset:
            self.query_one("#only-verified-results-checkbox", Switch).value = bool(
                preset["only_verified_results"]
            )
        if "dont_filter_results" in preset:
            self.query_one("#dont-filter-results-checkbox", Switch).value = bool(
                preset["dont_filter_results"]
            )

        for key, val in preset.items():
            if key.endswith("-checkbox"):
                try:
                    self.query_one(f"#{key}", Switch).value = bool(val)
                except Exception:
                    pass

    def _save_current_as_preset(self) -> None:
        """
        Save the current audio/filtering options as a preset.
        """

        # pylint: disable=import-outside-toplevel
        from spotdl.console.tui.screens.settings import SettingsScreen

        template_val = self.query_one("#template-select", Select).value
        target_name = (
            str(template_val)
            if template_val
            and template_val != "custom"
            and template_val is not Select.NULL
            else None
        )
        if not target_name:
            self.app.push_screen(SettingsScreen())
            return

        opts = {
            "format": self._choice("format-select") or "mp3",
            "bitrate": self._choice("bitrate-select") or "auto",
            "threads": self._text("threads-input") or "4",
            "preload": self._switch("preload-checkbox"),
            "only_verified_results": self._switch("only-verified-results-checkbox"),
            "dont_filter_results": self._switch("dont-filter-results-checkbox"),
            "generate_lrc": self._switch("generate-lrc-checkbox"),
            "sponsor_block": self._switch("sponsor-block-checkbox"),
        }
        save_single_preset(target_name, opts)
        self.notify(
            TR("query.preset_saved", name=target_name),
            title="spotDL",
            severity="information",
        )

    def _dir_chosen(self, path: Optional[Path]) -> None:
        if path is not None:
            self.query_one("#dir-input", Input).value = str(path)

    def _switch(self, widget_id: str) -> bool:
        return bool(self.query_one(f"#{widget_id}", Switch).value)

    def _text(self, widget_id: str) -> Optional[str]:
        return (self.query_one(f"#{widget_id}", Input).value or "").strip() or None

    def _choice(self, widget_id: str) -> Optional[str]:
        value = self.query_one(f"#{widget_id}", Select).value
        if value is None or value is Select.NULL:
            return None
        return cast(str, value)

    def _collect_options(self) -> Dict[str, Any]:
        query = self._text("query-input")
        if not query:
            self.query_one("#status", Static).update(TR("query.empty_query"))
            return {}

        try:
            threads = max(1, min(32, int(self._text("threads-input") or "4")))
        except ValueError:
            threads = 4

        try:
            max_filename_length: Optional[int] = int(
                self._text("max-filename-length-input") or ""
            )
        except ValueError:
            max_filename_length = None

        save_file = None
        if self.operation in ("save", "sync"):
            save_value = self._text("save-file-input") or ""
            save_file = save_value if save_value.endswith(".spotdl") else None

        primary_audio = self._choice("audio-select") or "youtube-music"
        fallback_audio = self._choice("fallback-audio-select")
        audio_providers = [primary_audio]
        if fallback_audio and fallback_audio not in ("none", primary_audio):
            audio_providers.append(fallback_audio)

        detect_format = self._choice("detect-formats-select")
        restrict = self._choice("restrict-select")
        output_dir = self._text("dir-input") or str(Path.cwd())

        m3u_value = None
        if self._switch("m3u-checkbox"):
            m3u_value = self._text("m3u-input") or DEFAULT_M3U_NAME
            if not Path(m3u_value).is_absolute():
                m3u_value = os.path.join(output_dir, m3u_value)

        options: Dict[str, Any] = {
            "query": [query],
            "format": self._choice("format-select") or "mp3",
            "bitrate": self._choice("bitrate-select") or "auto",
            "audio_providers": audio_providers,
            "lyrics_providers": [self._choice("lyrics-select") or "genius"],
            "threads": threads,
            "output_dir": output_dir,
            "save_file": save_file,
            "output_template": self._text("output-template-input")
            or DEFAULT_OUTPUT_TEMPLATE,
            "overwrite": self._choice("overwrite-select") or "skip",
            "m3u": m3u_value,
            "filter_results": not self._switch("dont-filter-results-checkbox"),
            "album_type": self._choice("album-type-select"),
            "detect_formats": [detect_format] if detect_format else None,
            "restrict": restrict if restrict != "none" else None,
            "max_filename_length": max_filename_length,
            "id3_separator": self._text("id3-separator-input") or "/",
            "log_level": self._choice("log-level-select") or "INFO",
        }
        for option, widget_id in _SWITCH_OPTIONS.items():
            options[option] = self._switch(widget_id)
        for option, widget_id in _INPUT_OPTIONS.items():
            options[option] = self._text(widget_id)
        return options

    def start_search(self) -> None:
        """
        Search the songs for the query, reusing the last result when the
        query and the options that change the result are the same.
        """

        options = self._collect_options()
        if not options:
            return

        needs_save_file = self.operation == "save" or (
            self.operation == "sync" and not options["query"][0].endswith(".spotdl")
        )
        if needs_save_file and not options["save_file"]:
            self.query_one("#status", Static).update(TR("query.save_hint"))
            return

        query_str = options["query"][0]
        cache_key = (
            f"{query_str}::{options['ytm_data']}::{options['playlist_numbering']}"
        )

        if self._cached_songs is not None and self._cached_query == cache_key:
            self._search_done(self._cached_songs, options)
            return

        self.query_one("#search-btn", Button).disabled = True
        self.query_one("#status", Static).update(TR("query.searching"))
        add_url_entry(query_str, self.operation)
        self._search_in_thread(options, cache_key)

    @work(thread=True, exclusive=True, group="search")
    def _search_in_thread(self, options: Dict[str, Any], cache_key: str) -> None:
        app = cast("SpotdlApp", self.app)
        try:
            app.state.ensure_spotify(user_auth=False)
            songs = get_simple_songs(
                options["query"],
                use_ytm_data=options["ytm_data"],
                playlist_numbering=options["playlist_numbering"],
                status_callback=lambda message: app.call_from_thread(
                    self._update_search_status, message
                ),
            )
        except Exception as exc:
            app.call_from_thread(self._search_failed, exc)
            return
        app.call_from_thread(self._search_done, songs, options, cache_key)

    def _update_search_status(self, message: str) -> None:
        if self.is_attached:
            self.query_one("#status", Static).update(
                f"{TR('query.searching')}: {message}"
            )

    def _search_done(
        self,
        songs: List[Any],
        options: Dict[str, Any],
        cache_key: Optional[str] = None,
    ) -> None:
        if not self.is_attached:
            return
        self.query_one("#search-btn", Button).disabled = False
        if not songs:
            self.query_one("#status", Static).update(TR("query.no_results"))
            return
        if cache_key:
            self._cached_query = cache_key
            self._cached_songs = songs
        self.query_one("#status", Static).update(
            TR("query.found", count=str(len(songs)))
        )
        self.app.push_screen(TrackListScreen(self.operation, songs, options))

    def _search_failed(self, exc: Exception) -> None:
        logger.error(TR("query.search_failed"), exc_info=exc)
        if not self.is_attached:
            return
        self.query_one("#search-btn", Button).disabled = False
        self.query_one("#status", Static).update(TR("query.error", message=str(exc)))

    def refresh_language(self) -> None:
        """
        Translate the screen to the current language, keeping the chosen values.
        """

        self.query_one(AppBar).set_title(TR("appbar.title"))
        self.query_one("#query-title", Static).update(self._get_title())
        self.query_one("#search-btn", Button).label = TR("query.btn_search")
        self.query_one("#back-btn", Button).label = TR("query.btn_back")
        self.query_one("#btn-save-query-preset", Button).label = TR(
            "query.btn_save_preset"
        )

        template_select = self.query_one("#template-select", Select)
        curr_template = template_select.value
        template_select.set_options(_get_template_select_options())
        template_select.value = curr_template

        for label in self.query(Label):
            if label.id in _QUERY_LABELS:
                label.update(TR(_QUERY_LABELS[label.id]))
        for text_input in self.query(Input):
            if text_input.id in _QUERY_PLACEHOLDERS:
                text_input.placeholder = TR(_QUERY_PLACEHOLDERS[text_input.id])
        for section_id, key in _SECTIONS.items():
            self.query_one(f"#{section_id}", Collapsible).title = TR(key)

        for widget_id, options in _TRANSLATED_SELECTS.items():
            select = self.query_one(f"#{widget_id}", Select)
            current = select.value
            select.set_options(_translated(options))
            select.value = current

        self.query_one(VersionFooter).refresh_language()
