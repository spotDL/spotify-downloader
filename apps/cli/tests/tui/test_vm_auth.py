"""``AuthViewModel`` — PAT flow, logout, and the copy-locked offline short-circuit."""

from __future__ import annotations

import pytest
from spotdl_cli.viewmodels.auth import OFFLINE_AUTH_MESSAGE, AuthViewModel
from spotdl_cli.viewmodels.base import LoadState

from .conftest import FakeCredentialStore
from .fakes import FakeSpotdlClient, make_pat, make_session, make_tokens, make_user

ORIGIN = "https://api.example.test"


def test_offline_auth_message_is_copy_locked() -> None:
    # EXACT CONTRACT A literal — do not edit without updating the contract.
    assert OFFLINE_AUTH_MESSAGE == "sign-in needs the community server; it's unavailable offline"


def _vm(
    client: FakeSpotdlClient, creds: FakeCredentialStore, *, can_auth: bool = True
) -> AuthViewModel:
    return AuthViewModel(client, creds, origin=ORIGIN, session=make_session(can_auth=can_auth))


async def test_login_mints_pat_and_stores() -> None:
    client = FakeSpotdlClient()
    client.login_result = make_tokens(user=make_user(email="user@example.com"))
    client.pat_result = make_pat(token="pat-secret")
    client.users_by_token["pat-secret"] = make_user(email="user@example.com")
    creds = FakeCredentialStore()

    result = await _vm(client, creds).login("user@example.com", "hunter2hunter2")

    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.logged_in is True
    assert result.data.email == "user@example.com"
    assert creds.tokens[ORIGIN] == "pat-secret"
    # flow order: login -> create_pat -> me
    names = [call[0] for call in client.calls]
    assert names == ["login_password", "create_pat", "me"]


async def test_register_mints_pat_and_stores() -> None:
    client = FakeSpotdlClient()
    client.register_result = make_tokens(user=make_user(email="new@example.com"))
    client.pat_result = make_pat(token="pat-new")
    client.users_by_token["pat-new"] = make_user(email="new@example.com")
    creds = FakeCredentialStore()

    result = await _vm(client, creds).register("new@example.com", "hunter2hunter2")

    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.logged_in is True
    assert creds.tokens[ORIGIN] == "pat-new"
    assert client.called("register")


async def test_logout_deletes_token() -> None:
    client = FakeSpotdlClient()
    creds = FakeCredentialStore()
    creds.store_token(ORIGIN, "tok", "user@example.com")

    result = await _vm(client, creds).logout()

    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.logged_in is False
    assert ORIGIN not in creds.tokens


async def test_status_logged_in_from_stored_token() -> None:
    client = FakeSpotdlClient()
    creds = FakeCredentialStore()
    creds.store_token(ORIGIN, "tok", "user@example.com")
    client.users_by_token["tok"] = make_user(email="user@example.com")

    result = await _vm(client, creds).status()
    assert result.data is not None
    assert result.data.logged_in is True
    assert result.data.email == "user@example.com"


@pytest.mark.parametrize("action", ["login", "register", "logout", "status"])
async def test_offline_short_circuits_with_exact_message(action: str) -> None:
    client = FakeSpotdlClient()
    creds = FakeCredentialStore()
    vm = _vm(client, creds, can_auth=False)

    if action == "login":
        result = await vm.login("a@b.co", "password12")
    elif action == "register":
        result = await vm.register("a@b.co", "password12")
    elif action == "logout":
        result = await vm.logout()
    else:
        result = await vm.status()

    assert result.state is LoadState.ERROR
    assert result.error is not None
    assert result.error.message == OFFLINE_AUTH_MESSAGE
    assert client.calls == []  # no client call made


async def test_revoke_calls_server_when_token_id_stored() -> None:
    from uuid import uuid4

    client = FakeSpotdlClient()
    creds = FakeCredentialStore()
    creds.store_token(ORIGIN, "spdl_pat_x", "a@b.c")
    creds.token_ids[ORIGIN] = str(uuid4())

    result = await _vm(client, creds).revoke()

    assert result.state is LoadState.READY
    assert result.data is not None and result.data.logged_in is False
    assert client.called("revoke_pat")
    assert creds.get_token(ORIGIN) is None


async def test_revoke_without_token_id_stays_local() -> None:
    client = FakeSpotdlClient()
    creds = FakeCredentialStore()
    creds.store_token(ORIGIN, "spdl_pat_x", "a@b.c")

    result = await _vm(client, creds).revoke()

    assert result.state is LoadState.READY
    assert result.data is not None and result.data.logged_in is False
    assert not client.called("revoke_pat")
    assert creds.get_token(ORIGIN) is None


async def test_revoke_survives_server_failure() -> None:
    from uuid import uuid4

    client = FakeSpotdlClient()
    client.errors["revoke_pat"] = RuntimeError("boom")
    creds = FakeCredentialStore()
    creds.store_token(ORIGIN, "spdl_pat_x", "a@b.c")
    creds.token_ids[ORIGIN] = str(uuid4())

    result = await _vm(client, creds).revoke()

    assert result.state is LoadState.READY
    assert result.data is not None and result.data.logged_in is False
    assert creds.get_token(ORIGIN) is None
