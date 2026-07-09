"""``SettingsForm`` — a data-driven ``CliConfig`` editor (CONTRACT B/D).

Renders a ``tuple[SettingField, ...]`` as one labelled control per field — a
``Switch`` for a bool, a ``Select`` for a choice, an ``Input`` otherwise — and emits
:class:`SettingsForm.FieldChanged` whenever a control's value changes. The widget
holds no config knowledge and never validates: the ``SettingsScreen`` funnels each
change to the ``SettingsViewModel``. This dumb, data-driven form is the antidote to
the abandoned rewrite's 1,605-line settings screen (spec §13).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, Select, Switch

from spotdl_cli.viewmodels.types import SettingField


class SettingsForm(VerticalScroll):
    """A scrollable stack of labelled controls, one per ``SettingField``."""

    class FieldChanged(Message):
        """A control changed; ``value`` is the raw string for the VM to validate."""

        def __init__(self, key: str, value: str) -> None:
            self.key = key
            self.value = value
            super().__init__()

    def __init__(self, fields: tuple[SettingField, ...], *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._fields = fields

    def compose(self) -> ComposeResult:
        for field in self._fields:
            yield Label(field.label, classes="settings-label")
            yield _control(field)

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        self.post_message(self.FieldChanged(event.input.id or "", event.value))

    def on_select_changed(self, event: Select.Changed) -> None:
        event.stop()
        value = "" if event.value is Select.BLANK else str(event.value)
        self.post_message(self.FieldChanged(event.select.id or "", value))

    def on_switch_changed(self, event: Switch.Changed) -> None:
        event.stop()
        raw = "true" if event.value else "false"
        self.post_message(self.FieldChanged(event.switch.id or "", raw))


def _control(field: SettingField) -> Widget:
    """Build the control that matches a field's ``kind`` (id == the config key)."""
    if field.kind == "bool":
        return Switch(value=field.value == "true", id=field.key)
    if field.kind == "choice":
        options = [(choice, choice) for choice in (field.choices or ())]
        return Select(options, value=field.value, allow_blank=False, id=field.key)
    return Input(value=field.value, id=field.key)
