"""Pure auth crypto leaf (spec §6.2 / Plan 6, Task 3).

This package is a **leaf utility** that sits *below* ``services`` in the import
graph: it imports neither FastAPI nor SQLAlchemy, so both ``services`` and the
``api`` auth glue may depend on it without a layering violation. It holds only
pure, DB-free crypto and time primitives:

* :mod:`~spotdl_server.auth.clock` — the injectable ``Clock`` seam (real +
  protocol) that makes every expiry/rotation window deterministic in tests.
* :mod:`~spotdl_server.auth.passwords` — argon2id password hashing.
* :mod:`~spotdl_server.auth.tokens` — HS256 JWT access tokens, opaque rotating
  refresh tokens, and personal access tokens (PATs), plus the ``sha256_hex``
  helper used to store tokens hashed.

Persistence (the ``refresh_tokens`` / ``api_tokens`` rows, rotation/reuse
detection) and HTTP wiring (the auth dependency) live in later tasks; this leaf
only mints, hashes, and verifies.
"""

from spotdl_server.auth.clock import Clock, SystemClock
from spotdl_server.auth.passwords import hash_password, needs_rehash, verify_password
from spotdl_server.auth.tokens import (
    AccessClaims,
    TokenService,
    is_pat,
    new_pat,
    new_refresh_token,
    sha256_hex,
)

__all__ = [
    "AccessClaims",
    "Clock",
    "SystemClock",
    "TokenService",
    "hash_password",
    "is_pat",
    "needs_rehash",
    "new_pat",
    "new_refresh_token",
    "sha256_hex",
    "verify_password",
]
