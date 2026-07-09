"""Stable API error envelope and exception handlers (spec §10).

The :class:`ErrorEnvelope` shape and the :class:`ErrorCode` vocabulary are a
**contract**: the generated clients in Plan 8 surface these codes as typed
errors, so codes and the envelope's field names must not drift.

Every exception the server can raise is mapped to ``(status, code, detail)`` by
the single table-driven :func:`_status_and_code` function, which is unit-tested
in isolation. :func:`register_exception_handlers` wires three handlers onto the
app: one for the whole :class:`~spotdl_core.providers.SpotdlError` hierarchy, one
for FastAPI/Pydantic request validation, and a catch-all that never leaks the
underlying message.
"""

from __future__ import annotations

import logging
import math
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from spotdl_core.providers import (
    DownloadFailed,
    EntityNotFound,
    NoMatchFound,
    ProviderAuthError,
    ProviderUnavailable,
    RateLimited,
    SpotdlError,
    UnsupportedURL,
)

from spotdl_server.services.errors import (
    AuthRequired,
    EmailTaken,
    Forbidden,
    InvalidCredentials,
    InvalidToken,
    NotAnAudioTarget,
    NotFoundError,
    OAuthEmailRequired,
    TokenExpired,
    TokenNotFound,
    UnsupportedBatchEntity,
)

logger = logging.getLogger("spotdl_server.api")

_GENERIC_INTERNAL_MESSAGE = "An internal server error occurred."


class ErrorCode(StrEnum):
    """The stable vocabulary of machine-readable error codes."""

    UNSUPPORTED_URL = "unsupported_url"
    NOT_FOUND = "not_found"
    NO_MATCH_FOUND = "no_match_found"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_AUTH_ERROR = "provider_auth_error"
    RATE_LIMITED = "rate_limited"
    VALIDATION_ERROR = "validation_error"
    DOWNLOADS_DISABLED = "downloads_disabled"  # defined now; raised in Plan 7
    DOWNLOAD_FAILED = "download_failed"  # defined now; raised in Plan 7
    UNSUPPORTED_ENTITY = "unsupported_entity"  # Plan 7: resolvable kind not batchable
    # Plan 6 community layer (auth / voting / submissions). All eight are declared
    # here (single home); Tasks 6 and 9 raise OAUTH_EMAIL_REQUIRED / NOT_AN_AUDIO_TARGET.
    AUTH_REQUIRED = "authentication_required"
    INVALID_CREDENTIALS = "invalid_credentials"
    INVALID_TOKEN = "invalid_token"
    TOKEN_EXPIRED = "token_expired"
    FORBIDDEN = "forbidden"
    EMAIL_TAKEN = "email_taken"
    OAUTH_EMAIL_REQUIRED = "oauth_email_required"
    NOT_AN_AUDIO_TARGET = "not_an_audio_target"
    INTERNAL_ERROR = "internal_error"


class ErrorEnvelope(BaseModel):
    """The single wire shape for every error response body.

    ``code`` is typed as the closed :class:`ErrorCode` vocabulary (not a bare
    ``str``) so the exported OpenAPI documents the full enum and Plan 8's generated
    clients surface every code as a typed error (spec §10). It still serializes to
    its plain string value (``ErrorCode`` is a :class:`~enum.StrEnum`).
    """

    code: ErrorCode
    message: str
    detail: dict[str, Any] | None = None


# Plan 6 message-only errors → (HTTP status, ErrorCode). Exact-type keyed (none
# of these subclass one another), consulted after the richer provider/entity
# mappings above so a future subclass with its own detail can slot in earlier.
_COMMUNITY_ERROR_MAP: dict[type[Exception], tuple[int, ErrorCode]] = {
    AuthRequired: (401, ErrorCode.AUTH_REQUIRED),
    InvalidCredentials: (401, ErrorCode.INVALID_CREDENTIALS),
    InvalidToken: (401, ErrorCode.INVALID_TOKEN),
    TokenExpired: (401, ErrorCode.TOKEN_EXPIRED),
    Forbidden: (403, ErrorCode.FORBIDDEN),
    TokenNotFound: (404, ErrorCode.NOT_FOUND),
    EmailTaken: (409, ErrorCode.EMAIL_TAKEN),
    OAuthEmailRequired: (400, ErrorCode.OAUTH_EMAIL_REQUIRED),
    NotAnAudioTarget: (400, ErrorCode.NOT_AN_AUDIO_TARGET),
}


def _provider_detail(exc: Any) -> dict[str, Any]:
    provider = getattr(exc, "provider", None)
    return {"provider": provider.value if provider is not None else None}


def _status_and_code(exc: Exception) -> tuple[int, ErrorCode, dict[str, Any] | None]:
    """Map an exception to its ``(HTTP status, ErrorCode, detail)`` per spec §10.

    Order matters: the most specific subclasses are checked first, and
    ``NotFoundError`` (server, rich detail) is checked before core's thinner
    ``EntityNotFound``. Anything unrecognised falls through to a 500 whose detail
    is ``None`` so no internal state leaks.
    """
    if isinstance(exc, UnsupportedURL):
        # Plan 2's ``parse`` raises ``UnsupportedURL(value)`` — the message is
        # the offending input, so it doubles as the detail value.
        return 400, ErrorCode.UNSUPPORTED_URL, {"value": str(exc)}
    if isinstance(exc, NotFoundError):
        return (
            404,
            ErrorCode.NOT_FOUND,
            {"entity_type": exc.entity_type_label, "id": str(exc.entity_id)},
        )
    if isinstance(exc, EntityNotFound):
        return 404, ErrorCode.NOT_FOUND, _provider_detail(exc)
    if isinstance(exc, NoMatchFound):
        return 404, ErrorCode.NO_MATCH_FOUND, None
    if isinstance(exc, UnsupportedBatchEntity):
        return 400, ErrorCode.UNSUPPORTED_ENTITY, {"entity_type": exc.entity_type_value}
    if isinstance(exc, RateLimited):
        return (
            429,
            ErrorCode.RATE_LIMITED,
            {**_provider_detail(exc), "retry_after": exc.retry_after},
        )
    if isinstance(exc, ProviderUnavailable):
        return 502, ErrorCode.PROVIDER_UNAVAILABLE, _provider_detail(exc)
    if isinstance(exc, ProviderAuthError):
        return 502, ErrorCode.PROVIDER_AUTH_ERROR, _provider_detail(exc)
    if isinstance(exc, DownloadFailed):
        # Covers ConversionFailed/MetadataEmbedFailed/AudioFetchFailed/... which
        # all set ``step``. Raised in Plan 7; mapped now to lock the code.
        return 500, ErrorCode.DOWNLOAD_FAILED, {"step": exc.step}
    # Plan 6 community-layer errors: each carries only a (safe) message, so the
    # detail is ``None`` and the message flows straight into the envelope. A flat
    # type→(status, code) table keeps the mapping declarative and one-line-per-row.
    community = _COMMUNITY_ERROR_MAP.get(type(exc))
    if community is not None:
        status, code = community
        return status, code, None
    return 500, ErrorCode.INTERNAL_ERROR, None


def _envelope_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    detail: dict[str, Any] | None,
    *,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    envelope = ErrorEnvelope(code=code, message=message, detail=detail)
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(envelope),
        headers=headers,
    )


async def _spotdl_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, SpotdlError)  # registered only for this hierarchy
    status_code, code, detail = _status_and_code(exc)
    if code is ErrorCode.INTERNAL_ERROR:
        # A SpotdlError with no mapping row (e.g. a bare ProviderError): log the
        # real error, return the generic message so nothing leaks.
        logger.exception("Unmapped SpotdlError surfaced to the API", exc_info=exc)
        return _envelope_response(status_code, code, _GENERIC_INTERNAL_MESSAGE, None)

    headers: dict[str, str] | None = None
    if isinstance(exc, RateLimited) and exc.retry_after is not None:
        # HTTP Retry-After is delta-seconds — a non-negative integer.
        headers = {"Retry-After": str(max(0, math.ceil(exc.retry_after)))}

    return _envelope_response(status_code, code, str(exc) or code.value, detail, headers=headers)


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return _envelope_response(
        422,
        ErrorCode.VALIDATION_ERROR,
        "Request validation failed",
        {"errors": jsonable_encoder(exc.errors())},
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception surfaced to the API", exc_info=exc)
    return _envelope_response(500, ErrorCode.INTERNAL_ERROR, _GENERIC_INTERNAL_MESSAGE, None)


def register_exception_handlers(app: FastAPI) -> None:
    """Install the spotDL error-envelope handlers on ``app``.

    Dispatch is by exception subclass (see :func:`_status_and_code`). FastAPI
    routes an exception to its most specific registered handler, so the three
    registrations below cover the whole surface: the ``SpotdlError`` hierarchy,
    request validation, and everything else.
    """
    app.add_exception_handler(SpotdlError, _spotdl_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
