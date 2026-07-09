"""Tests for :mod:`spotdl_server.auth.passwords` (argon2id, CONTRACT).

Pure, offline, and fast-ish: argon2id is deliberately memory-hard, so these
exercise correctness (round-trip, mismatch, salting, encoding format) and the
``needs_rehash`` upgrade seam rather than raw throughput.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from spotdl_server.auth.passwords import (
    hash_password,
    needs_rehash,
    verify_password,
)


def test_hash_and_verify_roundtrip() -> None:
    encoded = hash_password("correct horse battery staple")
    assert verify_password(encoded, "correct horse battery staple") is True


def test_verify_rejects_wrong_password() -> None:
    encoded = hash_password("correct horse battery staple")
    assert verify_password(encoded, "Tr0ub4dor&3") is False


def test_hash_is_argon2id() -> None:
    encoded = hash_password("hunter2hunter2")
    assert encoded.startswith("$argon2id$")


def test_needs_rehash_false_for_current_params() -> None:
    encoded = hash_password("current-params-please")
    assert needs_rehash(encoded) is False


def test_needs_rehash_true_after_param_change() -> None:
    # A hash produced by a deliberately weaker hasher must be flagged for the
    # transparent-upgrade-on-login path.
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
    encoded = weak.hash("upgrade-me")
    assert needs_rehash(encoded) is True


def test_hashes_are_salted() -> None:
    a = hash_password("same-password")
    b = hash_password("same-password")
    assert a != b


def test_verify_returns_false_on_garbage_hash() -> None:
    # A malformed/foreign encoded string must never raise out of verify.
    assert verify_password("not-a-real-argon2-hash", "whatever") is False
