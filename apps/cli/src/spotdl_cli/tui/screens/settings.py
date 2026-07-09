"""``SettingsScreen`` — the data-driven ``CliConfig`` editor in bordered sections (§4).

Renders ``SettingsViewModel.fields()`` grouped into bordered Connection / Downloads
sections through a dumb :class:`SettingsForm`, funnels each :class:`SettingsForm.
FieldChanged` to ``SettingsViewModel.set`` (surfacing a coercion failure inline under
the row, without persisting), and applies the working copy on ``enter``/``ctrl+s`` via
``SettingsViewModel.save``. A dirty-state footer offers ``enter`` Apply / ``esc``
Discard; Discard reloads a clean copy from the store. Editing ``api_url`` and applying
raises a reconnect notice — the client is rebuilt on the next launch, so the change
applies then (there is no live reconnect in v1). All logic lives in the view-model,
keeping this the antithesis of the 1,605-line rewrite settings screen (spec §13).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Input, Static

from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.tui.widgets.settings_form import FormSections, SettingsForm
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.settings import SettingsViewModel
from spotdl_cli.viewmodels.types import SettingField

_RECONNECT_NOTICE = "api_url changed — restart spotDL to reconnect to the new server"

# Which config keys belong to the Connection section; everything else is a download
# option. Grouping lives here (presentation), not in the data-driven view-model.
_CONNECTION_KEYS = ("api_url", "offline")

_CLEAN_FOOTER = "Saved. Edit a field to make changes."
_DIRTY_FOOTER = "● Unsaved changes — enter Apply · esc Discard"
_ERRORS_FOOTER = "⚠ Fix the highlighted fields before applying."


class SettingsScreen(SpotdlScreen):
    """Edit + apply ``CliConfig``; validation and persistence live in the VM."""

    BINDINGS = [
        Binding("ctrl+s", "apply", "Apply"),
        Binding("escape", "discard", "Discard", show=False),
    ]

    def compose_content(self) -> ComposeResult:
        self._vm: SettingsViewModel = self.vm_factory.settings()
        self._errors: set[str] = set()
        self._reset_tracking(self._vm.fields())
        yield SettingsForm(self._sections(), id="settings-form")
        yield Static(_CLEAN_FOOTER, id="settings-footer", classes="settings-footer")

    def on_settings_form_field_changed(self, event: SettingsForm.FieldChanged) -> None:
        self._pending[event.key] = event.value
        result = self._vm.set(event.key, event.value)
        message = result.error.message if result.error is not None else None
        self.query_one("#settings-form", SettingsForm).set_error(event.key, message)
        if message is None:
            self._errors.discard(event.key)
        else:
            self._errors.add(event.key)
        self._paint_footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Enter in any text field applies the whole form (footer promises "enter Apply").
        event.stop()
        self.action_apply()

    def action_apply(self) -> None:
        if self._errors:
            self.query_one("#settings-footer", Static).update(_ERRORS_FOOTER)
            return
        result = self._vm.save()
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        fields = self._vm.fields()
        if _value_of(fields, "api_url") != self._api_url:
            self.app.notify(_RECONNECT_NOTICE, severity="information")
        self._reset_tracking(fields)
        self._paint_footer()

    async def action_discard(self) -> None:
        if self._pending == self._baseline and not self._errors:
            return  # nothing to discard — leave escape as a no-op on this base screen
        self._vm = self.vm_factory.settings()
        self._errors.clear()
        self._reset_tracking(self._vm.fields())
        footer = self.query_one("#settings-footer", Static)
        await self.query_one("#settings-form", SettingsForm).remove()
        await self.query_one("#content-region").mount(
            SettingsForm(self._sections(), id="settings-form"), before=footer
        )
        self._paint_footer()

    def _reset_tracking(self, fields: tuple[SettingField, ...]) -> None:
        self._api_url = _value_of(fields, "api_url")
        self._baseline = {field.key: field.value for field in fields}
        self._pending = dict(self._baseline)

    def _paint_footer(self) -> None:
        if self._errors:
            text = _ERRORS_FOOTER
        elif self._pending != self._baseline:
            text = _DIRTY_FOOTER
        else:
            text = _CLEAN_FOOTER
        self.query_one("#settings-footer", Static).update(text)

    def _sections(self) -> FormSections:
        fields = self._vm.fields()
        connection = tuple(f for f in fields if f.key in _CONNECTION_KEYS)
        downloads = tuple(f for f in fields if f.key not in _CONNECTION_KEYS)
        return (("Connection", connection), ("Downloads", downloads))


def _value_of(fields: tuple[SettingField, ...], key: str) -> str:
    for field in fields:
        if field.key == key:
            return field.value
    return ""
