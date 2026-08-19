import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Collapsible,
    Input,
    Label,
    OptionList,
    RichLog,
    Select,
    Static,
    Switch,
)

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


class QueryScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    def __init__(self, operation: str, prefill: Optional[str] = None) -> None:
        super().__init__()
        self.operation = operation
        self.prefill = prefill

    def compose(self) -> ComposeResult:
        yield AppBar(TR("appbar.title"))
        with Vertical(id="add-download"):
            with VerticalScroll(id="ad-scroll"):
                yield Static(TR("query.title"), classes="menu-title")
                yield Label(TR("query.url_label"))
                yield Input(
                    placeholder=TR("query.url_placeholder"),
                    value=self.prefill or "",
                    id="query-input",
                )
                if self.operation == "save":
                    yield Label(TR("query.save_file_label"))
                    yield Input(
                        placeholder=TR("query.ph_save_file"),
                        id="save-file-input",
                    )

                with Collapsible(title=TR("section.audio_format"), collapsed=False):
                    yield Label(TR("query.template"))
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
                    yield Label(TR("query.format"))
                    yield Select(
                        [(f.upper(), f) for f in FORMATS],
                        value="mp3",
                        allow_blank=False,
                        id="format-select",
                    )
                    yield Label(TR("query.bitrate"))
                    yield Select(
                        [(b, b) for b in BITRATES],
                        value="auto",
                        allow_blank=False,
                        id="bitrate-select",
                    )
                    yield Label(TR("query.audio_provider"))
                    yield Select(
                        [(p, p) for p in AUDIO_PROVIDERS],
                        value="youtube-music",
                        allow_blank=False,
                        id="audio-select",
                    )
                    yield Label(TR("query.lyrics_provider"))
                    yield Select(
                        [(p, p) for p in LYRICS_PROVIDERS],
                        value="genius",
                        allow_blank=False,
                        id="lyrics-select",
                    )
                    yield Label(TR("query.threads"))
                    yield Input(
                        value="4",
                        placeholder=TR("query.ph_threads"),
                        id="threads-input",
                    )
                    yield Label(TR("query.generate_lrc"))
                    yield Switch(id="generate-lrc-checkbox")
                    yield Label(TR("query.search_query"))
                    yield Input(
                        placeholder=TR("query.ph_lyrics_template"),
                        id="search-query-input",
                    )

                with Collapsible(title=TR("section.output_playlist"), collapsed=False):
                    yield Label(TR("query.dir_label"))
                    with Horizontal(classes="dir-browse-row"):
                        yield Input(value=str(Path.cwd()), id="dir-input")
                        yield Button("...", id="dir-browse")
                    if self.operation == "save":
                        yield Label(TR("query.save_file"))
                        yield Input(
                            placeholder=TR("query.ph_save_file"),
                            id="save-file-input-2",
                        )
                    yield Label(TR("query.output_template"))
                    yield Input(
                        placeholder=TR("query.ph_output_template"),
                        value="{artists} - {title}.{output-ext}",
                        id="output-template-input",
                    )
                    yield Label(TR("query.overwrite"))
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
                    yield Label(TR("query.archive"))
                    yield Input(
                        placeholder=TR("query.ph_archive"),
                        id="archive-input",
                    )
                    yield Label(TR("query.m3u"))
                    yield Switch(id="m3u-checkbox")
                    yield Input(
                        placeholder=TR("query.ph_m3u"),
                        id="m3u-input",
                        disabled=True,
                    )
                    yield Label(TR("query.preload"))
                    yield Switch(id="preload-checkbox")
                    yield Label(TR("query.scan_for_songs"))
                    yield Switch(id="scan-for-songs-checkbox")
                    yield Label(TR("query.detect_formats"))
                    yield Select(
                        [(f, f) for f in _DETECT_FORMAT_CHOICES],
                        value="mp3",
                        allow_blank=True,
                        id="detect-formats-select",
                    )
                    yield Label(TR("query.restrict"))
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
                    yield Label(TR("query.max_filename_length"))
                    yield Input(
                        placeholder=TR("query.ph_max_filename"),
                        id="max-filename-length-input",
                    )
                    yield Label(TR("query.id3_separator"))
                    yield Input(
                        value="/",
                        placeholder=TR("query.ph_separator"),
                        id="id3-separator-input",
                    )
                    yield Label(TR("query.add_unavailable"))
                    yield Switch(id="add-unavailable-checkbox")
                    yield Label(TR("query.playlist_numbering"))
                    yield Switch(id="playlist-numbering-checkbox")
                    yield Label(TR("query.playlist_retain_track_cover"))
                    yield Switch(id="playlist-retain-track-cover-checkbox")
                    yield Label(TR("query.fetch_albums"))
                    yield Switch(id="fetch-albums-checkbox")

                with Collapsible(title=TR("section.filtering"), collapsed=True):
                    yield Label(TR("query.dont_filter_results"))
                    yield Switch(id="dont-filter-results-checkbox")
                    yield Label(TR("query.only_verified_results"))
                    yield Switch(id="only-verified-results-checkbox")
                    yield Label(TR("query.album_type"))
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
                    yield Label(TR("query.ytm_data"))
                    yield Switch(id="ytm-data-checkbox")
                    yield Label(TR("query.force_update_metadata"))
                    yield Switch(id="force-update-metadata-checkbox")
                    yield Label(TR("query.skip_album_art"))
                    yield Switch(id="skip-album-art-checkbox")
                    yield Label(TR("query.ignore_albums"))
                    yield Input(
                        placeholder=TR("query.ph_ignore_albums"),
                        id="ignore-albums-input",
                    )
                    yield Label(TR("query.skip_explicit"))
                    yield Switch(id="skip-explicit-checkbox")
                    yield Label(TR("query.create_skip_file"))
                    yield Switch(id="create-skip-file-checkbox")
                    yield Label(TR("query.respect_skip_file"))
                    yield Switch(id="respect-skip-file-checkbox")

                with Collapsible(title=TR("section.network_auth"), collapsed=True):
                    yield Label(TR("query.cookie_file"))
                    yield Input(
                        placeholder=TR("query.ph_cookie"),
                        id="cookie-file-input",
                    )
                    yield Label(TR("query.sponsor_block"))
                    yield Switch(id="sponsor-block-checkbox")
                    yield Label(TR("query.proxy"))
                    yield Input(
                        placeholder=TR("query.ph_proxy"),
                        id="proxy-input",
                    )
                    yield Label(TR("query.yt_dlp_args"))
                    yield Input(
                        placeholder=TR("query.ph_ytdlp_args"),
                        id="yt-dlp-args-input",
                    )

                with Collapsible(title=TR("section.finetuning"), collapsed=True):
                    yield Label(TR("query.print_errors"))
                    yield Switch(id="print-errors-checkbox")
                    yield Label(TR("query.save_errors"))
                    yield Input(
                        placeholder=TR("query.ph_errors"),
                        id="save-errors-input",
                    )
                    yield Label(TR("query.log_level"))
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
                    yield Label(TR("query.log_format"))
                    yield Input(
                        placeholder=TR("query.ph_log_format"),
                        id="log-format-input",
                    )
                    yield Label(TR("query.simple_tui"))
                    yield Switch(id="simple-tui-checkbox")

            with Vertical(id="ad-bottom"):
                yield Static("", id="status")
                yield RichLog(id="search-log", highlight=True, markup=True, wrap=True)
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
            if event.switch.value:
                query = self.query_one("#query-input", Input).value.strip()
                playlist_name = self._extract_playlist_name(query)
                if playlist_name:
                    m3u_input.value = f"{playlist_name}.m3u8"
                elif not m3u_input.value.strip():
                    m3u_input.value = "playlist.m3u8"

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

    def _extract_playlist_name(self, url: str) -> Optional[str]:
        patterns = [
            r"open\.spotify\.com/playlist/([^/?]+)",
            r"spotify:playlist:([^/?]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                playlist_id = match.group(1)
                return f"playlist_{playlist_id[:8]}"
        return None

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

        self.query_one("#search-btn", Button).disabled = True
        self.query_one("#status", Static).update(TR("query.searching"))
        add_url_entry(options["query"][0], self.operation)

        screen = self

        def run_search() -> None:
            app = cast("SpotdlApp", screen.app)
            try:
                app.state.ensure_spotify(user_auth=False)
                songs = get_simple_songs(
                    options["query"],
                    use_ytm_data=options.get("ytm_data", False),
                    playlist_numbering=options.get("playlist_numbering", False),
                )
                app.call_from_thread(screen._search_done, songs, options)
            except Exception as exc:
                app.call_from_thread(screen._search_failed, exc)

        self.run_worker(run_search, thread=True, exclusive=True, group="search")

    def _search_done(self, songs: List[Any], options: Dict[str, Any]) -> None:
        self.query_one("#search-btn", Button).disabled = False
        if not songs:
            self.query_one("#status", Static).update(TR("query.no_results"))
            return
        self.query_one("#status", Static).update(
            TR("query.found", count=str(len(songs)))
        )
        self.app.push_screen(TrackListScreen(self.operation, songs, options))

    def _search_failed(self, exc: Exception) -> None:
        logger.error(TR("query.search_failed"), exc_info=exc)
        self.query_one("#search-btn", Button).disabled = False
        self.query_one("#status", Static).update(TR("query.error", message=str(exc)))
