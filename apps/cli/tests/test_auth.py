"""``spotdl auth login|logout|status`` — PAT flow against the community server.

CONTRACT C rule 5: auth is **remote-only** and NEVER falls back to the embedded
(authless) server. ``--offline`` and an unreachable server fail fast with pinned
copy + exit codes; no embedded server is booted (no SQLite file, no fallback
warning).
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from spotdl_cli import config as cfgmod
from spotdl_cli.commands.auth import auth_app
from spotdl_cli.config import get_token, store_token
from typer.testing import CliRunner

runner = CliRunner()

BASE = "https://api.test"
ORIGIN = "https://api.test"

USER_JSON = {
    "created_at": "2026-01-01T00:00:00Z",
    "email": "user@example.com",
    "id": "22222222-2222-2222-2222-222222222222",
    "is_admin": False,
    "display_name": "User",
}
TOKEN_JSON = {
    "access_token": "jwt-access",
    "expires_in": 3600,
    "refresh_token": "jwt-refresh",
    "user": USER_JSON,
    "token_type": "bearer",
}
PAT_ID = "33333333-3333-3333-3333-333333333333"
PAT_SECRET = "spdl_pat_secretvalue1234567890"
PAT_JSON = {
    "created_at": "2026-01-01T00:00:00Z",
    "id": PAT_ID,
    "name": "spotdl-cli host",
    "token": PAT_SECRET,
    "token_prefix": "spdl_pat_secr",
}

OFFLINE_COPY = "`spotdl auth` needs the community server and can't run with --offline."


@pytest.fixture
def cfg_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cdir = tmp_path / "config"
    ddir = tmp_path / "data"
    monkeypatch.setattr(cfgmod.platformdirs, "user_config_dir", lambda *a, **k: str(cdir))
    monkeypatch.setattr(cfgmod.platformdirs, "user_data_dir", lambda *a, **k: str(ddir))
    return tmp_path


def _no_embedded(root: Path) -> bool:
    """No embedded SQLite anywhere under the throwaway home (rule 5)."""
    return list(root.glob("**/*.db")) == []


# ---- login: password flow mints + stores a PAT -----------------------------


def test_login_password_mints_and_stores_pat(cfg_home: Path) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        router.post("/api/v1/auth/login").mock(return_value=httpx.Response(200, json=TOKEN_JSON))
        pat_route = router.post("/api/v1/auth/tokens").mock(
            return_value=httpx.Response(201, json=PAT_JSON)
        )
        result = runner.invoke(
            auth_app,
            ["login", "--api-url", BASE],
            input="user@example.com\nsecret\n",
        )

    assert result.exit_code == 0, result.output
    # The PAT was created with a hostname-tagged name.
    assert pat_route.called
    body = pat_route.calls.last.request.content.decode()
    assert "spotdl-cli " in body
    # Stored for the server origin, with the token id recorded for logout revoke.
    cred = get_token(ORIGIN)
    assert cred is not None
    assert cred.token == PAT_SECRET
    assert cred.email == "user@example.com"
    assert cred.token_id == PAT_ID
    # Masked confirmation: email shown, raw secret NOT shown in full.
    assert "user@example.com" in result.output
    assert PAT_SECRET not in result.output
    assert "…" in result.output


def test_login_with_token_validates_via_me(cfg_home: Path) -> None:
    pasted = "spdl_pat_pasted1234567890abcd"
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        me_route = router.get("/api/v1/auth/me").mock(
            return_value=httpx.Response(200, json=USER_JSON)
        )
        result = runner.invoke(auth_app, ["login", "--token", pasted, "--api-url", BASE])

    assert result.exit_code == 0, result.output
    assert me_route.called
    # The pasted PAT was sent as the Bearer credential for validation.
    assert me_route.calls.last.request.headers["authorization"] == f"Bearer {pasted}"
    cred = get_token(ORIGIN)
    assert cred is not None
    assert cred.token == pasted
    assert cred.email == "user@example.com"


def test_login_with_invalid_token_reports_auth_error(cfg_home: Path) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        router.get("/api/v1/auth/me").mock(
            return_value=httpx.Response(401, json={"code": "invalid_token", "message": "nope"})
        )
        result = runner.invoke(auth_app, ["login", "--token", "spdl_pat_bad", "--api-url", BASE])

    assert result.exit_code == 4  # AUTH
    assert get_token(ORIGIN) is None


# ---- login: remote-only fail-fast (CONTRACT C rule 5) ----------------------


def test_login_offline_fails_usage_no_embedded(cfg_home: Path) -> None:
    result = runner.invoke(auth_app, ["login", "--offline", "--api-url", BASE])
    assert result.exit_code == 2  # USAGE
    assert OFFLINE_COPY in result.output
    assert "warning:" not in result.output
    assert _no_embedded(cfg_home)
    assert get_token(ORIGIN) is None


def test_login_unreachable_fails_transport_no_embedded(cfg_home: Path) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/health").mock(side_effect=httpx.ConnectError("boom"))
        result = runner.invoke(auth_app, ["login", "--api-url", BASE])

    assert result.exit_code == 3  # TRANSPORT
    assert f"can't reach the spotDL server at {BASE}" in result.output
    assert "`spotdl auth` needs it" in result.output
    assert "warning:" not in result.output  # no embedded-fallback warning
    assert _no_embedded(cfg_home)


# ---- status -----------------------------------------------------------------


def test_status_logged_in_prints_email(cfg_home: Path) -> None:
    store_token(ORIGIN, "spdl_pat_stored", email="user@example.com", token_id=PAT_ID)
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        router.get("/api/v1/auth/me").mock(return_value=httpx.Response(200, json=USER_JSON))
        result = runner.invoke(auth_app, ["status", "--api-url", BASE])

    assert result.exit_code == 0, result.output
    assert "user@example.com" in result.output
    assert BASE in result.output


def test_status_not_logged_in_when_no_token(cfg_home: Path) -> None:
    result = runner.invoke(auth_app, ["status", "--api-url", BASE])
    assert result.exit_code == 0
    assert "not logged in" in result.output


def test_status_401_prints_not_logged_in_exit_ok(cfg_home: Path) -> None:
    store_token(ORIGIN, "spdl_pat_stale", email="user@example.com")
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        router.get("/api/v1/auth/me").mock(
            return_value=httpx.Response(401, json={"code": "invalid_token", "message": "stale"})
        )
        result = runner.invoke(auth_app, ["status", "--api-url", BASE])

    assert result.exit_code == 0
    assert "not logged in" in result.output


# ---- logout -----------------------------------------------------------------


def test_logout_deletes_token_and_revokes(cfg_home: Path) -> None:
    store_token(ORIGIN, "spdl_pat_stored", email="user@example.com", token_id=PAT_ID)
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        del_route = router.delete(f"/api/v1/auth/tokens/{PAT_ID}").mock(
            return_value=httpx.Response(204)
        )
        result = runner.invoke(auth_app, ["logout", "--api-url", BASE])

    assert result.exit_code == 0, result.output
    assert del_route.called
    assert get_token(ORIGIN) is None


def test_logout_is_best_effort_on_revoke_failure(cfg_home: Path) -> None:
    store_token(ORIGIN, "spdl_pat_stored", email="user@example.com", token_id=PAT_ID)
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.delete(f"/api/v1/auth/tokens/{PAT_ID}").mock(side_effect=httpx.ConnectError("x"))
        result = runner.invoke(auth_app, ["logout", "--api-url", BASE])

    assert result.exit_code == 0, result.output
    assert get_token(ORIGIN) is None  # local logout still happened


def test_logout_without_token_id_skips_remote(cfg_home: Path) -> None:
    store_token(ORIGIN, "spdl_pat_pasted", email="user@example.com")  # no token_id
    with respx.mock(base_url=BASE, assert_all_called=True) as router:
        # No routes registered ⇒ any network call would raise; assert_all_called
        # with an empty router means "nothing expected".
        _ = router
        result = runner.invoke(auth_app, ["logout", "--api-url", BASE])

    assert result.exit_code == 0, result.output
    assert get_token(ORIGIN) is None


def test_logout_when_not_logged_in(cfg_home: Path) -> None:
    result = runner.invoke(auth_app, ["logout", "--api-url", BASE])
    assert result.exit_code == 0
    assert "not logged in" in result.output


def test_rule5_copy_matches_fallback_constants() -> None:
    """auth.py's inline rule-5 copy must render byte-identically to fallback.py's.

    Two sources exist deliberately (auth avoids from_config so no embedded SQLite
    side effects); this lock makes any divergence fail loudly.
    """
    from spotdl_cli import fallback
    from spotdl_cli.commands import auth as auth_cmd

    assert "error: " + auth_cmd._OFFLINE_COPY == fallback.OFFLINE_AUTH_ERROR
    rendered = "error: " + auth_cmd._unreachable_copy("https://api.spotdl.dev", "boom")
    assert rendered == fallback.UNREACHABLE_AUTH_ERROR.format(
        api_url="https://api.spotdl.dev", reason="boom"
    )
