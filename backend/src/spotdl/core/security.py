"""Security utilities for authentication and authorization."""

from __future__ import annotations

import hashlib
import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from spotdl.config import get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TokenBlacklistCache:
    """
    In-memory token blacklist cache with automatic expiry cleanup.

    This serves as a fast cache layer. The database is the source of truth
    for persistence across restarts.
    """

    def __init__(self) -> None:
        self._blacklist: dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._initialized = False

    def add(self, token: str, expires_at: datetime) -> None:
        """Add a token to the cache."""
        with self._lock:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            self._blacklist[token_hash] = expires_at
            self._cleanup()

    def add_by_hash(self, token_hash: str, expires_at: datetime) -> None:
        """Add a token to the cache by its hash (for loading from database)."""
        with self._lock:
            self._blacklist[token_hash] = expires_at

    def is_blacklisted(self, token: str) -> bool:
        """Check if a token is in the cache."""
        with self._lock:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            if token_hash in self._blacklist:
                # Check if still valid (not expired)
                if self._blacklist[token_hash] > datetime.now(UTC):
                    return True
                # Token has expired, remove from cache
                del self._blacklist[token_hash]
            return False

    def is_blacklisted_by_hash(self, token_hash: str) -> bool:
        """Check if a token hash is in the cache."""
        with self._lock:
            if token_hash in self._blacklist:
                if self._blacklist[token_hash] > datetime.now(UTC):
                    return True
                del self._blacklist[token_hash]
            return False

    def _cleanup(self) -> None:
        """Remove expired tokens from the cache."""
        now = datetime.now(UTC)
        expired = [h for h, exp in self._blacklist.items() if exp <= now]
        for token_hash in expired:
            del self._blacklist[token_hash]
        if expired:
            logger.debug("Cleaned up %d expired tokens from cache", len(expired))

    def clear(self) -> None:
        """Clear all tokens from the cache."""
        with self._lock:
            self._blacklist.clear()
            self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the cache has been initialized from database."""
        return self._initialized

    def mark_initialized(self) -> None:
        """Mark the cache as initialized."""
        self._initialized = True

    def count(self) -> int:
        """Get the number of tokens in the cache."""
        with self._lock:
            return len(self._blacklist)


# Global token blacklist cache instance
_token_cache = TokenBlacklistCache()


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    exp: datetime
    type: str  # "access" or "refresh"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(user_id: str) -> str:
    """Create an access token for a user."""
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode: dict[str, Any] = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


def create_refresh_token(user_id: str) -> str:
    """Create a refresh token for a user."""
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    to_encode: dict[str, Any] = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


def decode_token_payload(token: str) -> TokenPayload | None:
    """
    Decode a JWT token without blacklist check.

    Args:
        token: JWT token string

    Returns:
        TokenPayload if valid, None otherwise
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
        )
        return TokenPayload(**payload)
    except JWTError:
        return None


def decode_token(token: str) -> TokenPayload | None:
    """
    Decode and validate a JWT token (sync version with cache check only).

    For full blacklist checking with database, use decode_token_async.

    Args:
        token: JWT token string

    Returns:
        TokenPayload if valid and not in cache blacklist, None otherwise
    """
    # Check cache first (fast path)
    if _token_cache.is_blacklisted(token):
        logger.debug("Token found in blacklist cache")
        return None

    return decode_token_payload(token)


async def is_token_blacklisted(token: str, db: AsyncSession) -> bool:
    """
    Check if a token is blacklisted (checks cache and database).

    The cache is populated from the database on startup. If for some reason
    the cache isn't initialized, we fall back to database check and populate
    the cache as we go.

    Args:
        token: JWT token to check
        db: Database session

    Returns:
        True if blacklisted, False otherwise
    """
    # Check cache first (fast path) - only trust cache if initialized
    if _token_cache.is_initialized and _token_cache.is_blacklisted(token):
        return True

    # If cache isn't initialized or token not in cache, check database
    from spotdl.db.repositories.token_blacklist import TokenBlacklistRepository

    repo = TokenBlacklistRepository(db)
    is_blacklisted = await repo.is_blacklisted(token)

    # If found in database, add to cache for future fast lookups
    if is_blacklisted:
        payload = decode_token_payload(token)
        if payload:
            _token_cache.add(token, payload.exp)

    return is_blacklisted


async def blacklist_token(
    token: str,
    db: AsyncSession,
    reason: str = "logout",
) -> bool:
    """
    Add a token to the blacklist (both cache and database).

    Args:
        token: JWT token to blacklist
        db: Database session
        reason: Reason for blacklisting

    Returns:
        True if successfully blacklisted, False if token is invalid
    """
    # Decode to get expiry
    payload = decode_token_payload(token)
    if payload is None:
        return False

    # Add to cache
    _token_cache.add(token, payload.exp)

    # Add to database
    from spotdl.db.repositories.token_blacklist import TokenBlacklistRepository

    repo = TokenBlacklistRepository(db)
    await repo.add(token, payload.exp, reason)
    await db.commit()

    logger.info("Token blacklisted (reason: %s), expires at %s", reason, payload.exp)
    return True


async def cleanup_expired_tokens(db: AsyncSession) -> int:
    """
    Remove expired tokens from the database.

    Should be called periodically (e.g., daily) to clean up old tokens.

    Args:
        db: Database session

    Returns:
        Number of tokens removed
    """
    from spotdl.db.repositories.token_blacklist import TokenBlacklistRepository

    repo = TokenBlacklistRepository(db)
    count = await repo.cleanup_expired()
    await db.commit()

    if count > 0:
        logger.info("Cleaned up %d expired tokens from database", count)

    return count


async def initialize_token_blacklist(db: AsyncSession) -> int:
    """
    Initialize the token blacklist cache from the database.

    This should be called on application startup to ensure the cache
    is populated with all active blacklisted tokens.

    Args:
        db: Database session

    Returns:
        Number of tokens loaded into cache
    """
    if _token_cache.is_initialized:
        logger.debug("Token blacklist cache already initialized")
        return _token_cache.count()

    from spotdl.db.repositories.token_blacklist import TokenBlacklistRepository

    repo = TokenBlacklistRepository(db)

    # First, clean up expired tokens
    expired_count = await repo.cleanup_expired()
    if expired_count > 0:
        logger.info("Cleaned up %d expired tokens during initialization", expired_count)

    # Load all active tokens into cache
    active_tokens = await repo.get_all_active()

    for token_hash, expires_at in active_tokens:
        _token_cache.add_by_hash(token_hash, expires_at)

    _token_cache.mark_initialized()

    logger.info(
        "Token blacklist cache initialized with %d active tokens",
        len(active_tokens),
    )

    return len(active_tokens)
