"""``SettingsScreen`` — the data-driven ``CliConfig`` editor (CONTRACT B/C).

Renders ``SettingsViewModel.fields()`` through a dumb :class:`SettingsForm`, funnels
each :class:`SettingsForm.FieldChanged` to ``SettingsViewModel.set`` (surfacing a
coercion failure inline, without persisting), and saves the working copy on
``ctrl+s`` via ``SettingsViewModel.save``. Editing ``api_url`` and saving raises a
reconnect notice: the client is rebuilt on the next launch, so the change applies
then — there is no live reconnect in v1. All logic lives in the view-model, keeping
this screen the antithesis of the 1,605-line rewrite settings screen (spec §13).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.tui.widgets.settings_form import SettingsForm
from spotdl_cli.viewmodels.base import ErrorDisplay, LoadState
from spotdl_cli.viewmodels.settings import SettingsViewModel
from spotdl_cli.viewmodels.types import SettingField

_RECONNECT_NOTICE = "api_url changed — restart spotDL to reconnect to the new server"


class SettingsScreen(SpotdlScreen):
    """Edit + save ``CliConfig``; validation and persistence live in the VM."""

    BINDINGS = [Binding("ctrl+s", "save", "Save")]

    def compose_content(self) -> ComposeResult:
        self._vm: SettingsViewModel = self.vm_factory.settings()
        self._api_url = _value_of(self._vm.fields(), "api_url")
        yield SettingsForm(self._vm.fields(), id="settings-form")
        yield Static("", id="settings-error", classes="settings-error")

    def on_settings_form_field_changed(self, event: SettingsForm.FieldChanged) -> None:
        result = self._vm.set(event.key, event.value)
        self._show_validation(result.error)

    def action_save(self) -> None:
        result = self._vm.save()
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        self._show_validation(None)
        api_url = _value_of(self._vm.fields(), "api_url")
        if api_url != self._api_url:
            self._api_url = api_url
            self.app.notify(_RECONNECT_NOTICE, severity="information")

    def _show_validation(self, error: ErrorDisplay | None) -> None:
        self.query_one("#settings-error", Static).update("" if error is None else error.message)


def _value_of(fields: tuple[SettingField, ...], key: str) -> str:
    for field in fields:
        if field.key == key:
            return field.value
    return ""
