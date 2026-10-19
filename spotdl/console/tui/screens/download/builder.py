"""
Interactive builder that turns the chosen options into a spotdl command.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple, cast

from pyperclip import PyperclipException
from pyperclip import copy as clipboard_copy
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Checkbox, Input, Label, RichLog, Select, Static

from spotdl.console.tui import i18n
from spotdl.console.tui.constants import (
    AUDIO_PROVIDERS,
    BITRATES,
    FORMATS,
    LYRICS_PROVIDERS,
)

TR = i18n.tr

DEFAULT_OUTPUT_TEMPLATE = "{artists} - {title}.{output-ext}"
DEFAULT_M3U_NAME = "{list[0]}.m3u8"

_OVERWRITE_OPTIONS = [
    ("cmdbuilder.ow_skip", "skip"),
    ("cmdbuilder.ow_force", "force"),
    ("cmdbuilder.ow_metadata", "metadata"),
]

_OPERATION_OPTIONS = [
    ("cmdbuilder.op_download_default", "download"),
    ("cmdbuilder.op_save", "save"),
    ("cmdbuilder.op_sync", "sync"),
    ("cmdbuilder.op_meta", "meta"),
    ("cmdbuilder.op_url", "url"),
]

_TEMPLATE_OPTIONS = [
    ("cmdbuilder.template_custom", "custom"),
    ("cmdbuilder.template_light", "light"),
    ("cmdbuilder.template_efficient", "efficient"),
    ("cmdbuilder.template_balanced", "balanced"),
    ("cmdbuilder.template_studio", "studio"),
]

_TEMPLATES = {
    "light": {
        "format": "opus",
        "bitrate": "96k",
        "threads": "8",
        "dont-filter-results": False,
        "only-verified-results": False,
        "preload": True,
        "generate-lrc": False,
    },
    "efficient": {
        "format": "mp3",
        "bitrate": "auto",
        "threads": "8",
        "dont-filter-results": False,
        "only-verified-results": False,
        "preload": True,
        "generate-lrc": False,
    },
    "balanced": {
        "format": "mp3",
        "bitrate": "320k",
        "threads": "4",
        "dont-filter-results": False,
        "only-verified-results": False,
        "preload": False,
        "generate-lrc": False,
    },
    "studio": {
        "format": "opus",
        "bitrate": "disable",
        "threads": "2",
        "dont-filter-results": False,
        "only-verified-results": True,
        "preload": False,
        "generate-lrc": False,
    },
}

_LABEL_IDS = {
    "lbl-operation": "cmdbuilder.operation",
    "lbl-query": "cmdbuilder.query",
    "lbl-template": "cmdbuilder.template",
    "lbl-format": "cmdbuilder.format",
    "lbl-bitrate": "cmdbuilder.bitrate",
    "lbl-audio": "cmdbuilder.audio_providers",
    "lbl-fallback-audio": "cmdbuilder.fallback_audio_provider",
    "lbl-lyrics": "cmdbuilder.lyrics_providers",
    "lbl-threads": "cmdbuilder.threads",
    "lbl-search-query": "cmdbuilder.search_query",
    "lbl-output-template": "cmdbuilder.output_template",
    "lbl-overwrite": "cmdbuilder.overwrite",
    "lbl-output-dir": "cmdbuilder.output_directory",
    "lbl-save-file": "cmdbuilder.save_file",
    "lbl-archive": "cmdbuilder.archive",
    "lbl-playlist-options": "cmdbuilder.playlist_options",
    "lbl-output-options": "cmdbuilder.output_options",
    "lbl-network": "cmdbuilder.network",
    "lbl-spotify-auth": "cmdbuilder.spotify_auth",
}

_CHECKBOX_IDS = {
    "cmd-preload": "cmdbuilder.preload",
    "cmd-generate-lrc": "cmdbuilder.generate_lrc",
    "cmd-only-verified-results": "cmdbuilder.only_verified_results",
    "cmd-dont-filter-results": "cmdbuilder.dont_filter_results",
    "cmd-skip-explicit": "cmdbuilder.skip_explicit",
    "cmd-force-update-metadata": "cmdbuilder.force_update_metadata",
    "cmd-skip-album-art": "cmdbuilder.skip_album_art",
    "cmd-playlist-numbering": "cmdbuilder.playlist_numbering",
    "cmd-playlist-retain-cover": "cmdbuilder.retain_track_cover",
    "cmd-fetch-albums": "cmdbuilder.fetch_albums",
    "cmd-m3u": "cmdbuilder.generate_m3u",
    "cmd-sponsor-block": "cmdbuilder.sponsor_block",
    "cmd-scan-for-songs": "cmdbuilder.scan_for_songs",
    "cmd-create-skip": "cmdbuilder.generate_skip",
    "cmd-user-auth": "cmdbuilder.user_auth",
}

_INPUT_PLACEHOLDER_IDS = {
    "cmd-query": "cmdbuilder.query_placeholder",
    "cmd-threads": "query.ph_threads",
    "cmd-search-query": "query.ph_lyrics_template",
    "cmd-output-template": "query.ph_output_template",
    "cmd-save-file": "query.ph_save_file",
    "cmd-archive": "query.ph_archive",
    "cmd-m3u-name": "cmdbuilder.placeholder_m3u",
    "cmd-cookie-file": "query.ph_cookie",
    "cmd-proxy": "query.ph_proxy",
    "cmd-yt-dlp-args": "query.ph_ytdlp_args",
    "cmd-client-id": "cmdbuilder.client_id",
    "cmd-client-secret": "cmdbuilder.client_secret",
}

_BUTTON_IDS = {
    "cmd-copy": "cmdbuilder.btn_copy",
    "cmd-test": "cmdbuilder.btn_test",
    "cmd-back": "cmdbuilder.btn_back",
}

_TRANSLATED_SELECTS = {
    "cmd-operation": _OPERATION_OPTIONS,
    "cmd-overwrite": _OVERWRITE_OPTIONS,
    "cmd-template": _TEMPLATE_OPTIONS,
}

_FLAG_CHECKBOXES = [
    ("cmd-preload", "--preload"),
    ("cmd-generate-lrc", "--generate-lrc"),
    ("cmd-only-verified-results", "--only-verified-results"),
    ("cmd-dont-filter-results", "--dont-filter-results"),
    ("cmd-skip-explicit", "--skip-explicit"),
    ("cmd-force-update-metadata", "--force-update-metadata"),
    ("cmd-skip-album-art", "--skip-album-art"),
]

_OUTPUT_CHECKBOXES = [
    ("cmd-playlist-numbering", "--playlist-numbering"),
    ("cmd-playlist-retain-cover", "--playlist-retain-track-cover"),
    ("cmd-fetch-albums", "--fetch-albums"),
    ("cmd-sponsor-block", "--sponsor-block"),
    ("cmd-scan-for-songs", "--scan-for-songs"),
    ("cmd-create-skip", "--create-skip-file"),
]

_QUOTED_INPUTS = [
    ("cmd-search-query", "--search-query"),
    ("cmd-save-file", "--save-file"),
    ("cmd-archive", "--archive"),
]

_NETWORK_INPUTS = [
    ("cmd-cookie-file", "--cookie-file"),
    ("cmd-proxy", "--proxy"),
    ("cmd-yt-dlp-args", "--yt-dlp-args"),
]


def _translated(options: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    return [(TR(key), value) for key, value in options]


class CommandBuilder(Vertical):
    """
    Form that shows the spotdl command matching the chosen options.

    ### Attributes
    - command: The current command, empty until the form is mounted.
    """

    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.command = ""

    def _input(self, widget_id: str, value: str = "", **kwargs) -> Input:
        return Input(
            value=value,
            placeholder=TR(_INPUT_PLACEHOLDER_IDS[widget_id]),
            id=widget_id,
            **kwargs,
        )

    def _checkbox(self, widget_id: str) -> Checkbox:
        return Checkbox(TR(_CHECKBOX_IDS[widget_id]), id=widget_id)

    def _label(self, widget_id: str) -> Label:
        return Label(TR(_LABEL_IDS[widget_id]), id=widget_id)

    def compose(self) -> ComposeResult:
        """
        Build the two option columns and the generated command area.
        """

        yield Static(
            TR("cmdbuilder.title"), id="cmdbuilder-title", classes="menu-title"
        )
        yield Static(TR("cmdbuilder.hint"), id="cmdbuilder-hint", classes="menu-hint")

        with Horizontal(classes="split-pane"):
            with VerticalScroll(classes="left-pane"):
                yield self._label("lbl-operation")
                yield Select(
                    _translated(_OPERATION_OPTIONS),
                    value="download",
                    allow_blank=False,
                    id="cmd-operation",
                )

                yield self._label("lbl-query")
                yield self._input("cmd-query")

                yield self._label("lbl-output-dir")
                yield Input(value=str(Path.cwd()), id="cmd-output-dir")

                yield self._label("lbl-template")
                yield Select(
                    _translated(_TEMPLATE_OPTIONS),
                    value="custom",
                    allow_blank=False,
                    id="cmd-template",
                )

                yield self._label("lbl-format")
                yield Select(
                    [(f.upper(), f) for f in FORMATS],
                    value="mp3",
                    allow_blank=False,
                    id="cmd-format",
                )

                yield self._label("lbl-bitrate")
                yield Select(
                    [(b, b) for b in BITRATES],
                    value="auto",
                    allow_blank=False,
                    id="cmd-bitrate",
                )

                yield self._label("lbl-audio")
                yield Select(
                    [(p, p) for p in AUDIO_PROVIDERS],
                    value="youtube-music",
                    allow_blank=False,
                    id="cmd-audio",
                )
                yield self._label("lbl-fallback-audio")
                yield Select(
                    [(TR("cmdbuilder.none"), "none")]
                    + [(p, p) for p in AUDIO_PROVIDERS],
                    value="none",
                    allow_blank=False,
                    id="cmd-fallback-audio",
                )

                yield self._label("lbl-threads")
                yield self._input("cmd-threads", value="4")

                yield self._checkbox("cmd-preload")
                yield self._checkbox("cmd-generate-lrc")

                yield self._label("lbl-lyrics")
                yield Select(
                    [(p, p) for p in LYRICS_PROVIDERS],
                    value="genius",
                    allow_blank=False,
                    id="cmd-lyrics",
                )

                yield self._label("lbl-search-query")
                yield self._input("cmd-search-query")

                yield self._checkbox("cmd-only-verified-results")
                yield self._checkbox("cmd-dont-filter-results")
                yield self._checkbox("cmd-skip-explicit")
                yield self._checkbox("cmd-force-update-metadata")
                yield self._checkbox("cmd-skip-album-art")

            with VerticalScroll(classes="right-pane"):
                yield self._label("lbl-output-template")
                yield self._input("cmd-output-template", value=DEFAULT_OUTPUT_TEMPLATE)

                yield self._label("lbl-overwrite")
                yield Select(
                    _translated(_OVERWRITE_OPTIONS),
                    value="skip",
                    id="cmd-overwrite",
                )

                yield self._label("lbl-save-file")
                yield self._input("cmd-save-file")

                yield self._label("lbl-archive")
                yield self._input("cmd-archive")

                yield self._label("lbl-playlist-options")
                yield self._checkbox("cmd-m3u")
                yield self._input("cmd-m3u-name", disabled=True)
                yield self._checkbox("cmd-playlist-numbering")
                yield self._checkbox("cmd-playlist-retain-cover")
                yield self._checkbox("cmd-fetch-albums")

                yield self._label("lbl-output-options")
                yield self._checkbox("cmd-sponsor-block")
                yield self._checkbox("cmd-scan-for-songs")
                yield self._checkbox("cmd-create-skip")

                yield self._label("lbl-network")
                yield self._input("cmd-cookie-file")
                yield self._input("cmd-proxy")
                yield self._input("cmd-yt-dlp-args")

                yield self._label("lbl-spotify-auth")
                yield self._checkbox("cmd-user-auth")
                yield self._input("cmd-client-id")
                yield self._input("cmd-client-secret", password=True)

        with Vertical(id="cmdbuilder-bottom"):
            yield Static(
                TR("cmdbuilder.generated_command"),
                id="cmdbuilder-generated-title",
                classes="menu-title",
            )
            yield RichLog(id="cmd-output", highlight=True, markup=True)

            with Horizontal(classes="row"):
                yield Button(
                    TR("cmdbuilder.btn_copy"), variant="primary", id="cmd-copy"
                )
                yield Button(TR("cmdbuilder.btn_test"), id="cmd-test")
                yield Button(TR("cmdbuilder.btn_back"), id="cmd-back")

    def on_mount(self) -> None:
        """
        Show the initial command.
        """

        self.update_command()

    def on_select_changed(self, event: Select.Changed) -> None:
        """
        Apply the chosen preset and update the command.
        """

        if event.select.id == "cmd-template":
            template = _TEMPLATES.get(cast(str, event.value))
            if template:
                self.query_one("#cmd-format", Select).value = template["format"]
                self.query_one("#cmd-bitrate", Select).value = template["bitrate"]
                self.query_one("#cmd-threads", Input).value = str(template["threads"])
                for flag in (
                    "dont-filter-results",
                    "only-verified-results",
                    "preload",
                    "generate-lrc",
                ):
                    self.query_one(f"#cmd-{flag}", Checkbox).value = bool(
                        template[flag]
                    )
        self.update_command()

    def on_input_changed(self, _event: Input.Changed) -> None:
        """
        Update the command after any text change.
        """

        self.update_command()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """
        Enable the M3U name input when needed and update the command.
        """

        if event.checkbox.id == "cmd-m3u":
            self.query_one("#cmd-m3u-name", Input).disabled = not event.checkbox.value
        self.update_command()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Copy, test or leave the builder.
        """

        if event.button.id == "cmd-copy":
            self.copy_to_clipboard()
        elif event.button.id == "cmd-test":
            self.test_run()
        elif event.button.id == "cmd-back":
            self.action_back()

    def action_back(self) -> None:
        """
        Go back to the previous screen.
        """

        self.app.pop_screen()

    def _value(self, widget_id: str) -> str:
        return self.query_one(f"#{widget_id}", Input).value.strip()

    def _selected(self, widget_id: str) -> Optional[str]:
        value = self.query_one(f"#{widget_id}", Select).value
        return None if value is Select.NULL else cast(str, value)

    def _checked(self, widget_id: str) -> bool:
        return self.query_one(f"#{widget_id}", Checkbox).value

    def build_command(self) -> str:
        """
        Build the command from the current form values.

        ### Returns
        - The spotdl command, leaving out options that keep their default value.
        """

        parts = ["spotdl"]

        operation = self._selected("cmd-operation")
        if operation and operation != "download":
            parts.append(operation)

        query = self._value("cmd-query")
        if query:
            parts.append(f'"{query}"')

        audio_format = self._selected("cmd-format")
        if audio_format and audio_format != "mp3":
            parts.append(f"--format {audio_format}")

        bitrate = self._selected("cmd-bitrate")
        if bitrate and bitrate != "auto":
            parts.append(f"--bitrate {bitrate}")

        audio = self._selected("cmd-audio")
        fallback_audio = self._selected("cmd-fallback-audio")
        if fallback_audio and fallback_audio not in ("none", audio):
            parts.append(f"--audio {audio or 'youtube-music'} {fallback_audio}")
        elif audio and audio != "youtube-music":
            parts.append(f"--audio {audio}")

        lyrics = self._selected("cmd-lyrics")
        if lyrics and lyrics != "genius":
            parts.append(f"--lyrics {lyrics}")

        threads = self._value("cmd-threads")
        if threads and threads != "4":
            parts.append(f"--threads {threads}")

        overwrite = self._selected("cmd-overwrite")
        if overwrite and overwrite != "skip":
            parts.append(f"--overwrite {overwrite}")

        output = self._value("cmd-output-template") or DEFAULT_OUTPUT_TEMPLATE
        output_dir = self._value("cmd-output-dir")
        if output_dir and output_dir != str(Path.cwd()):
            output = os.path.join(output_dir, output)
        if output != DEFAULT_OUTPUT_TEMPLATE:
            parts.append(f'--output "{output}"')

        parts.extend(
            flag for widget_id, flag in _FLAG_CHECKBOXES if self._checked(widget_id)
        )

        for widget_id, flag in _QUOTED_INPUTS:
            if self._value(widget_id):
                parts.append(f'{flag} "{self._value(widget_id)}"')

        parts.extend(
            flag for widget_id, flag in _OUTPUT_CHECKBOXES if self._checked(widget_id)
        )

        m3u_name = self._value("cmd-m3u-name")
        if m3u_name and m3u_name != DEFAULT_M3U_NAME:
            parts.append(f'--m3u "{m3u_name}"')
        elif self._checked("cmd-m3u"):
            parts.append(f'--m3u "{DEFAULT_M3U_NAME}"')

        for widget_id, flag in _NETWORK_INPUTS:
            if self._value(widget_id):
                parts.append(f'{flag} "{self._value(widget_id)}"')

        if self._checked("cmd-user-auth"):
            parts.append("--user-auth")
            if self._value("cmd-client-id"):
                parts.append(f'--client-id "{self._value("cmd-client-id")}"')
            if self._value("cmd-client-secret"):
                parts.append(f'--client-secret "{self._value("cmd-client-secret")}"')

        return " ".join(parts)

    def update_command(self) -> None:
        """
        Rebuild the command and show it.
        """

        self.command = self.build_command()
        log = self.query_one("#cmd-output", RichLog)
        log.clear()
        log.write(f"[bold cyan]$[/bold cyan] {self.command}")

    def copy_to_clipboard(self) -> None:
        """
        Copy the current command to the clipboard.
        """

        if not self.command:
            self.app.notify(TR("cmdbuilder.no_cmd_copy"), severity="warning")
            return
        try:
            clipboard_copy(self.command)
        except PyperclipException as exc:
            self.app.notify(
                TR("cmdbuilder.copy_failed", exc=str(exc)), severity="error"
            )
            return
        self.app.notify(TR("cmdbuilder.copied"), severity="information")

    def test_run(self) -> None:
        """
        Show the command that would run, without running it.
        """

        if not self.command:
            self.app.notify(TR("cmdbuilder.no_cmd_test"), severity="warning")
            return
        self.app.notify(TR("cmdbuilder.would_execute", cmd=self.command), timeout=5)

    def refresh_language(self) -> None:
        """
        Translate the builder to the current language, keeping the chosen values.
        """

        self.query_one("#cmdbuilder-title", Static).update(TR("cmdbuilder.title"))
        self.query_one("#cmdbuilder-hint", Static).update(TR("cmdbuilder.hint"))
        self.query_one("#cmdbuilder-generated-title", Static).update(
            TR("cmdbuilder.generated_command")
        )

        for widget_id, key in _LABEL_IDS.items():
            self.query_one(f"#{widget_id}", Label).update(TR(key))
        for widget_id, key in _CHECKBOX_IDS.items():
            self.query_one(f"#{widget_id}", Checkbox).label = TR(key)
        for widget_id, key in _INPUT_PLACEHOLDER_IDS.items():
            self.query_one(f"#{widget_id}", Input).placeholder = TR(key)
        for widget_id, key in _BUTTON_IDS.items():
            self.query_one(f"#{widget_id}", Button).label = TR(key)

        for widget_id, options in _TRANSLATED_SELECTS.items():
            select = self.query_one(f"#{widget_id}", Select)
            current = select.value
            select.set_options(_translated(options))
            select.value = current
