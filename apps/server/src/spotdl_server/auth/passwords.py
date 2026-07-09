"""argon2id password hashing (CONTRACT — spec §6.2).

Passwords are hashed with **argon2id** (argon2-cffi's default variant), the
modern memory-hard KDF chosen over bcrypt for v5 (bcrypt's 72-byte truncation
trap does not apply; the register schema still caps length to bound cost). The
parameters below are pinned explicitly so :func:`needs_rehash` can flag any hash
produced under weaker settings for a transparent upgrade on the next login.

Only the *encoded* string (``$argon2id$v=19$m=65536,t=3,p=4$salt$hash``) is ever
persisted — it self-describes its salt and parameters, so verification needs no
side data. Nothing here touches the DB or FastAPI.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# Pinned argon2id parameters (RFC 9106 low-memory baseline, stated explicitly so
# they are the single source of truth for ``needs_rehash``). argon2id is the
# default ``type`` for ``PasswordHasher``.
_HASHER = PasswordHasher(
    time_cost=3,  # iterations
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash ``password`` with argon2id, returning the encoded hash string.

    The result embeds a fresh random salt, so two calls with the same password
    return different strings.
    """
    return _HASHER.hash(password)


def verify_password(encoded: str, password: str) -> bool:
    """Return whether ``password`` matches the ``encoded`` argon2 hash.

    Returns ``False`` — never raises — for a wrong password
    (:class:`VerifyMismatchError`) or a malformed/foreign hash string
    (:class:`InvalidHashError`), so callers get a clean boolean at the login
    site regardless of stored-hash provenance.
    """
    try:
        return _HASHER.verify(encoded, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(encoded: str) -> bool:
    """Return whether ``encoded`` was produced under weaker-than-current params.

    Called after a successful login so the caller can recompute and persist a
    stronger hash transparently when the pinned parameters are raised.
    """
    return _HASHER.check_needs_rehash(encoded)
