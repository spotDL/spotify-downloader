"""``AppStateViewModel.load`` → ``SessionSnapshot`` feature gating (CONTRACT F)."""

from __future__ import annotations

from spotdl_cli.viewmodels.app_state import AppStateViewModel
from spotdl_cli.viewmodels.base import LoadState

from .conftest import FakeCredentialStore
from .fakes import FakeSpotdlClient, make_config, make_features, make_user

ORIGIN = "https://api.example.test"
LABEL = "remote · api.example.test"


def _vm(client: FakeSpotdlClient, creds: FakeCredentialStore) -> AppStateViewModel:
    return AppStateViewModel(client, creds, server_origin=ORIGIN, transport_label=LABEL)


async def test_all_flags_true_when_admin_logged_in() -> None:
    client = FakeSpotdlClient(
        config=make_config(features=make_features(auth=True, voting=True)),
        download_config=make_config(features=make_features(downloads=True)),
    )
    creds = FakeCredentialStore()
    creds.store_token(ORIGIN, "tok", "admin@example.com")
    client.users_by_token["tok"] = make_user(email="admin@example.com", is_admin=True)

    result = await _vm(client, creds).load()

    assert result.state is LoadState.READY
    snap = result.data
    assert snap is not None
    assert snap.can_auth is True
    assert snap.can_vote is True
    assert snap.can_download is True
    assert snap.is_admin is True
    assert snap.user_email == "admin@example.com"
    assert snap.mode == "self_host"
    assert snap.matcher_version == "m1"
    assert snap.transport_label == LABEL
    assert snap.server_origin == ORIGIN
    assert snap.degraded is False


async def test_offline_hosted_flags_false() -> None:
    client = FakeSpotdlClient(
        config=make_config(mode="hosted", features=make_features(auth=False, voting=False)),
        download_config=make_config(features=make_features(downloads=False)),
    )
    creds = FakeCredentialStore()  # no token → guest

    result = await _vm(client, creds).load()

    snap = result.data
    assert snap is not None
    assert snap.can_auth is False
    assert snap.can_vote is False
    assert snap.can_download is False
    assert snap.is_admin is False
    assert snap.user_email is None
    assert snap.mode == "hosted"


async def test_stored_token_but_auth_disabled_stays_guest() -> None:
    client = FakeSpotdlClient(
        config=make_config(features=make_features(auth=False)),
        download_config=make_config(),
    )
    creds = FakeCredentialStore()
    creds.store_token(ORIGIN, "tok", "user@example.com")
    client.users_by_token["tok"] = make_user(is_admin=True)

    snap = (await _vm(client, creds).load()).data
    assert snap is not None
    assert snap.is_admin is False
    assert snap.user_email is None
    assert not client.called("me")  # short-circuits, no wasted call


async def test_rejected_token_degrades_to_guest() -> None:
    client = FakeSpotdlClient(
        config=make_config(features=make_features(auth=True)),
        download_config=make_config(),
    )
    creds = FakeCredentialStore()
    creds.store_token(ORIGIN, "stale", "user@example.com")
    # no users_by_token entry → me() raises invalid_token

    snap = (await _vm(client, creds).load()).data
    assert snap is not None
    assert snap.is_admin is False
    assert snap.user_email is None


async def test_config_failure_yields_failed_snapshot() -> None:
    from spotdl_cli._generated.api.models.error_code import ErrorCode
    from spotdl_cli.errors import ApiError

    client = FakeSpotdlClient()
    client.errors["config"] = ApiError(ErrorCode.INTERNAL_ERROR, message="boom")
    result = await _vm(client, FakeCredentialStore()).load()
    assert result.state is LoadState.ERROR
    assert result.error is not None
