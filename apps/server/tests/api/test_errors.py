"""Tests for the stable error envelope and exception handlers (spec §10).

The ``ErrorEnvelope`` shape and the error-code vocabulary are CONTRACT — the
generated clients in Plan 8 surface these codes as typed errors. These tests
exercise both the table-driven ``_status_and_code`` mapper in isolation and the
end-to-end handler behaviour via a throwaway FastAPI app.
"""

import uuid

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel, Field
from spotdl_core.model import EntityType, ProviderId
from spotdl_core.providers import (
    ConversionFailed,
    DownloadFailed,
    EntityNotFound,
    MetadataEmbedFailed,
    NoMatchFound,
    ProviderAuthError,
    ProviderError,
    ProviderUnavailable,
    RateLimited,
    SpotdlError,
    UnsupportedURL,
)
from spotdl_server.api.errors import (
    ErrorCode,
    ErrorEnvelope,
    _status_and_code,
    register_exception_handlers,
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
)

# --------------------------------------------------------------------------
# NotFoundError (server-side rich 404)
# --------------------------------------------------------------------------


def test_not_found_error_carries_entity_type_and_id() -> None:
    eid = uuid.uuid4()
    exc = NotFoundError(entity_type=EntityType.TRACK, entity_id=eid)
    assert exc.entity_type is EntityType.TRACK
    assert exc.entity_id == eid
    assert str(eid) in str(exc)
    assert isinstance(exc, SpotdlError)  # dispatched by the SpotdlError handler


# --------------------------------------------------------------------------
# _status_and_code — one assertion per CONTRACT table row, each exception
# constructed exactly as Plan 2 / services/errors.py define it.
# --------------------------------------------------------------------------


def test_map_unsupported_url() -> None:
    status, code, detail = _status_and_code(UnsupportedURL("not:a:url"))
    assert status == 400
    assert code is ErrorCode.UNSUPPORTED_URL
    assert detail == {"value": "not:a:url"}


def test_map_not_found_error() -> None:
    eid = uuid.uuid4()
    status, code, detail = _status_and_code(
        NotFoundError(entity_type=EntityType.ALBUM, entity_id=eid)
    )
    assert status == 404
    assert code is ErrorCode.NOT_FOUND
    assert detail == {"entity_type": "album", "id": str(eid)}


def test_map_entity_not_found_with_provider() -> None:
    status, code, detail = _status_and_code(EntityNotFound("gone", provider=ProviderId.SPOTIFY))
    assert status == 404
    assert code is ErrorCode.NOT_FOUND
    assert detail == {"provider": "spotify"}


def test_map_entity_not_found_without_provider() -> None:
    _, code, detail = _status_and_code(EntityNotFound("gone"))
    assert code is ErrorCode.NOT_FOUND
    assert detail == {"provider": None}


def test_map_no_match_found() -> None:
    status, code, detail = _status_and_code(NoMatchFound("nothing viable"))
    assert status == 404
    assert code is ErrorCode.NO_MATCH_FOUND
    assert detail is None


def test_map_provider_unavailable() -> None:
    status, code, detail = _status_and_code(ProviderUnavailable("down", provider=ProviderId.DEEZER))
    assert status == 502
    assert code is ErrorCode.PROVIDER_UNAVAILABLE
    assert detail == {"provider": "deezer"}


def test_map_provider_auth_error() -> None:
    status, code, detail = _status_and_code(
        ProviderAuthError("bad token", provider=ProviderId.SPOTIFY)
    )
    assert status == 502
    assert code is ErrorCode.PROVIDER_AUTH_ERROR
    assert detail == {"provider": "spotify"}


def test_map_rate_limited() -> None:
    status, code, detail = _status_and_code(
        RateLimited("slow down", provider=ProviderId.GENIUS, retry_after=30.0)
    )
    assert status == 429
    assert code is ErrorCode.RATE_LIMITED
    assert detail == {"provider": "genius", "retry_after": 30.0}


def test_map_rate_limited_without_retry_after() -> None:
    _, code, detail = _status_and_code(RateLimited(provider=ProviderId.GENIUS))
    assert code is ErrorCode.RATE_LIMITED
    assert detail == {"provider": "genius", "retry_after": None}


def test_map_download_failed() -> None:
    status, code, detail = _status_and_code(DownloadFailed("boom", step="fetch"))
    assert status == 500
    assert code is ErrorCode.DOWNLOAD_FAILED
    assert detail == {"step": "fetch"}


def test_map_download_failed_subclasses_use_their_step() -> None:
    for exc, step in ((ConversionFailed(), "convert"), (MetadataEmbedFailed(), "embed")):
        status, code, detail = _status_and_code(exc)
        assert status == 500
        assert code is ErrorCode.DOWNLOAD_FAILED
        assert detail == {"step": step}


def test_map_bare_provider_error_falls_through_to_internal() -> None:
    status, code, detail = _status_and_code(ProviderError("weird"))
    assert status == 500
    assert code is ErrorCode.INTERNAL_ERROR
    assert detail is None


def test_map_arbitrary_exception_is_internal() -> None:
    status, code, detail = _status_and_code(ValueError("nope"))
    assert status == 500
    assert code is ErrorCode.INTERNAL_ERROR
    assert detail is None


def test_not_found_error_beats_entity_not_found_dispatch() -> None:
    """NotFoundError must be matched before EntityNotFound so the richer
    server-side detail (entity_type + id) wins over the provider-shaped one."""
    eid = uuid.uuid4()
    _, code, detail = _status_and_code(NotFoundError(entity_type=EntityType.ARTIST, entity_id=eid))
    assert code is ErrorCode.NOT_FOUND
    assert detail == {"entity_type": "artist", "id": str(eid)}
    assert "provider" not in detail


# --------------------------------------------------------------------------
# Plan 6 auth/community error codes — one assertion per CONTRACT table row,
# each exception constructed exactly as ``services/errors.py`` defines it.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc, status, code",
    [
        (AuthRequired(), 401, ErrorCode.AUTH_REQUIRED),
        (InvalidCredentials(), 401, ErrorCode.INVALID_CREDENTIALS),
        (InvalidToken(), 401, ErrorCode.INVALID_TOKEN),
        (TokenExpired(), 401, ErrorCode.TOKEN_EXPIRED),
        (Forbidden(), 403, ErrorCode.FORBIDDEN),
        (EmailTaken(), 409, ErrorCode.EMAIL_TAKEN),
        (OAuthEmailRequired(), 400, ErrorCode.OAUTH_EMAIL_REQUIRED),
        (NotAnAudioTarget(), 400, ErrorCode.NOT_AN_AUDIO_TARGET),
    ],
)
def test_new_error_codes_mapped(exc: SpotdlError, status: int, code: ErrorCode) -> None:
    mapped_status, mapped_code, detail = _status_and_code(exc)
    assert mapped_status == status
    assert mapped_code is code
    assert detail is None
    assert isinstance(exc, SpotdlError)  # routed through the SpotdlError handler


@pytest.mark.parametrize(
    "member, value",
    [
        (ErrorCode.AUTH_REQUIRED, "authentication_required"),
        (ErrorCode.INVALID_CREDENTIALS, "invalid_credentials"),
        (ErrorCode.INVALID_TOKEN, "invalid_token"),
        (ErrorCode.TOKEN_EXPIRED, "token_expired"),
        (ErrorCode.FORBIDDEN, "forbidden"),
        (ErrorCode.EMAIL_TAKEN, "email_taken"),
        (ErrorCode.OAUTH_EMAIL_REQUIRED, "oauth_email_required"),
        (ErrorCode.NOT_AN_AUDIO_TARGET, "not_an_audio_target"),
    ],
)
def test_new_error_code_vocabulary_is_stable(member: ErrorCode, value: str) -> None:
    assert member.value == value


# --------------------------------------------------------------------------
# Integration — a throwaway app whose routes raise each exception.
# --------------------------------------------------------------------------


class _Body(BaseModel):
    count: int = Field(ge=0)


def _make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/unsupported")
    async def _unsupported() -> None:
        raise UnsupportedURL("bad:url:value")

    @app.get("/not-found")
    async def _not_found() -> None:
        raise NotFoundError(entity_type=EntityType.TRACK, entity_id="the-id")

    @app.get("/entity-not-found")
    async def _entity_not_found() -> None:
        raise EntityNotFound("upstream gone", provider=ProviderId.SPOTIFY)

    @app.get("/no-match")
    async def _no_match() -> None:
        raise NoMatchFound("nothing")

    @app.get("/rate-limited")
    async def _rate_limited() -> None:
        raise RateLimited("slow", provider=ProviderId.GENIUS, retry_after=30.0)

    @app.get("/rate-limited-no-retry")
    async def _rate_limited_no_retry() -> None:
        raise RateLimited(provider=ProviderId.GENIUS)

    @app.get("/unavailable")
    async def _unavailable() -> None:
        raise ProviderUnavailable("down", provider=ProviderId.DEEZER)

    @app.get("/download-failed")
    async def _download_failed() -> None:
        raise DownloadFailed("boom", step="convert")

    @app.get("/boom")
    async def _boom() -> None:
        raise RuntimeError("super secret internal detail")

    @app.post("/validate")
    async def _validate(body: _Body) -> dict[str, int]:
        return {"count": body.count}

    return app


def _client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=_make_app(), raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_integration_unsupported_url() -> None:
    async with _client() as client:
        resp = await client.get("/unsupported")
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "unsupported_url"
    assert body["message"] == "bad:url:value"
    assert body["detail"] == {"value": "bad:url:value"}


async def test_integration_not_found_error() -> None:
    async with _client() as client:
        resp = await client.get("/not-found")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "not_found"
    assert body["detail"] == {"entity_type": "track", "id": "the-id"}


async def test_integration_entity_not_found() -> None:
    async with _client() as client:
        resp = await client.get("/entity-not-found")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "not_found"
    assert body["detail"] == {"provider": "spotify"}


async def test_integration_no_match() -> None:
    async with _client() as client:
        resp = await client.get("/no-match")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "no_match_found"
    assert body["detail"] is None


async def test_integration_rate_limited_sets_header() -> None:
    async with _client() as client:
        resp = await client.get("/rate-limited")
    assert resp.status_code == 429
    body = resp.json()
    assert body["code"] == "rate_limited"
    assert body["detail"] == {"provider": "genius", "retry_after": 30.0}
    assert resp.headers["Retry-After"] == "30"


async def test_integration_rate_limited_without_retry_has_no_header() -> None:
    async with _client() as client:
        resp = await client.get("/rate-limited-no-retry")
    assert resp.status_code == 429
    assert "Retry-After" not in resp.headers
    assert resp.json()["detail"] == {"provider": "genius", "retry_after": None}


async def test_integration_provider_unavailable() -> None:
    async with _client() as client:
        resp = await client.get("/unavailable")
    assert resp.status_code == 502
    assert resp.json()["code"] == "provider_unavailable"


async def test_integration_download_failed() -> None:
    async with _client() as client:
        resp = await client.get("/download-failed")
    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == "download_failed"
    assert body["detail"] == {"step": "convert"}


async def test_integration_validation_error() -> None:
    async with _client() as client:
        resp = await client.post("/validate", json={"count": -1})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "validation_error"
    assert isinstance(body["detail"]["errors"], list)
    assert body["detail"]["errors"]  # non-empty


async def test_unhandled_exception_is_internal_error_and_hides_message() -> None:
    async with _client() as client:
        resp = await client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == "internal_error"
    assert body["detail"] is None
    assert "super secret internal detail" not in body["message"]


# --------------------------------------------------------------------------
# Envelope + vocabulary shape
# --------------------------------------------------------------------------


def test_error_envelope_defaults_detail_to_none() -> None:
    env = ErrorEnvelope(code=ErrorCode.INTERNAL_ERROR.value, message="x")
    assert env.detail is None
    assert env.model_dump() == {"code": "internal_error", "message": "x", "detail": None}


@pytest.mark.parametrize(
    "member, value",
    [
        (ErrorCode.UNSUPPORTED_URL, "unsupported_url"),
        (ErrorCode.NOT_FOUND, "not_found"),
        (ErrorCode.NO_MATCH_FOUND, "no_match_found"),
        (ErrorCode.PROVIDER_UNAVAILABLE, "provider_unavailable"),
        (ErrorCode.PROVIDER_AUTH_ERROR, "provider_auth_error"),
        (ErrorCode.RATE_LIMITED, "rate_limited"),
        (ErrorCode.VALIDATION_ERROR, "validation_error"),
        (ErrorCode.DOWNLOADS_DISABLED, "downloads_disabled"),
        (ErrorCode.DOWNLOAD_FAILED, "download_failed"),
        (ErrorCode.INTERNAL_ERROR, "internal_error"),
    ],
)
def test_error_code_vocabulary_is_stable(member: ErrorCode, value: str) -> None:
    assert member.value == value
