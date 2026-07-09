"""``SettingsViewModel`` — CliConfig introspection, per-field validation, save."""

from __future__ import annotations

from spotdl_cli.config import CliConfig
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.settings import SettingsViewModel

from .conftest import FakeConfigStore


def _fields_by_key(vm: SettingsViewModel) -> dict[str, object]:
    return {field.key: field for field in vm.fields()}


def test_fields_cover_every_config_field() -> None:
    vm = SettingsViewModel(FakeConfigStore())
    keys = {field.key for field in vm.fields()}
    assert keys == set(CliConfig.model_fields)


def test_field_kinds_and_choices() -> None:
    fields = _fields_by_key(SettingsViewModel(FakeConfigStore()))

    assert fields["format"].kind == "choice"  # type: ignore[attr-defined]
    assert fields["format"].choices == ("mp3", "flac", "m4a", "ogg", "opus", "wav")  # type: ignore[attr-defined]
    assert fields["overwrite"].kind == "choice"  # type: ignore[attr-defined]
    assert fields["restrict"].choices == ("none", "ascii", "strict")  # type: ignore[attr-defined]
    assert fields["threads"].kind == "int"  # type: ignore[attr-defined]
    assert fields["offline"].kind == "bool"  # type: ignore[attr-defined]
    assert fields["embed_lyrics"].kind == "bool"  # type: ignore[attr-defined]
    assert fields["output_dir"].kind == "path"  # type: ignore[attr-defined]
    assert fields["cookie_file"].kind == "path"  # type: ignore[attr-defined]
    assert fields["api_url"].kind == "str"  # type: ignore[attr-defined]


def test_set_int_coerces() -> None:
    store = FakeConfigStore()
    vm = SettingsViewModel(store)
    result = vm.set("threads", "8")
    assert result.state is LoadState.READY
    assert _fields_by_key(vm)["threads"].value == "8"  # type: ignore[attr-defined]
    assert store.saves == []  # set does not save


def test_set_bad_int_fails_without_mutating() -> None:
    store = FakeConfigStore()
    vm = SettingsViewModel(store)
    result = vm.set("threads", "not-a-number")
    assert result.state is LoadState.ERROR
    # working copy unchanged (still the default 4)
    assert _fields_by_key(vm)["threads"].value == "4"  # type: ignore[attr-defined]


def test_set_invalid_choice_rejected() -> None:
    vm = SettingsViewModel(FakeConfigStore())
    result = vm.set("format", "xyz")
    assert result.state is LoadState.ERROR
    assert _fields_by_key(vm)["format"].value == "mp3"  # type: ignore[attr-defined]


def test_set_valid_choice_accepted() -> None:
    vm = SettingsViewModel(FakeConfigStore())
    result = vm.set("format", "flac")
    assert result.state is LoadState.READY
    assert _fields_by_key(vm)["format"].value == "flac"  # type: ignore[attr-defined]


def test_set_unknown_key_fails() -> None:
    vm = SettingsViewModel(FakeConfigStore())
    assert vm.set("bogus", "x").state is LoadState.ERROR


def test_save_persists_via_store() -> None:
    store = FakeConfigStore()
    vm = SettingsViewModel(store)
    vm.set("threads", "6")
    vm.set("format", "opus")
    result = vm.save()
    assert result.state is LoadState.READY
    assert len(store.saves) == 1
    assert store.saves[0].threads == 6
    assert store.saves[0].format == "opus"
