"""Pilot tests for the data-driven settings screen (Plan 9 Task 9).

The abandoned rewrite's settings screen was **1,605 lines**; this one renders
``SettingsViewModel.fields()`` through a dumb ``SettingsForm`` and delegates every
edit + save to the view-model. Runs headless via ``App.run_test`` over the fake
``ConfigStore`` — no real config file, client, server, or terminal. The contract:
one control per field kind, an inline validation error that does not persist, a
valid edit + save that reaches the store, and a reconnect notice when ``api_url``
changes (the client is rebuilt on next launch — documented, no live reconnect in v1).
"""

from __future__ import annotations

from spotdl_cli.config import CliConfig
from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.viewmodels.factory import ViewModelFactory
from textual.widgets import Input, Select, Static, Switch

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import FakeSpotdlClient

_ORIGIN = "https://api.example.test"
_TRANSPORT = "remote · api.example.test"


def _factory(store: FakeConfigStore) -> ViewModelFactory:
    return ViewModelFactory(
        FakeSpotdlClient(),
        FakeCredentialStore(),
        store,
        server_origin=_ORIGIN,
        transport_label=_TRANSPORT,
    )


async def _goto_settings(pilot: object, app: SpotdlApp) -> None:
    await pilot.pause()  # type: ignore[attr-defined]
    await pilot.press("4")  # type: ignore[attr-defined]
    assert app.current_mode == "settings"
    await pilot.pause()  # type: ignore[attr-defined]


async def test_renders_one_control_per_field_kind() -> None:
    app = SpotdlApp(_factory(FakeConfigStore()))
    async with app.run_test() as pilot:
        await _goto_settings(pilot, app)
        # every CliConfig field maps to exactly one control, of the right kind
        controls = (
            len(app.screen.query(Input))
            + len(app.screen.query(Select))
            + len(app.screen.query(Switch))
        )
        assert controls == len(CliConfig.model_fields)
        app.screen.query_one("#api_url", Input)  # str -> Input
        app.screen.query_one("#threads", Input)  # int -> Input
        app.screen.query_one("#format", Select)  # choice -> Select
        app.screen.query_one("#offline", Switch)  # bool -> Switch


async def test_invalid_threads_shows_inline_error_and_does_not_persist() -> None:
    store = FakeConfigStore()
    app = SpotdlApp(_factory(store))
    async with app.run_test() as pilot:
        await _goto_settings(pilot, app)
        app.screen.query_one("#threads", Input).value = "not-a-number"
        await pilot.pause()
        # inline validation line names the field; nothing was written to the store
        assert "threads" in str(app.screen.query_one("#settings-error", Static).render())
        assert store.saves == []


async def test_valid_edit_and_save_persists() -> None:
    store = FakeConfigStore()
    app = SpotdlApp(_factory(store))
    async with app.run_test() as pilot:
        await _goto_settings(pilot, app)
        app.screen.query_one("#threads", Input).value = "8"
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert len(store.saves) == 1
        assert store.saves[-1].threads == 8


async def test_changing_api_url_and_saving_notifies_reconnect() -> None:
    store = FakeConfigStore()
    app = SpotdlApp(_factory(store))
    async with app.run_test() as pilot:
        await _goto_settings(pilot, app)
        app.screen.query_one("#api_url", Input).value = "https://other.example.test"
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert store.saves[-1].api_url == "https://other.example.test"
        messages = [n.message for n in app._notifications]
        assert any("reconnect" in message for message in messages)
