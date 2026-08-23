import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Collapsible, Input, Label, Select, Static, Switch

from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar, VersionFooter, handle_appbar
from spotdl.console.tui.constants import (
    AUDIO_PROVIDERS,
    BITRATES,
    FORMATS,
    LYRICS_PROVIDERS,
)
from spotdl.console.tui.history import add_url_entry
from spotdl.console.tui.screens.download.tracklist import TrackListScreen
from spotdl.console.tui.widgets import DirModal
from spotdl.utils.search import get_simple_songs

if TYPE_CHECKING:
    from spotdl.console.tui.app import SpotdlApp

TR = i18n.tr

logger = logging.getLogger(__name__)

_DETECT_FORMAT_CHOICES = ["mp3", "flac", "m4a", "opus", "ogg", "wav"]

_TEMPLATE_CUSTOM = "custom"
_TEMPLATE_LIGHT = "light"
_TEMPLATE_EFFICIENT = "efficient"
_TEMPLATE_BALANCED = "balanced"
_TEMPLATE_STUDIO = "studio"

TEMPLATES = {
    _TEMPLATE_LIGHT: {
        "format": "opus",
        "bitrate": "96k",
        "threads": "8",
        "dont-filter-results-checkbox": False,
        "only-verified-results-checkbox": False,
        "preload-checkbox": True,
        "generate-lrc-checkbox": False,
    },
    _TEMPLATE_EFFICIENT: {
        "format": "mp3",
        "bitrate": "auto",
        "threads": "8",
        "dont-filter-results-checkbox": False,
        "only-verified-results-checkbox": False,
        "preload-checkbox": True,
        "generate-lrc-checkbox": False,
    },
    _TEMPLATE_BALANCED: {
        "format": "mp3",
        "bitrate": "320k",
        "threads": "4",
        "dont-filter-results-checkbox": False,
        "only-verified-results-checkbox": False,
        "preload-checkbox": False,
        "generate-lrc-checkbox": False,
    },
    _TEMPLATE_STUDIO: {
        "format": "opus",
        "bitrate": "disable",
        "threads": "2",
        "dont-filter-results-checkbox": False,
        "only-verified-results-checkbox": True,
        "preload-checkbox": False,
        "generate-lrc-checkbox": False,
    },
}


_QUERY_LABELS = {
    "lbl-query-url": "query.url_label",
    "lbl-query-dir": "query.dir_label",
    "lbl-query-save-file": "query.save_file_label",
    "lbl-query-template": "query.template",
    "lbl-query-format": "query.format",
    "lbl-query-bitrate": "query.bitrate",
    "lbl-query-audio-provider": "query.audio_provider",
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


class QueryScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    def __init__(self, operation: str, prefill: Optional[str] = None) -> None:
        super().__init__()
        self.operation = operation
        self.prefill = prefill
        self._cached_query: Optional[str] = None
        self._cached_songs: Optional[List[Any]] = None

    def _get_title(self) -> str:
        if self.operation == "save":
            return TR("query.title_save")
        if self.operation == "sync":
            return TR("query.title_sync")
        if self.operation == "download":
            return TR("query.title_download")
        return TR("query.title")

    def compose(self) -> ComposeResult:
        yield AppBar(TR("appbar.title"))
        with Vertical(id="add-download"):
            with VerticalScroll(id="ad-scroll"):
                yield Static(self._get_title(), id="query-title", classes="menu-title")
                yield Label(TR("query.url_label"), id="lbl-query-url")
                yield Input(
                    placeholder=TR("query.url_placeholder"),
                    value=self.prefill or "",
                    id="query-input",
                )
                yield Label(TR("query.dir_label"), id="lbl-query-dir")
                with Horizontal(classes="dir-browse-row"):
                    yield Input(value=str(Path.cwd()), id="dir-input")
                    yield Button("...", id="dir-browse")
                if self.operation in ("save", "sync"):
                    yield Label(TR("query.save_file_label"), id="lbl-query-save-file")
                    yield Input(
                        placeholder=TR("query.ph_save_file"),
                        id="save-file-input",
                    )

                with Collapsible(title=TR("section.audio_format"), collapsed=False):
                    yield Label(TR("query.template"), id="lbl-query-template")
                    yield Select(
                        [
                            (TR("query.template_custom"), _TEMPLATE_CUSTOM),
                            (TR("query.template_light"), _TEMPLATE_LIGHT),
                            (TR("query.template_efficient"), _TEMPLATE_EFFICIENT),
                            (TR("query.template_balanced"), _TEMPLATE_BALANCED),
                            (TR("query.template_studio"), _TEMPLATE_STUDIO),
                        ],
                        value=_TEMPLATE_CUSTOM,
                        allow_blank=False,
                        id="template-select",
                    )
                    yield Label(TR("query.format"), id="lbl-query-format")
                    yield Select(
                        [(f.upper(), f) for f in FORMATS],
                        value="mp3",
                        allow_blank=False,
                        id="format-select",
                    )
                    yield Label(TR("query.bitrate"), id="lbl-query-bitrate")
                    yield Select(
                        [(b, b) for b in BITRATES],
                        value="auto",
                        allow_blank=False,
                        id="bitrate-select",
                    )
                    yield Label(
                        TR("query.audio_provider"), id="lbl-query-audio-provider"
                    )
                    yield Select(
                        [(p, p) for p in AUDIO_PROVIDERS],
                        value="youtube-music",
                        allow_blank=False,
                        id="audio-select",
                    )
                    yield Label(TR("query.threads"), id="lbl-query-threads")
                    yield Input(
                        value="4",
                        placeholder=TR("query.ph_threads"),
                        id="threads-input",
                    )
                    yield Label(TR("query.preload"), id="lbl-query-preload")
                    yield Switch(id="preload-checkbox")

                with Collapsible(title=TR("section.filtering"), collapsed=False):
                    yield Label(TR("query.generate_lrc"), id="lbl-query-generate-lrc")
                    yield Switch(id="generate-lrc-checkbox")
                    yield Label(
                        TR("query.lyrics_provider"), id="lbl-query-lyrics-provider"
                    )
                    yield Select(
                        [(p, p) for p in LYRICS_PROVIDERS],
                        value="genius",
                        allow_blank=False,
                        id="lyrics-select",
                    )
                    yield Label(TR("query.search_query"), id="lbl-query-search-query")
                    yield Input(
                        placeholder=TR("query.ph_lyrics_template"),
                        id="search-query-input",
                    )
                    yield Label(
                        TR("query.force_update_metadata"), id="lbl-query-force-update"
                    )
                    yield Switch(id="force-update-metadata-checkbox")
                    yield Label(
                        TR("query.skip_album_art"), id="lbl-query-skip-album-art"
                    )
                    yield Switch(id="skip-album-art-checkbox")
                    yield Label(TR("query.skip_explicit"), id="lbl-query-skip-explicit")
                    yield Switch(id="skip-explicit-checkbox")
                    yield Label(
                        TR("query.only_verified_results"), id="lbl-query-only-verified"
                    )
                    yield Switch(id="only-verified-results-checkbox")
                    yield Label(
                        TR("query.dont_filter_results"), id="lbl-query-dont-filter"
                    )
                    yield Switch(id="dont-filter-results-checkbox")
                    yield Label(TR("query.album_type"), id="lbl-query-album-type")
                    yield Select(
                        [
                            (TR("query.album_type_album"), "album"),
                            (TR("query.album_type_single"), "single"),
                            (TR("query.album_type_compilation"), "compilation"),
                        ],
                        value="album",
                        allow_blank=True,
                        id="album-type-select",
                    )
                    yield Label(TR("query.ignore_albums"), id="lbl-query-ignore-albums")
                    yield Input(
                        placeholder=TR("query.ph_ignore_albums"),
                        id="ignore-albums-input",
                    )

                with Collapsible(title=TR("section.output_playlist"), collapsed=False):
                    yield Label(
                        TR("query.output_template"), id="lbl-query-output-template"
                    )
                    yield Input(
                        placeholder=TR("query.ph_output_template"),
                        value="{artists} - {title}.{output-ext}",
                        id="output-template-input",
                    )
                    yield Label(TR("query.overwrite"), id="lbl-query-overwrite")
                    yield Select(
                        [
                            (TR("query.overwrite_force"), "force"),
                            (TR("query.overwrite_skip"), "skip"),
                            (TR("query.overwrite_metadata"), "metadata"),
                        ],
                        value="skip",
                        allow_blank=False,
                        id="overwrite-select",
                    )
                    yield Label(TR("query.m3u"), id="lbl-query-m3u")
                    yield Switch(id="m3u-checkbox")
                    yield Input(
                        placeholder=TR("query.ph_m3u"),
                        id="m3u-input",
                        disabled=True,
                    )
                    yield Label(
                        TR("query.playlist_numbering"),
                        id="lbl-query-playlist-numbering",
                    )
                    yield Switch(id="playlist-numbering-checkbox")
                    yield Label(
                        TR("query.playlist_retain_track_cover"),
                        id="lbl-query-retain-cover",
                    )
                    yield Switch(id="playlist-retain-track-cover-checkbox")
                    yield Label(TR("query.fetch_albums"), id="lbl-query-fetch-albums")
                    yield Switch(id="fetch-albums-checkbox")
                    yield Label(TR("query.archive"), id="lbl-query-archive")
                    yield Input(
                        placeholder=TR("query.ph_archive"),
                        id="archive-input",
                    )

                with Collapsible(title=TR("section.network_auth"), collapsed=False):
                    yield Label(TR("query.sponsor_block"), id="lbl-query-sponsor-block")
                    yield Switch(id="sponsor-block-checkbox")
                    yield Label(TR("query.cookie_file"), id="lbl-query-cookie-file")
                    yield Input(
                        placeholder=TR("query.ph_cookie"),
                        id="cookie-file-input",
                    )
                    yield Label(TR("query.proxy"), id="lbl-query-proxy")
                    yield Input(
                        placeholder=TR("query.ph_proxy"),
                        id="proxy-input",
                    )
                    yield Label(TR("query.yt_dlp_args"), id="lbl-query-ytdlp-args")
                    yield Input(
                        placeholder=TR("query.ph_ytdlp_args"),
                        id="yt-dlp-args-input",
                    )
                    yield Label(TR("query.restrict"), id="lbl-query-restrict")
                    yield Select(
                        [
                            (TR("query.restrict_none"), "none"),
                            (TR("query.restrict_ascii"), "ascii"),
                            (TR("query.restrict_strict"), "strict"),
                        ],
                        value="none",
                        allow_blank=False,
                        id="restrict-select",
                    )
                    yield Label(
                        TR("query.max_filename_length"), id="lbl-query-max-filename"
                    )
                    yield Input(
                        placeholder=TR("query.ph_max_filename"),
                        id="max-filename-length-input",
                    )
                    yield Label(TR("query.scan_for_songs"), id="lbl-query-scan-songs")
                    yield Switch(id="scan-for-songs-checkbox")
                    yield Label(
                        TR("query.detect_formats"), id="lbl-query-detect-formats"
                    )
                    yield Select(
                        [(f, f) for f in _DETECT_FORMAT_CHOICES],
                        value="mp3",
                        allow_blank=True,
                        id="detect-formats-select",
                    )
                    yield Label(TR("query.id3_separator"), id="lbl-query-id3-sep")
                    yield Input(
                        value="/",
                        placeholder=TR("query.ph_separator"),
                        id="id3-separator-input",
                    )
                    yield Label(TR("query.ytm_data"), id="lbl-query-ytm-data")
                    yield Switch(id="ytm-data-checkbox")
                    yield Label(
                        TR("query.create_skip_file"), id="lbl-query-create-skip"
                    )
                    yield Switch(id="create-skip-file-checkbox")
                    yield Label(
                        TR("query.respect_skip_file"), id="lbl-query-respect-skip"
                    )
                    yield Switch(id="respect-skip-file-checkbox")

                with Collapsible(title=TR("section.finetuning"), collapsed=False):
                    yield Label(TR("query.log_level"), id="lbl-query-log-level")
                    yield Select(
                        [
                            ("DEBUG", "DEBUG"),
                            ("INFO", "INFO"),
                            ("WARNING", "WARNING"),
                            ("ERROR", "ERROR"),
                        ],
                        value="INFO",
                        allow_blank=False,
                        id="log-level-select",
                    )
                    yield Label(TR("query.print_errors"), id="lbl-query-print-errors")
                    yield Switch(id="print-errors-checkbox")
                    yield Label(TR("query.save_errors"), id="lbl-query-save-errors")
                    yield Input(
                        placeholder=TR("query.ph_errors"),
                        id="save-errors-input",
                    )
                    yield Label(TR("query.log_format"), id="lbl-query-log-format")
                    yield Input(
                        placeholder=TR("query.ph_log_format"),
                        id="log-format-input",
                    )
                    yield Label(TR("query.simple_tui"), id="lbl-query-simple-tui")
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
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if handle_appbar(self, event):
            return
        if event.button.id == "back-btn":
            self.action_back()
        elif event.button.id == "dir-browse":
            try:
                start_path = (
                    Path(self.query_one("#dir-input", Input).value.strip() or ".")
                    .expanduser()
                    .resolve()
                )
                if not start_path.exists():
                    start_path = Path.cwd()
            except Exception:
                start_path = Path.cwd()
            self.app.push_screen(DirModal(start_path), callback=self._dir_chosen)
        elif event.button.id == "search-btn":
            self.start_search()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "m3u-checkbox":
            m3u_input = self.query_one("#m3u-input", Input)
            m3u_input.disabled = not event.switch.value
            if event.switch.value and not m3u_input.value.strip():
                m3u_input.value = "{list[0]}.m3u8"

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "template-select":
            return

        template = TEMPLATES.get(cast(str, event.value))
        if template is None:
            return

        for widget_id, value in template.items():
            if widget_id.endswith("-checkbox"):
                try:
                    self.query_one(f"#{widget_id}", Switch).value = cast(bool, value)
                except Exception:
                    pass
            elif widget_id == "threads":
                try:
                    self.query_one("#threads-input", Input).value = cast(str, value)
                except Exception:
                    pass
            else:
                try:
                    self.query_one(f"#{widget_id}-select", Select).value = cast(
                        str, value
                    )
                except Exception:
                    pass

    def _dir_chosen(self, path: Optional[Path]) -> None:
        if path is not None:
            self.query_one("#dir-input", Input).value = str(path)

    def _collect_options(self) -> Dict[str, Any]:
        query_input = self.query_one("#query-input", Input)
        query = query_input.value.strip()
        if not query:
            self.query_one("#status", Static).update(TR("query.empty_query"))
            return {}

        threads_input = self.query_one("#threads-input", Input)
        try:
            threads = max(1, int(threads_input.value.strip() or "4"))
        except ValueError:
            threads = 4

        save_file: Optional[str] = None
        if self.operation == "save":
            save_value = self.query_one("#save-file-input", Input).value.strip()
            if not save_value.endswith(".spotdl"):
                save_file = None
            else:
                save_file = save_value

        def get_cb(id_: str) -> bool:
            try:
                return self.query_one(f"#{id_}", Switch).value
            except Exception:
                return False

        def get_input(id_: str) -> Optional[str]:
            try:
                val = self.query_one(f"#{id_}", Input).value.strip()
                return val if val else None
            except Exception:
                return None

        def get_select(id_: str) -> Optional[str]:
            try:
                return cast(Optional[str], self.query_one(f"#{id_}", Select).value)
            except Exception:
                return None

        audio_providers = [get_select("audio-select") or "youtube-music"]
        lyrics_providers = [get_select("lyrics-select") or "genius"]
        detect_formats_val = get_select("detect-formats-select")
        detect_formats = [detect_formats_val] if detect_formats_val else None
        restrict_val = get_select("restrict-select")
        restrict = restrict_val if restrict_val and restrict_val != "none" else None
        album_type_val = get_select("album-type-select")
        album_type = album_type_val if album_type_val else None
        log_level_val = get_select("log-level-select")
        log_level = log_level_val if log_level_val else "INFO"

        output_dir = get_input("dir-input") or str(Path.cwd())

        if get_cb("m3u-checkbox"):
            m3u_value = get_input("m3u-input") or "{list[0]}.m3u8"
        else:
            m3u_value = None
        if m3u_value:
            m3u_path = Path(m3u_value)
            if not m3u_path.is_absolute():
                m3u_value = os.path.join(output_dir, m3u_value)

        max_fn_raw = get_input("max-filename-length-input")
        max_filename_length = int(max_fn_raw) if max_fn_raw else None

        return {
            "query": [query],
            "format": get_select("format-select") or "mp3",
            "bitrate": get_select("bitrate-select") or "auto",
            "audio_providers": audio_providers,
            "lyrics_providers": lyrics_providers,
            "threads": threads,
            "output_dir": output_dir,
            "save_file": save_file,
            "output_template": get_input("output-template-input")
            or "{artists} - {title}.{output-ext}",
            "overwrite": get_select("overwrite-select") or "skip",
            "m3u": m3u_value,
            "archive": get_input("archive-input"),
            "preload": get_cb("preload-checkbox"),
            "cookie_file": get_input("cookie-file-input"),
            "sponsor_block": get_cb("sponsor-block-checkbox"),
            "proxy": get_input("proxy-input"),
            "yt_dlp_args": get_input("yt-dlp-args-input"),
            "search_query": get_input("search-query-input"),
            "filter_results": not get_cb("dont-filter-results-checkbox"),
            "only_verified_results": get_cb("only-verified-results-checkbox"),
            "album_type": album_type,
            "scan_for_songs": get_cb("scan-for-songs-checkbox"),
            "detect_formats": detect_formats,
            "restrict": restrict,
            "max_filename_length": max_filename_length,
            "id3_separator": get_input("id3-separator-input") or "/",
            "generate_lrc": get_cb("generate-lrc-checkbox"),
            "add_unavailable": get_cb("add-unavailable-checkbox"),
            "playlist_numbering": get_cb("playlist-numbering-checkbox"),
            "playlist_retain_track_cover": get_cb(
                "playlist-retain-track-cover-checkbox"
            ),
            "fetch_albums": get_cb("fetch-albums-checkbox"),
            "ytm_data": get_cb("ytm-data-checkbox"),
            "force_update_metadata": get_cb("force-update-metadata-checkbox"),
            "skip_album_art": get_cb("skip-album-art-checkbox"),
            "ignore_albums": get_input("ignore-albums-input"),
            "skip_explicit": get_cb("skip-explicit-checkbox"),
            "create_skip_file": get_cb("create-skip-file-checkbox"),
            "respect_skip_file": get_cb("respect-skip-file-checkbox"),
            "print_errors": get_cb("print-errors-checkbox"),
            "save_errors": get_input("save-errors-input"),
            "log_level": log_level,
            "log_format": get_input("log-format-input"),
            "simple_tui": get_cb("simple-tui-checkbox"),
        }

    def start_search(self) -> None:
        options = self._collect_options()
        if not options:
            return

        if self.operation == "save" and not options["save_file"]:
            self.query_one("#status", Static).update(TR("query.save_hint"))
            return

        query_str = options["query"][0]
        use_ytm = options.get("ytm_data", False)
        playlist_num = options.get("playlist_numbering", False)
        cache_key = f"{query_str}::{use_ytm}::{playlist_num}"

        if self._cached_songs is not None and self._cached_query == cache_key:
            self._search_done(self._cached_songs, options)
            return

        self.query_one("#search-btn", Button).disabled = True
        self.query_one("#status", Static).update(TR("query.searching"))
        add_url_entry(query_str, self.operation)

        screen = self

        def run_search() -> None:
            app = cast("SpotdlApp", screen.app)
            try:
                app.state.ensure_spotify(user_auth=False)

                def search_status(msg: str) -> None:
                    app.call_from_thread(screen._update_search_status, msg)

                songs = get_simple_songs(
                    options["query"],
                    use_ytm_data=options.get("ytm_data", False),
                    playlist_numbering=options.get("playlist_numbering", False),
                    status_callback=search_status,
                )
                app.call_from_thread(screen._search_done, songs, options, cache_key)
            except Exception as exc:
                app.call_from_thread(screen._search_failed, exc)

        self.run_worker(run_search, thread=True, exclusive=True, group="search")

    def _update_search_status(self, msg: str) -> None:
        try:
            self.query_one("#status", Static).update(f"{TR('query.searching')}: {msg}")
        except Exception:
            pass

    def _search_done(
        self,
        songs: List[Any],
        options: Dict[str, Any],
        cache_key: Optional[str] = None,
    ) -> None:
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
        self.query_one("#search-btn", Button).disabled = False
        self.query_one("#status", Static).update(TR("query.error", message=str(exc)))

    def refresh_language(self) -> None:
        try:
            appbar = self.query_one(AppBar)
            appbar.set_title(TR("appbar.title"))
        except Exception:
            pass
        try:
            self.query_one("#query-title", Static).update(self._get_title())
            self.query_one("#search-btn", Button).label = TR("query.btn_search")
            self.query_one("#back-btn", Button).label = TR("query.btn_back")
        except Exception:
            pass

        for lbl_id, tr_key in _QUERY_LABELS.items():
            try:
                self.query_one(f"#{lbl_id}", Label).update(TR(tr_key))
            except Exception:
                pass

        for input_id, tr_key in _QUERY_PLACEHOLDERS.items():
            try:
                self.query_one(f"#{input_id}", Input).placeholder = TR(tr_key)
            except Exception:
                pass

        try:
            collapsibles = list(self.query(Collapsible))
            if len(collapsibles) >= 5:
                collapsibles[0].title = TR("section.audio_format")
                collapsibles[1].title = TR("section.filtering")
                collapsibles[2].title = TR("section.output_playlist")
                collapsibles[3].title = TR("section.network_auth")
                collapsibles[4].title = TR("section.finetuning")
        except Exception:
            pass

        try:
            template_select = self.query_one("#template-select", Select)
            curr_tmpl = template_select.value
            template_select.set_options(
                [
                    (TR("query.template_custom"), _TEMPLATE_CUSTOM),
                    (TR("query.template_light"), _TEMPLATE_LIGHT),
                    (TR("query.template_efficient"), _TEMPLATE_EFFICIENT),
                    (TR("query.template_balanced"), _TEMPLATE_BALANCED),
                    (TR("query.template_studio"), _TEMPLATE_STUDIO),
                ]
            )
            template_select.value = curr_tmpl
        except Exception:
            pass

        try:
            overwrite_select = self.query_one("#overwrite-select", Select)
            curr_ow = overwrite_select.value
            overwrite_select.set_options(
                [
                    (TR("query.overwrite_force"), "force"),
                    (TR("query.overwrite_skip"), "skip"),
                    (TR("query.overwrite_metadata"), "metadata"),
                ]
            )
            overwrite_select.value = curr_ow
        except Exception:
            pass

        try:
            album_type_select = self.query_one("#album-type-select", Select)
            curr_at = album_type_select.value
            album_type_select.set_options(
                [
                    (TR("query.album_type_album"), "album"),
                    (TR("query.album_type_single"), "single"),
                    (TR("query.album_type_compilation"), "compilation"),
                ]
            )
            album_type_select.value = curr_at
        except Exception:
            pass

        try:
            restrict_select = self.query_one("#restrict-select", Select)
            curr_res = restrict_select.value
            restrict_select.set_options(
                [
                    (TR("query.restrict_none"), "none"),
                    (TR("query.restrict_ascii"), "ascii"),
                    (TR("query.restrict_strict"), "strict"),
                ]
            )
            restrict_select.value = curr_res
        except Exception:
            pass

        try:
            self.query_one(VersionFooter).refresh_language()
        except Exception:
            pass
