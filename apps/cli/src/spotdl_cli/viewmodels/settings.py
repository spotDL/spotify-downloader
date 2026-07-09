"""``SettingsViewModel`` — a data-driven form over ``CliConfig`` (CONTRACT A).

``fields()`` introspects ``CliConfig`` into ``SettingField``\\s (the 1,605-line
anti-pattern settings screen becomes ~160 lines rendering these). ``set`` coerces +
validates one field against a working copy without saving; ``save`` persists via the
``ConfigStore``. No ``textual`` and no direct pydantic import — coercion failures are
caught structurally.
"""

from __future__ import annotations

from pathlib import Path
from typing import get_args

from spotdl_cli.config import CliConfig
from spotdl_cli.viewmodels.base import ErrorDisplay, Loadable
from spotdl_cli.viewmodels.protocol import ConfigStore
from spotdl_cli.viewmodels.types import FieldKind, SettingField

# Choice fields and their allowed values (CliConfig stores these as plain strings,
# so the choice constraint is enforced here, not by pydantic).
_CHOICES: dict[str, tuple[str, ...]] = {
    "format": ("mp3", "flac", "m4a", "ogg", "opus", "wav"),
    "overwrite": ("skip", "metadata", "force"),
    "restrict": ("none", "ascii", "strict"),
}


class SettingsViewModel:
    def __init__(self, store: ConfigStore) -> None:
        self._store = store
        self._cfg = store.load()

    def fields(self) -> tuple[SettingField, ...]:
        """Enumerate every ``CliConfig`` field as a typed ``SettingField`` (pure)."""
        return tuple(self._field(name) for name in CliConfig.model_fields)

    def set(self, key: str, raw: str) -> Loadable[tuple[SettingField, ...]]:
        """Validate + coerce one field into the working copy (no save)."""
        if key not in CliConfig.model_fields:
            return _fail(f"unknown setting: {key}")
        choices = _CHOICES.get(key)
        if choices is not None and raw not in choices:
            return _fail(f"{key} must be one of: {', '.join(choices)}")
        try:
            coerced = getattr(CliConfig.model_validate({key: raw}), key)
        except Exception:
            return _fail(f"invalid value for {key}: {raw!r}")
        self._cfg = self._cfg.model_copy(update={key: coerced})
        return Loadable.ready(self.fields())

    def save(self) -> Loadable[tuple[SettingField, ...]]:
        """Persist the working copy via the ``ConfigStore``."""
        try:
            self._store.save(self._cfg)
        except Exception as exc:
            return _fail(f"couldn't save settings: {exc}")
        return Loadable.ready(self.fields())

    def _field(self, name: str) -> SettingField:
        annotation = CliConfig.model_fields[name].annotation
        kind = _kind(name, annotation)
        return SettingField(
            key=name,
            label=name.replace("_", " "),
            kind=kind,
            value=_render(getattr(self._cfg, name)),
            choices=_CHOICES.get(name),
        )


def _fail(message: str) -> Loadable[tuple[SettingField, ...]]:
    return Loadable.failed(ErrorDisplay(message, code=None, severity="error"))


def _kind(name: str, annotation: object) -> FieldKind:
    if name in _CHOICES:
        return "choice"
    if annotation is bool:
        return "bool"
    if annotation is int:
        return "int"
    if annotation is Path or Path in get_args(annotation):
        return "path"
    return "str"


def _render(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
