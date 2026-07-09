"""Tests for :mod:`spotdl_server.auth.tokens` (JWT / refresh / PAT, CONTRACT).

Fully offline and deterministic: expiry and rotation windows are driven through
the injected :class:`FakeClock`, so nothing here sleeps or reads the wall clock.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from uuid import uuid4

import jwt
import pytest
from spotdl_server.auth.tokens import (
    AccessClaims,
    TokenService,
    is_pat,
    new_pat,
    new_refresh_token,
    sha256_hex,
)

from tests.conftest import FakeClock

_SECRET = "test-signing-secret-not-from-prod"


@pytest.fixture
def service(clock: FakeClock) -> TokenService:
    return TokenService(secret=_SECRET, clock=clock)


# --------------------------------------------------------------------------- #
# JWT access tokens
# --------------------------------------------------------------------------- #
def test_mint_and_verify_access(service: TokenService) -> None:
    user_id = uuid4()
    token = service.mint_access(user_id=user_id, is_admin=True)
    claims = service.verify_access(token)
    assert claims == AccessClaims(user_id=user_id, is_admin=True)


def test_mint_access_claims_match_contract(clock: FakeClock, service: TokenService) -> None:
    user_id = uuid4()
    token = service.mint_access(user_id=user_id, is_admin=False)
    # ``verify_exp`` off because the fake clock is anchored far from the real
    # wall clock PyJWT would otherwise compare against — we assert exp directly.
    payload = jwt.decode(token, _SECRET, algorithms=["HS256"], options={"verify_exp": False})
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert payload["is_admin"] is False
    assert payload["iat"] == int(clock.now().timestamp())
    assert payload["exp"] == int((clock.now() + timedelta(seconds=900)).timestamp())


def test_verify_expired_returns_none(clock: FakeClock, service: TokenService) -> None:
    token = service.mint_access(user_id=uuid4(), is_admin=False)
    clock.advance(901)  # past the 900s access TTL
    assert service.verify_access(token) is None


def test_verify_at_expiry_boundary_still_valid(clock: FakeClock, service: TokenService) -> None:
    token = service.mint_access(user_id=uuid4(), is_admin=False)
    clock.advance(899)
    assert service.verify_access(token) is not None


def test_verify_tampered_signature_returns_none(service: TokenService) -> None:
    token = service.mint_access(user_id=uuid4(), is_admin=False)
    header, payload, _sig = token.split(".")
    tampered = f"{header}.{payload}.AAAAtamperedsignatureAAAA"
    assert service.verify_access(tampered) is None


def test_verify_wrong_type_returns_none(clock: FakeClock) -> None:
    # A hand-crafted, correctly-signed JWT whose ``type`` is not "access" must
    # be rejected — access verification must not accept a refresh-typed token.
    now = int(clock.now().timestamp())
    forged = jwt.encode(
        {
            "sub": str(uuid4()),
            "iat": now,
            "exp": now + 900,
            "type": "refresh",
            "is_admin": False,
        },
        _SECRET,
        algorithm="HS256",
    )
    service = TokenService(secret=_SECRET, clock=clock)
    assert service.verify_access(forged) is None


def test_verify_missing_type_returns_none(clock: FakeClock) -> None:
    now = int(clock.now().timestamp())
    forged = jwt.encode(
        {"sub": str(uuid4()), "iat": now, "exp": now + 900, "is_admin": False},
        _SECRET,
        algorithm="HS256",
    )
    service = TokenService(secret=_SECRET, clock=clock)
    assert service.verify_access(forged) is None


def test_verify_bad_secret_returns_none(clock: FakeClock) -> None:
    minted = TokenService(secret=_SECRET, clock=clock).mint_access(user_id=uuid4(), is_admin=False)
    other = TokenService(secret="a-different-secret-also-long-enough-to-be-safe", clock=clock)
    assert other.verify_access(minted) is None


def test_verify_garbage_returns_none(service: TokenService) -> None:
    assert service.verify_access("not.a.jwt") is None
    assert service.verify_access("") is None


def test_custom_access_ttl_respected(clock: FakeClock) -> None:
    service = TokenService(secret=_SECRET, clock=clock, access_ttl_s=60)
    token = service.mint_access(user_id=uuid4(), is_admin=False)
    clock.advance(61)
    assert service.verify_access(token) is None


# --------------------------------------------------------------------------- #
# Refresh token expiry
# --------------------------------------------------------------------------- #
def test_refresh_expiry_uses_clock(clock: FakeClock, service: TokenService) -> None:
    assert service.refresh_expiry() == clock.now() + timedelta(seconds=2_592_000)


def test_refresh_expiry_custom_ttl(clock: FakeClock) -> None:
    service = TokenService(secret=_SECRET, clock=clock, refresh_ttl_s=3600)
    assert service.refresh_expiry() == clock.now() + timedelta(seconds=3600)


def test_new_refresh_token_is_opaque_and_unique() -> None:
    a = new_refresh_token()
    b = new_refresh_token()
    assert a != b
    assert not is_pat(a)
    assert "." not in a  # not a JWT


# --------------------------------------------------------------------------- #
# PATs and hashing helpers
# --------------------------------------------------------------------------- #
def test_new_pat_prefix_and_shape() -> None:
    full, prefix = new_pat()
    assert is_pat(full) is True
    assert prefix.startswith("spdl_pat_")
    assert full.startswith(prefix)
    assert full != prefix
    # prefix = "spdl_pat_" + first 6 chars of the url-safe secret
    secret = full[len("spdl_pat_") :]
    assert prefix == "spdl_pat_" + secret[:6]
    assert len(prefix) == len("spdl_pat_") + 6


def test_new_pat_is_unique() -> None:
    assert new_pat()[0] != new_pat()[0]


def test_is_pat_discriminates() -> None:
    assert is_pat("spdl_pat_abcdef") is True
    assert is_pat("eyJhbGciOiJIUzI1NiJ9.payload.sig") is False
    assert is_pat("") is False


def test_sha256_hex_stable() -> None:
    token = "spdl_pat_deadbeefcafebabe"
    digest = sha256_hex(token)
    assert digest == sha256_hex(token)
    assert digest == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert len(digest) == 64
    assert digest != sha256_hex(token + "x")
