import signal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Input,
    Label,
    OptionList,
    ProgressBar,
    RichLog,
    Static,
)
from textual.widgets.option_list import Option

from spotdl._version import __version__
from spotdl.console.tui import i18n
from spotdl.console.tui.bar import VersionFooter
from spotdl.console.tui.constants import SPOTDL_THEME
from spotdl.console.tui.css import CSS
from spotdl.utils import setup as setup_ops

__all__ = ["run_setup_ui", "open_setup_screen", "SetupChooseScreen"]

TR = i18n.tr

_SETUP_STEPS = [
    ("ffmpeg", setup_ops.ffmpeg_status, setup_ops.install_ffmpeg),
    ("deno", setup_ops.deno_status, setup_ops.install_deno),
]


class SetupChooseScreen(Screen):
    BINDINGS = [
        Binding("escape", "quit_app", "quit"),
    ]

    def __init__(self, current: Optional[Path], embedded: bool = False) -> None:
        super().__init__()
        self.current = current
        self.embedded = embedded

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="setup-box", classes="box"):
                with Horizontal(id="setup-header-row"):
                    yield Static(
                        TR("setup.title"), classes="menu-title", id="setup-title"
                    )
                    with Horizontal(id="setup-lang-bar"):
                        yield Button("EN", id="setup-lang-en")
                        yield Button("ES", id="setup-lang-es")
                if self.current is not None:
                    yield Static(
                        TR("setup.current", path=str(self.current)),
                        id="setup-current",
                    )
                cwd, subfolder = setup_ops.default_data_dir_choices()
                options = [
                    Option(TR("setup.choice_here", path=str(cwd)), id="1"),
                    Option(TR("setup.choice_sub", path=str(subfolder)), id="2"),
                    Option(TR("setup.choice_custom"), id="3"),
                ]
                yield OptionList(*options, id="setup-choices")
                with Vertical(id="setup-custom-row"):
                    yield Label(TR("setup.custom_label"), id="setup-custom-lbl")
                    yield Input(placeholder=TR("setup.custom_ph"), id="setup-custom")
                with Horizontal(id="setup-btns"):
                    yield Button(
                        TR("setup.btn_confirm"), variant="primary", id="setup-go"
                    )
                    yield Button(TR("setup.btn_quit"), id="setup-quit")
                yield Static("", id="setup-status")
        yield VersionFooter()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "3":
            self.query_one("#setup-custom", Input).focus()

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if event.option and event.option.id == "3":
            try:
                self.query_one("#setup-custom", Input).focus()
            except Exception:
                pass

    def refresh_language(self) -> None:
        try:
            self.query_one("#setup-title", Static).update(TR("setup.title"))
            if self.current is not None:
                self.query_one("#setup-current", Static).update(
                    TR("setup.current", path=str(self.current))
                )
            self.query_one("#setup-custom-lbl", Label).update(TR("setup.custom_label"))
            custom = self.query_one("#setup-custom", Input)
            custom.placeholder = TR("setup.custom_ph")
            self.query_one("#setup-go", Button).label = TR("setup.btn_confirm")
            self.query_one("#setup-quit", Button).label = TR("setup.btn_quit")
        except Exception:
            pass

        try:
            cwd, subfolder = setup_ops.default_data_dir_choices()
            opt_list = self.query_one("#setup-choices", OptionList)
            opt_list.replace_option_prompt("1", TR("setup.choice_here", path=str(cwd)))
            opt_list.replace_option_prompt(
                "2", TR("setup.choice_sub", path=str(subfolder))
            )
            opt_list.replace_option_prompt("3", TR("setup.choice_custom"))
        except Exception:
            pass
        try:
            self.query_one(VersionFooter).refresh_language()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "setup-lang-en":
            i18n.set_language("en")
            self.refresh_language()
            return
        if event.button.id == "setup-lang-es":
            i18n.set_language("es")
            self.refresh_language()
            return
        if event.button.id == "setup-quit":
            self._close()
            return
        if event.button.id == "setup-go":
            self._confirm()

    def action_quit_app(self) -> None:
        self._close()

    def _close(self) -> None:
        if self.embedded:
            self.app.pop_screen()
        else:
            self.app.exit()

    def _confirm(self) -> None:
        option_list = self.query_one("#setup-choices", OptionList)
        highlighted = option_list.highlighted
        choice = "1" if highlighted is None else str(highlighted + 1)
        custom = self.query_one("#setup-custom", Input).value
        data_dir = setup_ops.resolve_choice(choice, custom)
        if data_dir is None:
            self.query_one("#setup-status", Static).update(TR("setup.no_custom"))
            return
        self.app.push_screen(SetupProgressScreen(data_dir, embedded=self.embedded))


class SetupProgressScreen(Screen):
    BINDINGS = [
        Binding("escape", "quit_app", "quit"),
    ]

    def __init__(self, data_dir: Path, embedded: bool = False) -> None:
        super().__init__()
        self.data_dir = data_dir
        self.embedded = embedded
        self._step_ok: List[bool] = []
        self._active = True
        self._step_state: Dict[str, Tuple[str, str]] = {
            key: ("", f"setup.step_{key}") for key, _, _ in _SETUP_STEPS
        }

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="setup-progress-box", classes="box"):
                yield Static(
                    TR("setup.progress_title"),
                    classes="menu-title",
                    id="setup-progress-title",
                )
                yield Static(
                    TR("setup.target", path=str(self.data_dir)),
                    id="setup-progress-target",
                )
                with Vertical(id="setup-progress-table"):
                    for key, _, _ in _SETUP_STEPS:
                        yield Static(TR(f"setup.step_{key}"), id=f"step-{key}")
                        yield ProgressBar(total=100, show_eta=False, id=f"bar-{key}")
                yield RichLog(highlight=True, markup=True, id="setup-progress-log")
                with Horizontal(id="setup-progress-btns"):
                    yield Button(
                        TR("setup.btn_done"), variant="primary", id="setup-finish"
                    )
                yield Static("", id="setup-progress-status")
        yield VersionFooter()

    def on_mount(self) -> None:
        finish_btn = self.query_one("#setup-finish", Button)
        finish_btn.disabled = True
        self.run_worker(self._run_steps, thread=True, exclusive=True, group="setup")

    def action_quit_app(self) -> None:
        self._active = False
        self._close()

    def _close(self) -> None:
        if self.embedded:
            self.app.pop_screen()
        else:
            self.app.exit()

    def _set_step_color(self, step_key: str, color: str, text_key: str) -> None:
        self._step_state[step_key] = (color, text_key)
        self._render_step(step_key)

    def _render_step(self, step_key: str) -> None:
        color, text_key = self._step_state.get(step_key, ("", f"setup.step_{step_key}"))
        text = TR(text_key)
        try:
            label = self.query_one(f"#step-{step_key}", Static)
            label.update(f"[{color}]{text}[/{color}]" if color else text)
        except Exception:
            pass

    def refresh_language(self) -> None:
        try:
            self.query_one("#setup-progress-title", Static).update(
                TR("setup.progress_title")
            )
            self.query_one("#setup-progress-target", Static).update(
                TR("setup.target", path=str(self.data_dir))
            )
            for key, _, _ in _SETUP_STEPS:
                self._render_step(key)
            self.query_one("#setup-finish", Button).label = TR("setup.btn_done")
        except Exception:
            pass
        try:
            self.query_one(VersionFooter).refresh_language()
        except Exception:
            pass

    def _set_bar(self, step_key: str, percent: float) -> None:
        try:
            self.query_one(f"#bar-{step_key}", ProgressBar).update(progress=percent)
        except Exception:
            pass

    def _log(self, line: str) -> None:
        try:
            self.query_one("#setup-progress-log", RichLog).write(line)
        except Exception:
            pass

    def _run_steps(self) -> None:
        setup_ops.apply_data_dir(self.data_dir)
        manifest = setup_ops.prepare_data_dir(self.data_dir)
        self.app.call_from_thread(
            self._log, TR("setup.dir_set", path=str(self.data_dir.resolve()))
        )

        try:
            for key, status_fn, install_fn in _SETUP_STEPS:
                if not self._active:
                    return

                status_value, msg_key = status_fn(manifest)
                self.app.call_from_thread(
                    self._log,
                    TR(f"setup.status_{status_value}", step=TR(f"setup.step_{key}")),
                )

                if status_value == setup_ops._STEP_READY:
                    self._step_ok.append(True)
                    self.app.call_from_thread(
                        self._set_step_color, key, "green", f"setup.step_{key}_ready"
                    )
                    self.app.call_from_thread(self._set_bar, key, 100.0)
                elif status_value == setup_ops._STEP_NONE:
                    self._step_ok.append(True)
                    self.app.call_from_thread(
                        self._set_step_color, key, "yellow", "setup.step_skipped"
                    )
                    self.app.call_from_thread(self._set_bar, key, 100.0)
                    self.app.call_from_thread(self._log, TR(msg_key))
                else:
                    self.app.call_from_thread(
                        self._set_step_color,
                        key,
                        "cyan",
                        f"setup.step_{key}_downloading",
                    )
                    self.app.call_from_thread(self._set_bar, key, 10.0)
                    ok, result_key, path = install_fn(manifest)
                    self._step_ok.append(ok)
                    if ok:
                        self.app.call_from_thread(self._set_bar, key, 100.0)
                        self.app.call_from_thread(
                            self._set_step_color,
                            key,
                            "green",
                            f"setup.step_{key}_ready",
                        )
                        extra = str(path) if path is not None else ""
                        self.app.call_from_thread(self._log, TR(result_key, path=extra))
                    else:
                        self.app.call_from_thread(self._set_bar, key, 0.0)
                        self.app.call_from_thread(
                            self._set_step_color, key, "red", "setup.step_failed"
                        )
                        self.app.call_from_thread(self._log, TR(result_key))

            setup_ops.finalize_data_dir(self.data_dir, manifest)
            self.app.call_from_thread(self._finish)
        except Exception as exc:
            self.app.call_from_thread(self._fail, exc)

    def _finish(self) -> None:
        self._active = False
        all_ok = all(self._step_ok)
        if all_ok:
            self.query_one("#setup-progress-status", Static).update(TR("setup.done"))
            self.query_one("#setup-finish", Button).disabled = False
        else:
            self.query_one("#setup-progress-status", Static).update(
                TR("setup.done_with_errors")
            )
            self.query_one("#setup-finish", Button).disabled = False

    def _fail(self, exc: Exception) -> None:
        self._active = False
        self.query_one("#setup-progress-status", Static).update(
            TR("setup.error", message=str(exc))
        )
        self._log(str(exc))
        self.query_one("#setup-finish", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "setup-finish":
            self._active = False
            self._close()


class SetupApp(App):
    TITLE = f"spotDL {__version__} - Setup"
    CSS = CSS
    ENABLE_COMMAND_PALETTE = False

    def __init__(self, current: Optional[Path] = None) -> None:
        super().__init__()
        self.current = current
        self.register_theme(SPOTDL_THEME)
        self.theme = "spotdl"

    def get_default_screen(self) -> Screen:
        return SetupChooseScreen(self.current)


def open_setup_screen(app: App) -> None:
    from spotdl.utils.config import get_configured_data_dir

    current = get_configured_data_dir()
    app.push_screen(SetupChooseScreen(current, embedded=True))


def run_setup_ui(current: Optional[Path] = None) -> None:
    i18n.init()
    app = SetupApp(current=current)

    def _handle_signal(_signum, _frame) -> None:
        app.exit()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    app.run()
