"""AuthService — email+password accounts with rotating refresh tokens (spec §6.2).

The orchestration seam for ``/api/v1/auth``: it composes the pure crypto in
:mod:`spotdl_server.auth` (password hashing, JWT minting, opaque-token hashing)
with the credential repositories to implement register / login / refresh /
logout / me. Two invariants define its security posture:

* **No user enumeration.** Every login failure — unknown email, wrong password,
  or a disabled account — raises the same :class:`InvalidCredentials`.
* **Rotating, reuse-detecting refresh tokens.** Each refresh spends the presented
  token (stamping ``rotated_at``) and mints a successor in the same family;
  re-presenting a spent/revoked token revokes the *whole family* (a replay of a
  stolen token logs everyone in that lineage out). Access tokens are short-lived
  JWTs that simply expire — there is no blacklist.

Time flows exclusively through the injected :class:`Clock`, so expiry and
rotation are deterministic in tests. Following Plan 5's unit-of-work rule the
service normally **never commits**: it flushes through its repositories and the
caller (the ``get_session`` dependency, or a test's session fixture) owns commit
/ rollback. The one deliberate exception is :meth:`refresh`'s security branches
(reuse detected / expired / owner disabled): those revoke a token or family and
then **raise**, but ``get_session`` rolls back on any exception — so they commit
the revocation before raising, otherwise a stolen-token replay would be rolled
back to life and the rotated successor would keep working. Nothing here imports
FastAPI, and the only ORM type it returns is the ``User`` row named in the
CONTRACT, which the router maps to a response schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.auth.clock import Clock, ensure_utc
from spotdl_server.auth.passwords import hash_password, needs_rehash, verify_password
from spotdl_server.auth.tokens import TokenService, new_refresh_token, sha256_hex
from spotdl_server.db.models import User
from spotdl_server.repositories.tokens import RefreshTokenRepository
from spotdl_server.repositories.users import UserRepository
from spotdl_server.services.errors import (
    AuthRequired,
    EmailTaken,
    InvalidCredentials,
    InvalidToken,
    TokenExpired,
)


def normalize_email(email: str) -> str:
    """Trim then casefold the whole address (email-normalization CONTRACT, v1).

    Does not strip Gmail dots/plus-tags. The result is what is stored in
    ``users.email`` and the form every lookup is keyed on (store-normalized,
    look-up-normalized).
    """
    return email.strip().casefold()


@dataclass(frozen=True)
class TokenPair:
    """A freshly issued access JWT + opaque refresh token, plus the owner row."""

    access_token: str
    refresh_token: str
    user: User


class AuthService:
    """Register, log in, rotate, and revoke email+password sessions."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        token_service: TokenService,
        clock: Clock,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
    ) -> None:
        self._session = session
        self._token_service = token_service
        self._clock = clock
        self._users = users
        self._refresh_tokens = refresh_tokens

    async def register(
        self, *, email: str, password: str, display_name: str | None = None
    ) -> TokenPair:
        """Create an account and issue its first token pair.

        The email is normalized and the password argon2id-hashed before storage.
        A duplicate email surfaces the ``uq_users_email`` violation as
        :class:`EmailTaken` (409). There is deliberately **no email
        verification** in v1 — the account is usable immediately.
        """
        try:
            user = await self._users.create(
                email=normalize_email(email),
                password_hash=hash_password(password),
                display_name=display_name,
            )
        except IntegrityError as exc:
            raise EmailTaken() from exc
        return await self._issue_pair(user)

    async def login(self, *, email: str, password: str) -> TokenPair:
        """Verify credentials and issue a fresh token pair (new refresh family).

        A missing user, a wrong password, or a disabled account all raise the
        identical :class:`InvalidCredentials` (no user enumeration). A stored hash
        produced under weaker params is transparently upgraded on success.
        """
        user = await self._users.get_by_email(normalize_email(email))
        if user is None or user.password_hash is None:
            raise InvalidCredentials()
        if not verify_password(user.password_hash, password):
            raise InvalidCredentials()
        if needs_rehash(user.password_hash):
            await self._users.set_password_hash(user, hash_password(password))
        if not user.is_active:
            raise InvalidCredentials()
        return await self._issue_pair(user)

    async def refresh(self, *, refresh_token: str) -> TokenPair:
        """Rotate a refresh token, detecting reuse of a spent/revoked one.

        State machine (CONTRACT): not found → :class:`InvalidToken`;
        already-rotated **or** revoked → reuse detected, revoke the whole family +
        :class:`InvalidToken`; expired → revoke this row + :class:`TokenExpired`;
        otherwise rotate (spend the presented token, mint a same-family successor)
        and issue a new access JWT.
        """
        now = self._clock.now()
        row = await self._refresh_tokens.get_by_hash(sha256_hex(refresh_token))
        if row is None:
            raise InvalidToken()
        if row.revoked_at is not None or row.rotated_at is not None:
            # A legitimate client never re-presents a spent token — this is reuse.
            await self._refresh_tokens.revoke_family(row.family_id, now=now)
            # Persist the revocation *before* raising: ``get_session`` rolls back on
            # any exception, so without this commit the family (and the rotated
            # successor) would survive a stolen-token replay, defeating eviction.
            await self._session.commit()
            raise InvalidToken()
        if ensure_utc(row.expires_at) <= now:
            await self._refresh_tokens.revoke(row, now=now)
            await self._session.commit()  # survive the error-path rollback (see above)
            raise TokenExpired()

        user = await self._users.get(row.user_id)
        if user is None or not user.is_active:
            # The account was deleted or disabled after this token was issued —
            # kill the family so no successor can be minted for it.
            await self._refresh_tokens.revoke_family(row.family_id, now=now)
            await self._session.commit()  # survive the error-path rollback (see above)
            raise InvalidToken()

        successor = await self._refresh_tokens.create(
            user_id=user.id,
            token_hash=sha256_hex(new_plain := new_refresh_token()),
            family_id=row.family_id,
            expires_at=self._token_service.refresh_expiry(),
        )
        await self._refresh_tokens.mark_rotated(row, replaced_by=successor.id, now=now)
        access = self._token_service.mint_access(user_id=user.id, is_admin=user.is_admin)
        return TokenPair(access_token=access, refresh_token=new_plain, user=user)

    async def logout(self, *, refresh_token: str) -> None:
        """Revoke the presented token's whole family. Idempotent.

        An unknown token (or an already-revoked one) is a silent no-op — logout
        always succeeds so a client can safely retry.
        """
        row = await self._refresh_tokens.get_by_hash(sha256_hex(refresh_token))
        if row is not None:
            await self._refresh_tokens.revoke_family(row.family_id, now=self._clock.now())

    async def get_me(self, user_id: UUID) -> User:
        """Load the profile behind an authenticated context.

        The ``user_id`` comes from an already-verified token/PAT; a vanished row
        means the session outlived its account, so it is treated as no longer
        authenticated (:class:`AuthRequired` → 401).
        """
        user = await self._users.get(user_id)
        if user is None:
            raise AuthRequired()
        return user

    async def _issue_pair(self, user: User) -> TokenPair:
        """Mint an access JWT and open a brand-new refresh family for ``user``."""
        refresh_plain = new_refresh_token()
        await self._refresh_tokens.create(
            user_id=user.id,
            token_hash=sha256_hex(refresh_plain),
            family_id=uuid4(),
            expires_at=self._token_service.refresh_expiry(),
        )
        access = self._token_service.mint_access(user_id=user.id, is_admin=user.is_admin)
        return TokenPair(access_token=access, refresh_token=refresh_plain, user=user)
