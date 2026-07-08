"""Shared async HTTP plumbing: client factory and ``request_json``.

This module owns *all* retrying and failure translation for the provider layer.
Providers never see raw :class:`httpx.Response` errors; they call
:func:`request_json` and receive either parsed JSON or one of the typed
exceptions from :mod:`spotdl_core.providers.errors`.

The error-mapping performed by :func:`request_json` is a **contract** relied on
by later plans (Plan 5 maps these exceptions to the stable API error envelope).
Backoff timing and tenacity wiring are implementation details.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from spotdl_core.model import ProviderId
from spotdl_core.providers.errors import (
    EntityNotFound,
    ProviderAuthError,
    ProviderUnavailable,
    RateLimited,
)

__all__ = ["DEFAULT_USER_AGENT", "RETRY_STATUSES", "create_client", "request_json"]

DEFAULT_USER_AGENT = "spotdl/5.0 (+https://github.com/spotDL/spotify-downloader)"

#: Default HTTP status codes that trigger a retry with backoff.
RETRY_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

#: Connect timeout applied to every client (the overall timeout is per-call).
_CONNECT_TIMEOUT = 5.0

#: Backoff bounds for the tenacity retry loop.
_WAIT_MULTIPLIER = 0.5
_WAIT_MAX = 2.0


def create_client(
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    base_url: str = "",
    timeout: float = 15.0,
    headers: Mapping[str, str] | None = None,
    follow_redirects: bool = True,
) -> httpx.AsyncClient:
    """Build a fresh :class:`httpx.AsyncClient` with no shared/global state.

    Each call returns an independent client with a 5s connect timeout, the given
    overall ``timeout`` for the rest of the request lifecycle, and the given
    per-provider ``User-Agent``. Transport-level retries are disabled
    (``retries=0``) so :func:`request_json`'s tenacity loop is the single owner
    of all retrying and the worst-case attempt count is exactly ``retries``.
    """
    merged_headers: dict[str, str] = {"User-Agent": user_agent}
    if headers is not None:
        merged_headers.update(headers)
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(timeout, connect=_CONNECT_TIMEOUT),
        headers=merged_headers,
        follow_redirects=follow_redirects,
        transport=httpx.AsyncHTTPTransport(retries=0),
    )


class _Retryable(Exception):
    """Internal signal that an attempt failed with a retryable HTTP status.

    Carries the status and parsed ``Retry-After`` so the caller can, after the
    tenacity loop exhausts, translate the last failure to the right taxonomy
    error (:class:`RateLimited` for 429, otherwise :class:`ProviderUnavailable`).
    """

    def __init__(self, *, status: int, retry_after: float | None) -> None:
        super().__init__(f"retryable status {status}")
        self.status = status
        self.retry_after = retry_after


def _parse_retry_after(response: httpx.Response) -> float | None:
    """Parse a ``Retry-After`` header as seconds, or ``None`` if absent/invalid.

    Supports both the delta-seconds form (``Retry-After: 120``) and the
    HTTP-date form (``Retry-After: Wed, 21 Oct 2015 07:28:00 GMT``).
    """
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    raw = raw.strip()
    try:
        return float(raw)
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    delta = (when - datetime.now(UTC)).total_seconds()
    return max(delta, 0.0)


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    provider: ProviderId,
    retries: int = 3,
    retry_statuses: frozenset[int] = RETRY_STATUSES,
    expect_ok_body: Callable[[Any], None] | None = None,
    _sleep: Callable[[float], Awaitable[None]] | None = None,
    **kwargs: Any,
) -> Any:
    """Perform an HTTP request with backoff and map failures to the taxonomy.

    Returns the parsed JSON body on success. On failure raises one of
    :class:`EntityNotFound`, :class:`ProviderAuthError`, :class:`RateLimited`,
    or :class:`ProviderUnavailable` per the module contract.

    ``_sleep`` overrides the async sleep used between retries (tests inject a
    no-op to keep the suite fast); it defaults to :func:`asyncio.sleep`.
    """
    sleep_fn: Callable[[float], Awaitable[Any]] = _sleep or asyncio.sleep
    retrying: AsyncRetrying = AsyncRetrying(
        stop=stop_after_attempt(retries),
        wait=wait_exponential(multiplier=_WAIT_MULTIPLIER, max=_WAIT_MAX),
        retry=retry_if_exception_type((_Retryable, httpx.TransportError)),
        sleep=sleep_fn,
        reraise=True,
    )

    async def _attempt() -> Any:
        response = await client.request(method, url, **kwargs)
        status = response.status_code
        if status == 404:
            raise EntityNotFound(provider=provider)
        if status in (401, 403):
            raise ProviderAuthError(provider=provider)
        if status in retry_statuses:
            raise _Retryable(status=status, retry_after=_parse_retry_after(response))
        if not response.is_success:
            raise ProviderUnavailable(provider=provider)
        try:
            body: Any = response.json()
        except ValueError as exc:
            raise ProviderUnavailable(provider=provider) from exc
        if expect_ok_body is not None:
            expect_ok_body(body)
        return body

    try:
        return await retrying(_attempt)
    except _Retryable as exc:
        if exc.status == 429:
            raise RateLimited(provider=provider, retry_after=exc.retry_after) from exc
        raise ProviderUnavailable(provider=provider) from exc
    except httpx.TransportError as exc:
        raise ProviderUnavailable(provider=provider) from exc
