"""Unit tests for the rate-limit classifier and client-IP extraction (CONTRACT).

``classify`` and ``client_ip`` are pure functions over a Starlette ``Request`` —
no app, no DB — so these tests build lightweight request scopes directly. They
pin the exact tier-selection decision order (spec §6.4) and the exact
proxy-header IP rule (split on ``,``, strip, index 0; fall back to
``request.client.host``).
"""

from __future__ import annotations

import uuid

import jwt
from spotdl_server.ratelimit.tiers import TIERS, Tier, classify, client_ip
from starlette.requests import Request


def _request(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    client: tuple[str, int] | None = ("9.9.9.9", 4321),
) -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": raw_headers,
        "client": client,
    }
    return Request(scope)


def _jwt_for(user_id: uuid.UUID) -> str:
    # Signed with an arbitrary secret: the classifier decodes the ``sub`` claim
    # WITHOUT signature verification (keying only), so any secret works here.
    secret = "unused-signing-secret-only-for-keying-0123456789"
    return jwt.encode({"sub": str(user_id), "type": "access"}, secret, algorithm="HS256")


def test_tier_table_matches_contract() -> None:
    assert TIERS == {
        Tier.ANON_READ: (120, 60),
        Tier.ANON_AUTH: (20, 60),
        Tier.AUTHED_READ: (600, 60),
        Tier.AUTHED_WRITE: (60, 60),
    }


def test_anonymous_get_is_anon_read() -> None:
    tier, key = classify(_request("GET", "/api/v1/config"), authenticated=False)
    assert tier is Tier.ANON_READ
    assert key == "ip:9.9.9.9"


def test_anonymous_post_to_non_auth_path_is_anon_read() -> None:
    # The middleware runs before routing: an anonymous write hits the limiter as
    # anon_read (IP-keyed) and gets its cheap 401 downstream — never authed_write.
    tier, key = classify(
        _request("POST", f"/api/v1/matches/{uuid.uuid4()}/vote"), authenticated=False
    )
    assert tier is Tier.ANON_READ
    assert key == "ip:9.9.9.9"


def test_login_register_refresh_are_anon_auth() -> None:
    for path in (
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    ):
        tier, _ = classify(_request("POST", path), authenticated=False)
        assert tier is Tier.ANON_AUTH, path


def test_oauth_callback_is_anon_auth() -> None:
    tier, _ = classify(_request("GET", "/api/v1/auth/oauth/github/callback"), authenticated=False)
    assert tier is Tier.ANON_AUTH


def test_unverifiable_pat_is_treated_as_anonymous_ip_keyed() -> None:
    # The hot path cannot verify a PAT (needs the DB), so the middleware passes
    # authenticated=False for it. A bare ``spdl_pat_`` prefix must therefore land
    # in the anonymous tier keyed by IP — never an authed tier.
    tier, key = classify(
        _request(
            "POST",
            f"/api/v1/matches/{uuid.uuid4()}/vote",
            headers={"Authorization": "Bearer spdl_pat_abcdef0123456789"},
        ),
        authenticated=False,
    )
    assert tier is Tier.ANON_READ
    assert key == "ip:9.9.9.9"


def test_distinct_pats_from_one_ip_share_a_single_bucket() -> None:
    # Varying the forged PAT per request must NOT mint a fresh bucket: two
    # different PATs from the same IP must derive the same (IP-scoped) key, so an
    # attacker cannot amplify their effective rate by rotating token text.
    _, key_a = classify(
        _request("GET", "/api/v1/config", headers={"Authorization": "Bearer spdl_pat_aaaa"}),
        authenticated=False,
    )
    _, key_b = classify(
        _request("GET", "/api/v1/config", headers={"Authorization": "Bearer spdl_pat_bbbb"}),
        authenticated=False,
    )
    assert key_a == key_b == "ip:9.9.9.9"


def test_user_get_is_authed_read() -> None:
    user_id = uuid.uuid4()
    tier, key = classify(
        _request(
            "GET",
            "/api/v1/config",
            headers={"Authorization": f"Bearer {_jwt_for(user_id)}"},
        ),
        authenticated=True,
    )
    assert tier is Tier.AUTHED_READ
    assert key == f"user:{user_id}"


def test_forged_jwt_not_authenticated_falls_back_to_ip_key() -> None:
    # A JWT the middleware could not verify => authenticated=False => the key must
    # NOT be user-scoped (else distinct forged subs would amplify the IP budget).
    user_id = uuid.uuid4()
    tier, key = classify(
        _request(
            "GET",
            "/api/v1/config",
            headers={"Authorization": f"Bearer {_jwt_for(user_id)}"},
        ),
        authenticated=False,
    )
    assert tier is Tier.ANON_READ
    assert key == "ip:9.9.9.9"


# --------------------------------------------------------------------------
# client_ip: proxy-header rule
# --------------------------------------------------------------------------


def test_client_ip_uses_header_when_present() -> None:
    req = _request("GET", "/", headers={"cf-connecting-ip": "5.6.7.8"})
    assert client_ip(req, "cf-connecting-ip") == "5.6.7.8"


def test_client_ip_takes_first_of_multi_value_forwarded_for() -> None:
    req = _request("GET", "/", headers={"x-forwarded-for": "1.2.3.4, 10.0.0.1"})
    assert client_ip(req, "x-forwarded-for") == "1.2.3.4"


def test_client_ip_falls_back_when_header_unset() -> None:
    req = _request("GET", "/", headers={"x-forwarded-for": "1.2.3.4"})
    # header name not configured -> use the socket peer
    assert client_ip(req, None) == "9.9.9.9"


def test_client_ip_falls_back_when_header_absent() -> None:
    req = _request("GET", "/")
    assert client_ip(req, "x-forwarded-for") == "9.9.9.9"


def test_client_ip_falls_back_when_header_empty() -> None:
    req = _request("GET", "/", headers={"x-forwarded-for": "   "})
    assert client_ip(req, "x-forwarded-for") == "9.9.9.9"
