"""Pilot tests for the auth screen (Plan 9 Task 10).

Runs headless via ``App.run_test`` with a :class:`ViewModelFactory` over
:class:`FakeSpotdlClient` + fake stores — no real client, server, or terminal. The
contract: show identity (guest / signed-in email) and a login form; login/register
mint + store a PAT and repaint the status bar (the app re-loads ``SessionSnapshot``
via ``AuthChanged``); logout clears it; and when ``can_auth`` is False the screen
shows the exact copy-locked ``OFFLINE_AUTH_MESSAGE`` with no form.
"""

from __future__ import annotations

from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.tui.screens.auth import AuthScreen
from spotdl_cli.tui.widgets.status_bar import StatusBar
from spotdl_cli.viewmodels.auth import OFFLINE_AUTH_MESSAGE
from spotdl_cli.viewmodels.factory import ViewModelFactory
from textual.widgets import Button, Input, Static

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import FakeSpotdlClient, make_config, make_features, make_pat, make_tokens, make_user

_ORIGIN = "https://api.example.test"
_TRANSPORT = "remote · api.example.test"


def _factory(
    client: FakeSpotdlClient | None = None,
    creds: FakeCredentialStore | None = None,
) -> ViewModelFactory:
    return ViewModelFactory(
        client if client is not None else FakeSpotdlClient(),
        creds if creds is not None else FakeCredentialStore(),
        FakeConfigStore(),
        server_origin=_ORIGIN,
        transport_label=_TRANSPORT,
    )


async def test_shows_guest_status_and_login_form() -> None:
    app = SpotdlApp(_factory())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("4")
        assert app.current_mode == "auth"
        await pilot.pause()
        assert "Guest" in str(app.screen.query_one("#auth-status", Static).render())
        app.screen.query_one("#auth-email", Input)
        app.screen.query_one("#auth-login", Button)


async def test_login_mints_pat_and_repaints_status_bar() -> None:
    client = FakeSpotdlClient()
    client.login_result = make_tokens(user=make_user(email="user@example.com"))
    client.pat_result = make_pat(token="pat-x")
    client.users_by_token["pat-x"] = make_user(email="user@example.com")
    creds = FakeCredentialStore()
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("4")
        await pilot.pause()
        app.screen.query_one("#auth-email", Input).value = "user@example.com"
        app.screen.query_one("#auth-password", Input).value = "hunter2hunter2"
        await pilot.click("#auth-login")
        await pilot.pause()
        await pilot.pause()
        assert creds.tokens[_ORIGIN] == "pat-x"
        assert "user@example.com" in app.screen.query_one(StatusBar).summary


async def test_register_mints_pat_and_stores() -> None:
    client = FakeSpotdlClient()
    client.register_result = make_tokens(user=make_user(email="new@example.com"))
    client.pat_result = make_pat(token="pat-new")
    client.users_by_token["pat-new"] = make_user(email="new@example.com")
    creds = FakeCredentialStore()
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("4")
        await pilot.pause()
        app.screen.query_one("#auth-email", Input).value = "new@example.com"
        app.screen.query_one("#auth-password", Input).value = "hunter2hunter2"
        await pilot.click("#auth-register")
        await pilot.pause()
        await pilot.pause()
        assert creds.tokens[_ORIGIN] == "pat-new"
        assert client.called("register")


async def test_logout_clears_identity_and_status_bar() -> None:
    client = FakeSpotdlClient()
    creds = FakeCredentialStore()
    creds.store_token(_ORIGIN, "tok", "user@example.com")
    client.users_by_token["tok"] = make_user(email="user@example.com")
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("4")
        await pilot.pause()
        assert "user@example.com" in str(app.screen.query_one("#auth-status", Static).render())
        await pilot.click("#auth-logout")
        await pilot.pause()
        await pilot.pause()
        assert _ORIGIN not in creds.tokens
        assert "guest" in app.screen.query_one(StatusBar).summary


async def test_offline_shows_locked_message_and_no_form() -> None:
    client = FakeSpotdlClient(config=make_config(features=make_features(auth=False)))
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("4")  # section gated off when auth is unavailable
        assert app.current_mode == "home"
        await app.push_screen(AuthScreen())  # exercise the screen's offline state directly
        await pilot.pause()
        offline = str(app.screen.query_one("#auth-offline", Static).render())
        assert offline == OFFLINE_AUTH_MESSAGE
        assert len(app.screen.query(Input)) == 0
        assert len(app.screen.query(Button)) == 0
