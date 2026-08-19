import os
from pathlib import Path
from typing import cast

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

_LABEL_IDS = {
    "lbl-operation": "cmdbuilder.operation",
    "lbl-query": "cmdbuilder.query",
    "lbl-format": "cmdbuilder.format",
    "lbl-bitrate": "cmdbuilder.bitrate",
    "lbl-audio": "cmdbuilder.audio_providers",
    "lbl-lyrics": "cmdbuilder.lyrics_providers",
    "lbl-threads": "cmdbuilder.threads",
    "lbl-output-template": "cmdbuilder.output_template",
    "lbl-overwrite": "cmdbuilder.overwrite",
    "lbl-output-dir": "cmdbuilder.output_directory",
    "lbl-playlist-options": "cmdbuilder.playlist_options",
    "lbl-output-options": "cmdbuilder.output_options",
    "lbl-network": "cmdbuilder.network",
    "lbl-spotify-auth": "cmdbuilder.spotify_auth",
    "lbl-save-file": "cmdbuilder.save_file",
}

_CHECKBOX_IDS = {
    "cmd-playlist-numbering": "cmdbuilder.playlist_numbering",
    "cmd-playlist-retain-cover": "cmdbuilder.retain_track_cover",
    "cmd-fetch-albums": "cmdbuilder.fetch_albums",
    "cmd-m3u": "cmdbuilder.generate_m3u",
    "cmd-generate-lrc": "cmdbuilder.generate_lrc",
    "cmd-sponsor-block": "cmdbuilder.sponsor_block",
    "cmd-scan-for-songs": "cmdbuilder.scan_for_songs",
    "cmd-create-skip": "cmdbuilder.generate_skip",
    "cmd-user-auth": "cmdbuilder.user_auth",
}

_INPUT_PLACEHOLDER_IDS = {
    "cmd-query": "cmdbuilder.query_placeholder",
    "cmd-threads": "cmdbuilder.placeholder_threads",
    "cmd-output-template": "cmdbuilder.placeholder_template",
    "cmd-m3u-name": "cmdbuilder.placeholder_m3u",
    "cmd-save-file": "cmdbuilder.placeholder_save_file",
    "cmd-proxy": "cmdbuilder.placeholder_proxy",
    "cmd-cookie-file": "cmdbuilder.placeholder_cookie",
    "cmd-yt-dlp-args": "cmdbuilder.placeholder_ytdlp",
    "cmd-client-id": "cmdbuilder.client_id",
    "cmd-client-secret": "cmdbuilder.client_secret",
}

_BUTTON_IDS = {
    "cmd-copy": "cmdbuilder.btn_copy",
    "cmd-test": "cmdbuilder.btn_test",
}


class CommandBuilder(VerticalScroll):
    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    def compose(self) -> ComposeResult:
        yield Static(
            TR("cmdbuilder.title"), id="cmdbuilder-title", classes="menu-title"
        )
        yield Static(TR("cmdbuilder.hint"), id="cmdbuilder-hint", classes="menu-hint")

        with Horizontal(classes="split-pane"):
            with Vertical(classes="left-pane"):
                yield Label(TR("cmdbuilder.operation"), id="lbl-operation")
                yield Select(
                    [(TR(key), value) for key, value in _OPERATION_OPTIONS],
                    value="download",
                    allow_blank=False,
                    id="cmd-operation",
                )

                yield Label(TR("cmdbuilder.query"), id="lbl-query")
                yield Input(
                    placeholder=TR("cmdbuilder.query_placeholder"),
                    id="cmd-query",
                )

                yield Label(TR("cmdbuilder.format"), id="lbl-format")
                yield Select(
                    [(f.upper(), f) for f in FORMATS],
                    value="mp3",
                    allow_blank=False,
                    id="cmd-format",
                )

                yield Label(TR("cmdbuilder.bitrate"), id="lbl-bitrate")
                yield Select(
                    [(b, b) for b in BITRATES],
                    value="128k",
                    allow_blank=False,
                    id="cmd-bitrate",
                )

                yield Label(TR("cmdbuilder.audio_providers"), id="lbl-audio")
                yield Select(
                    [(p, p) for p in AUDIO_PROVIDERS],
                    value="youtube-music",
                    allow_blank=False,
                    id="cmd-audio",
                )

                yield Label(TR("cmdbuilder.lyrics_providers"), id="lbl-lyrics")
                yield Select(
                    [(p, p) for p in LYRICS_PROVIDERS],
                    value="genius",
                    allow_blank=False,
                    id="cmd-lyrics",
                )

                yield Label(TR("cmdbuilder.threads"), id="lbl-threads")
                yield Input(
                    value="4",
                    placeholder=TR("cmdbuilder.placeholder_threads"),
                    id="cmd-threads",
                )

                yield Label(TR("cmdbuilder.output_template"), id="lbl-output-template")
                yield Input(
                    value="{artists} - {title}.{output-ext}",
                    placeholder=TR("cmdbuilder.placeholder_template"),
                    id="cmd-output-template",
                )

                yield Label(TR("cmdbuilder.overwrite"), id="lbl-overwrite")
                yield Select(
                    [(TR(key), value) for key, value in _OVERWRITE_OPTIONS],
                    value="skip",
                    id="cmd-overwrite",
                )

                yield Label(TR("cmdbuilder.output_directory"), id="lbl-output-dir")
                yield Input(value=str(Path.cwd()), id="cmd-output-dir")

            with Vertical(classes="right-pane"):
                yield Label(
                    TR("cmdbuilder.playlist_options"), id="lbl-playlist-options"
                )
                yield Checkbox(
                    TR("cmdbuilder.playlist_numbering"), id="cmd-playlist-numbering"
                )
                yield Checkbox(
                    TR("cmdbuilder.retain_track_cover"), id="cmd-playlist-retain-cover"
                )
                yield Checkbox(TR("cmdbuilder.fetch_albums"), id="cmd-fetch-albums")

                yield Label(TR("cmdbuilder.output_options"), id="lbl-output-options")
                yield Checkbox(TR("cmdbuilder.generate_m3u"), id="cmd-m3u")
                yield Input(
                    placeholder=TR("cmdbuilder.placeholder_m3u"),
                    id="cmd-m3u-name",
                    disabled=True,
                )
                yield Checkbox(TR("cmdbuilder.generate_lrc"), id="cmd-generate-lrc")
                yield Checkbox(TR("cmdbuilder.sponsor_block"), id="cmd-sponsor-block")
                yield Checkbox(TR("cmdbuilder.scan_for_songs"), id="cmd-scan-for-songs")
                yield Checkbox(TR("cmdbuilder.generate_skip"), id="cmd-create-skip")
                yield Label(TR("cmdbuilder.save_file"), id="lbl-save-file")
                yield Input(
                    placeholder=TR("cmdbuilder.placeholder_save_file"),
                    id="cmd-save-file",
                )

                yield Label(TR("cmdbuilder.network"), id="lbl-network")
                yield Input(
                    placeholder=TR("cmdbuilder.placeholder_proxy"), id="cmd-proxy"
                )
                yield Input(
                    placeholder=TR("cmdbuilder.placeholder_cookie"),
                    id="cmd-cookie-file",
                )
                yield Input(
                    placeholder=TR("cmdbuilder.placeholder_ytdlp"),
                    id="cmd-yt-dlp-args",
                )

                yield Label(TR("cmdbuilder.spotify_auth"), id="lbl-spotify-auth")
                yield Checkbox(TR("cmdbuilder.user_auth"), id="cmd-user-auth")
                yield Input(placeholder=TR("cmdbuilder.client_id"), id="cmd-client-id")
                yield Input(
                    placeholder=TR("cmdbuilder.client_secret"),
                    password=True,
                    id="cmd-client-secret",
                )

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

    def on_mount(self) -> None:
        self.set_timer(0.1, self.update_command)

    def on_select_changed(self, _event: Select.Changed) -> None:
        self.update_command()

    def on_input_changed(self, _event: Input.Changed) -> None:
        self.update_command()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "cmd-m3u":
            m3u_name = self.query_one("#cmd-m3u-name", Input)
            m3u_name.disabled = not event.checkbox.value
        self.update_command()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cmd-copy":
            self.copy_to_clipboard()
        elif event.button.id == "cmd-test":
            self.test_run()

    def update_command(self) -> None:
        parts = ["spotdl"]

        operation = self.query_one("#cmd-operation", Select).value
        if operation != "download":
            parts.append(cast(str, operation))

        query = self.query_one("#cmd-query", Input).value.strip()
        if query:
            parts.append(f'"{query}"')

        fmt = self.query_one("#cmd-format", Select).value
        if fmt != "mp3":
            parts.append(f"--format {fmt}")

        bitrate = self.query_one("#cmd-bitrate", Select).value
        if bitrate != "128k":
            parts.append(f"--bitrate {bitrate}")

        audio = self.query_one("#cmd-audio", Select).value
        if audio != "youtube-music":
            parts.append(f"--audio {audio}")

        lyrics = self.query_one("#cmd-lyrics", Select).value
        if lyrics != "genius":
            parts.append(f"--lyrics {lyrics}")

        threads = self.query_one("#cmd-threads", Input).value.strip()
        if threads and threads != "4":
            parts.append(f"--threads {threads}")

        overwrite = self.query_one("#cmd-overwrite", Select).value
        if overwrite != "skip":
            parts.append(f"--overwrite {overwrite}")

        output = (
            self.query_one("#cmd-output-template", Input).value.strip()
            or "{artists} - {title}.{output-ext}"
        )
        out_dir = self.query_one("#cmd-output-dir", Input).value.strip()
        if out_dir and out_dir != str(Path.cwd()):
            output = os.path.join(out_dir, output)
        if output != "{artists} - {title}.{output-ext}":
            parts.append(f'--output "{output}"')

        if self.query_one("#cmd-playlist-numbering", Checkbox).value:
            parts.append("--playlist-numbering")
        if self.query_one("#cmd-playlist-retain-cover", Checkbox).value:
            parts.append("--playlist-retain-track-cover")
        if self.query_one("#cmd-fetch-albums", Checkbox).value:
            parts.append("--fetch-albums")
        if self.query_one("#cmd-generate-lrc", Checkbox).value:
            parts.append("--generate-lrc")
        if self.query_one("#cmd-sponsor-block", Checkbox).value:
            parts.append("--sponsor-block")
        if self.query_one("#cmd-scan-for-songs", Checkbox).value:
            parts.append("--scan-for-songs")
        if self.query_one("#cmd-create-skip", Checkbox).value:
            parts.append("--create-skip-file")

        m3u_name = self.query_one("#cmd-m3u-name", Input).value.strip()
        if m3u_name and m3u_name != "{list[0]}.m3u8":
            parts.append(f'--m3u "{m3u_name}"')
        elif self.query_one("#cmd-m3u", Checkbox).value:
            parts.append('--m3u "{list[0]}.m3u8"')

        proxy = self.query_one("#cmd-proxy", Input).value.strip()
        if proxy:
            parts.append(f'--proxy "{proxy}"')

        cookie = self.query_one("#cmd-cookie-file", Input).value.strip()
        if cookie:
            parts.append(f'--cookie-file "{cookie}"')

        yt_dlp = self.query_one("#cmd-yt-dlp-args", Input).value.strip()
        if yt_dlp:
            parts.append(f'--yt-dlp-args "{yt_dlp}"')

        save_file = self.query_one("#cmd-save-file", Input).value.strip()
        if save_file:
            parts.append(f'--save-file "{save_file}"')

        user_auth = self.query_one("#cmd-user-auth", Checkbox).value
        if user_auth:
            parts.append("--user-auth")
            client_id = self.query_one("#cmd-client-id", Input).value.strip()
            if client_id:
                parts.append(f'--client-id "{client_id}"')
            client_secret = self.query_one("#cmd-client-secret", Input).value.strip()
            if client_secret:
                parts.append(f'--client-secret "{client_secret}"')

        cmd_str = " ".join(parts)
        log = self.query_one("#cmd-output", RichLog)
        log.clear()
        log.write(f"[bold cyan]$[/bold cyan] {cmd_str}")

    def _current_command(self) -> str:
        log = self.query_one("#cmd-output", RichLog)
        for line in reversed(log.lines):
            text = line.text
            if text.startswith("$ "):
                return text[2:]
        return ""

    def copy_to_clipboard(self) -> None:
        cmd = self._current_command()
        if not cmd:
            self.app.notify(TR("cmdbuilder.no_cmd_copy"), severity="warning")
            return
        try:
            clipboard_copy(cmd)
            self.app.notify(TR("cmdbuilder.copied"), severity="information")
        except Exception as exc:
            self.app.notify(
                TR("cmdbuilder.copy_failed", exc=str(exc)), severity="error"
            )

    def test_run(self) -> None:
        cmd = self._current_command()
        if not cmd:
            self.app.notify(TR("cmdbuilder.no_cmd_test"), severity="warning")
            return
        self.app.notify(TR("cmdbuilder.would_execute", cmd=cmd), timeout=5)

    def refresh_language(self) -> None:
        try:
            self.query_one("#cmdbuilder-title", Static).update(TR("cmdbuilder.title"))
            self.query_one("#cmdbuilder-hint", Static).update(TR("cmdbuilder.hint"))
            self.query_one("#cmdbuilder-generated-title", Static).update(
                TR("cmdbuilder.generated_command")
            )
        except Exception:
            pass

        for widget_id, key in _LABEL_IDS.items():
            try:
                self.query_one(f"#{widget_id}", Label).update(TR(key))
            except Exception:
                pass

        for widget_id, key in _CHECKBOX_IDS.items():
            try:
                self.query_one(f"#{widget_id}", Checkbox).label = TR(key)
            except Exception:
                pass

        for widget_id, key in _INPUT_PLACEHOLDER_IDS.items():
            try:
                self.query_one(f"#{widget_id}", Input).placeholder = TR(key)
            except Exception:
                pass

        for widget_id, key in _BUTTON_IDS.items():
            try:
                self.query_one(f"#{widget_id}", Button).label = TR(key)
            except Exception:
                pass

        try:
            operation_select = self.query_one("#cmd-operation", Select)
            current_op = operation_select.value
            operation_select.set_options(
                [(TR(key), value) for key, value in _OPERATION_OPTIONS]
            )
            operation_select.value = current_op
        except Exception:
            pass

        try:
            overwrite_select = self.query_one("#cmd-overwrite", Select)
            current_ow = overwrite_select.value
            overwrite_select.set_options(
                [(TR(key), value) for key, value in _OVERWRITE_OPTIONS]
            )
            overwrite_select.value = current_ow
        except Exception:
            pass
