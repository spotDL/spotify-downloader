"""PatService — personal access tokens (PATs) for CLI auth (spec §6.2, CONTRACT).

The orchestration seam for ``/api/v1/auth/tokens``: it mints an opaque
``spdl_pat_`` secret with :func:`~spotdl_server.auth.tokens.new_pat`, stores only
its sha256 digest + a short display prefix through
:class:`~spotdl_server.repositories.tokens.ApiTokenRepository`, and returns the
full secret to the caller **exactly once** (create). Two invariants define its
security posture:

* **Shown once, stored hashed.** The plaintext token never touches the database —
  only ``token_hash`` (for auth lookup) and ``token_prefix`` (for listings). After
  create there is no way to recover the secret; a lost PAT is revoked and replaced.
* **Ownership-checked revoke.** Revocation addresses a token by id *scoped to the
  owner* (:meth:`ApiTokenRepository.get_owned`); a token id the caller does not own
  is indistinguishable from a non-existent one — both raise :class:`TokenNotFound`
  (404) — so one user can never revoke, or even probe for, another's tokens.

Time flows through the injected :class:`~spotdl_server.auth.clock.Clock` so the
``revoked_at`` stamp is deterministic in tests. Following Plan 5's unit-of-work
rule the service **never commits**: it flushes through the repository and the
caller (the ``get_session`` dependency, or a test's session fixture) owns
commit / rollback. Nothing here imports FastAPI, and the only ORM type it returns
is the ``ApiToken`` row named in the CONTRACT, which the router maps to a schema.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.auth.clock import Clock
from spotdl_server.auth.tokens import new_pat, sha256_hex
from spotdl_server.db.models import ApiToken
from spotdl_server.repositories.tokens import ApiTokenRepository
from spotdl_server.services.errors import TokenNotFound


class PatService:
    """Create, list, and revoke a user's personal access tokens."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        clock: Clock,
        api_tokens: ApiTokenRepository,
    ) -> None:
        self._session = session
        self._clock = clock
        self._api_tokens = api_tokens

    async def create(
        self, *, user_id: UUID, name: str, expires_at: datetime | None = None
    ) -> tuple[ApiToken, str]:
        """Mint a PAT for ``user_id`` and return ``(row, full_token)``.

        ``full_token`` is the once-shown ``spdl_pat_`` secret — the router surfaces
        it in the create response and never again. Only its digest and display
        prefix are persisted. ``expires_at`` is an absolute instant (``None`` =
        never expires); the router derives it from the request's optional
        ``expires_in_days`` using the shared clock.
        """
        full, prefix = new_pat()
        row = await self._api_tokens.create(
            user_id=user_id,
            name=name,
            token_prefix=prefix,
            token_hash=sha256_hex(full),
            expires_at=expires_at,
        )
        return row, full

    async def list_for_user(self, user_id: UUID) -> list[ApiToken]:
        """Every PAT owned by ``user_id`` (newest-first, revoked ones included)."""
        return await self._api_tokens.list_for_user(user_id)

    async def revoke(self, *, user_id: UUID, token_id: UUID) -> None:
        """Revoke PAT ``token_id`` owned by ``user_id``; :class:`TokenNotFound` else.

        The lookup is ownership-scoped, so a token id belonging to another user
        (or one that does not exist) raises the same 404 — no cross-user probing.
        Revocation is a ``revoked_at`` stamp, not a delete, so the ``last_used_at``
        audit trail survives.
        """
        row = await self._api_tokens.get_owned(token_id, user_id)
        if row is None:
            raise TokenNotFound()
        await self._api_tokens.revoke(row, now=self._clock.now())
