"""Pilot tests for the data-driven settings screen (Plan 9 Task 9, redesign §4).

The abandoned rewrite's settings screen was **1,605 lines**; this one renders
``SettingsViewModel.fields()`` — grouped into bordered Connection / Downloads
sections — through a dumb ``SettingsForm`` and delegates every edit + apply to the
view-model. Runs headless via ``App.run_test`` over the fake ``ConfigStore`` — no real
config file, client, server, or terminal. The contract: one control per field kind,
an inline error under the row that does not persist, a dirty-state footer, a valid
edit + Apply that reaches the store, Discard that reloads a clean copy, and a
reconnect notice when ``api_url`` changes (documented, no live reconnect in v1).
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


async def test_renders_one_control_per_field_kind_in_sections() -> None:
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
        # grouped into the two bordered sections
        app.screen.query_one("#form-section-0")
        app.screen.query_one("#form-section-1")


async def test_invalid_threads_shows_inline_error_and_does_not_persist() -> None:
    store = FakeConfigStore()
    app = SpotdlApp(_factory(store))
    async with app.run_test() as pilot:
        await _goto_settings(pilot, app)
        app.screen.query_one("#threads", Input).value = "not-a-number"
        await pilot.pause()
        # the inline error sits under the threads row and names the field
        error = app.screen.query_one("#settings-error-threads", Static)
        assert "threads" in str(error.render())
        assert not error.has_class("hidden")
        assert store.saves == []


async def test_dirty_footer_then_valid_apply_persists() -> None:
    store = FakeConfigStore()
    app = SpotdlApp(_factory(store))
    async with app.run_test() as pilot:
        await _goto_settings(pilot, app)
        app.screen.query_one("#threads", Input).value = "8"
        await pilot.pause()
        footer = app.screen.query_one("#settings-footer", Static)
        assert "Unsaved changes" in str(footer.render())
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert len(store.saves) == 1
        assert store.saves[-1].threads == 8
        assert "Unsaved changes" not in str(footer.render())


async def test_discard_reverts_edits() -> None:
    store = FakeConfigStore()
    app = SpotdlApp(_factory(store))
    async with app.run_test() as pilot:
        await _goto_settings(pilot, app)
        app.screen.query_one("#threads", Input).value = "8"
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        # the form was reloaded clean from the store: control back to the default
        assert app.screen.query_one("#threads", Input).value == "4"
        assert store.saves == []
        assert "Unsaved changes" not in str(
            app.screen.query_one("#settings-footer", Static).render()
        )


async def test_changing_api_url_and_applying_notifies_reconnect() -> None:
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
