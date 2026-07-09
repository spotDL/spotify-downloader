"""Pilot tests for the Account screen (Plan 9 Task 10, redesign §4).

Runs headless via ``App.run_test`` with a :class:`ViewModelFactory` over
:class:`FakeSpotdlClient` + fake stores — no real client, server, or terminal. The
contract: one centred card that follows identity — signed-out shows the email +
password form (Sign in / Register) and the OAuth-in-web note; signed-in shows the
profile, admin badge, masked PAT, and [Rotate token]/[Revoke token]/[Sign out].
Login/register mint + store a PAT and repaint the status bar (the app re-loads
``SessionSnapshot`` via ``AuthChanged``); rotate replaces the PAT in place; revoke and
sign-out forget it; and when ``can_auth`` is False the card is the copy-locked
``OFFLINE_AUTH_MESSAGE`` with no form.
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


def _signed_in(*, is_admin: bool = False) -> tuple[FakeSpotdlClient, FakeCredentialStore]:
    client = FakeSpotdlClient()
    creds = FakeCredentialStore()
    creds.store_token(_ORIGIN, "tok", "user@example.com")
    client.users_by_token["tok"] = make_user(email="user@example.com", is_admin=is_admin)
    return client, creds


async def _goto_account(pilot: object, app: SpotdlApp) -> None:
    await pilot.pause()  # type: ignore[attr-defined]
    await pilot.press("5")  # type: ignore[attr-defined]
    assert app.current_mode == "auth"
    await pilot.pause()  # type: ignore[attr-defined]
    await pilot.pause()  # type: ignore[attr-defined]


async def test_signed_out_shows_form_and_oauth_note() -> None:
    app = SpotdlApp(_factory())
    async with app.run_test() as pilot:
        await _goto_account(pilot, app)
        app.screen.query_one("#auth-email", Input)
        app.screen.query_one("#auth-login", Button)
        app.screen.query_one("#auth-register", Button)
        note = " ".join(str(s.render()) for s in app.screen.query(Static))
        assert "web app" in note  # OAuth non-goal note points at the web UI


async def test_login_mints_pat_and_repaints_status_bar() -> None:
    client = FakeSpotdlClient()
    client.login_result = make_tokens(user=make_user(email="user@example.com"))
    client.pat_result = make_pat(token="pat-x")
    client.users_by_token["pat-x"] = make_user(email="user@example.com")
    creds = FakeCredentialStore()
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_account(pilot, app)
        app.screen.query_one("#auth-email", Input).value = "user@example.com"
        app.screen.query_one("#auth-password", Input).value = "hunter2hunter2"
        await pilot.click("#auth-login")
        await pilot.pause()
        await pilot.pause()
        assert creds.tokens[_ORIGIN] == "pat-x"
        assert "user@example.com" in app.screen.query_one(StatusBar).summary
        # the card flipped to the signed-in profile
        assert "user@example.com" in str(app.screen.query_one("#auth-status", Static).render())


async def test_register_mints_pat_and_stores() -> None:
    client = FakeSpotdlClient()
    client.register_result = make_tokens(user=make_user(email="new@example.com"))
    client.pat_result = make_pat(token="pat-new")
    client.users_by_token["pat-new"] = make_user(email="new@example.com")
    creds = FakeCredentialStore()
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_account(pilot, app)
        app.screen.query_one("#auth-email", Input).value = "new@example.com"
        app.screen.query_one("#auth-password", Input).value = "hunter2hunter2"
        await pilot.click("#auth-register")
        await pilot.pause()
        await pilot.pause()
        assert creds.tokens[_ORIGIN] == "pat-new"
        assert client.called("register")


async def test_signed_in_shows_admin_badge_and_masked_pat() -> None:
    client, creds = _signed_in(is_admin=True)
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_account(pilot, app)
        status = str(app.screen.query_one("#auth-status", Static).render())
        assert "user@example.com" in status
        assert "admin" in status
        pat = str(app.screen.query_one("#auth-pat", Static).render())
        assert "tok" in pat and pat.count("•") >= 4  # short prefix kept, rest masked


async def test_rotate_replaces_stored_token() -> None:
    client, creds = _signed_in()
    client.pat_result = make_pat(token="pat-rotated")
    client.users_by_token["pat-rotated"] = make_user(email="user@example.com")
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_account(pilot, app)
        await pilot.click("#auth-rotate")
        await pilot.pause()
        await pilot.pause()
        assert creds.tokens[_ORIGIN] == "pat-rotated"
        assert client.called("create_pat")
        assert "pat-ro" in str(app.screen.query_one("#auth-pat", Static).render())


async def test_revoke_forgets_token_and_shows_form() -> None:
    client, creds = _signed_in()
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_account(pilot, app)
        await pilot.click("#auth-revoke")
        await pilot.pause()
        await pilot.pause()
        assert _ORIGIN not in creds.tokens
        app.screen.query_one("#auth-login", Button)  # flipped back to the signed-out form


async def test_logout_clears_identity_and_status_bar() -> None:
    client, creds = _signed_in()
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_account(pilot, app)
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
        await pilot.press("5")  # section gated off when auth is unavailable
        assert app.current_mode == "home"
        await app.push_screen(AuthScreen())  # exercise the screen's offline state directly
        await pilot.pause()
        await pilot.pause()
        offline = str(app.screen.query_one("#auth-offline", Static).render())
        assert offline == OFFLINE_AUTH_MESSAGE
        assert len(app.screen.query(Input)) == 0
        assert len(app.screen.query(Button)) == 0
