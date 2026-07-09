"""``SettingsForm`` — a data-driven ``CliConfig`` editor in bordered sections (§4).

Renders a sequence of ``(section title, fields)`` groups as bordered ``.panel``
sections (Connection / Downloads …); each field is one aligned ``label + control``
row — a ``Switch`` for a bool, a ``Select`` for a choice, an ``Input`` otherwise —
with an inline error slot directly under the row. The widget holds no config
knowledge and never validates: it emits :class:`SettingsForm.FieldChanged` and the
``SettingsScreen`` funnels each change to the ``SettingsViewModel``, feeding any error
back via :meth:`set_error`. This dumb, data-driven form is the antidote to the
abandoned rewrite's 1,605-line settings screen (spec §13).
"""

from __future__ import annotations

from collections.abc import Sequence

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, Select, Static, Switch

from spotdl_cli.viewmodels.types import SettingField

FormSections = Sequence[tuple[str, tuple[SettingField, ...]]]


class SettingsForm(VerticalScroll):
    """A scroll of bordered sections, each a stack of aligned label+control rows."""

    class FieldChanged(Message):
        """A control changed; ``value`` is the raw string for the VM to validate."""

        def __init__(self, key: str, value: str) -> None:
            self.key = key
            self.value = value
            super().__init__()

    def __init__(self, sections: FormSections, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._sections = tuple(sections)

    def compose(self) -> ComposeResult:
        for index, (_title, fields) in enumerate(self._sections):
            with Vertical(classes="form-section panel", id=f"form-section-{index}"):
                for field in fields:
                    with Horizontal(classes="form-row"):
                        yield Label(field.label, classes="form-label")
                        yield _control(field)
                    yield Static("", id=_error_id(field.key), classes="field-error hidden")

    def on_mount(self) -> None:
        for index, (title, _fields) in enumerate(self._sections):
            self.query_one(f"#form-section-{index}", Vertical).border_title = title

    def set_error(self, key: str, message: str | None) -> None:
        """Show (or clear) the inline error under one field's row."""
        slot = self.query_one(f"#{_error_id(key)}", Static)
        slot.update(message or "")
        slot.set_class(message is None, "hidden")

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


def _error_id(key: str) -> str:
    return f"settings-error-{key}"


def _control(field: SettingField) -> Widget:
    """Build the control that matches a field's ``kind`` (id == the config key)."""
    if field.kind == "bool":
        return Switch(value=field.value == "true", id=field.key)
    if field.kind == "choice":
        options = [(choice, choice) for choice in (field.choices or ())]
        return Select(options, value=field.value, allow_blank=False, id=field.key)
    return Input(value=field.value, id=field.key)
