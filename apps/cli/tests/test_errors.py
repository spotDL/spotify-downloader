"""CONTRACT E: exit codes + exhaustive server-envelope rendering.

The expected-message table below is table-driven over **every** ``ErrorCode`` the
generated client knows about; ``test_every_error_code_is_covered`` asserts the
table has one row per code, so a new server error code fails this suite until CLI
copy is written for it. ``render_api_error`` is exercised for each row to lock the
exact stderr message and the returned :class:`ExitCode`.
"""

from __future__ import annotations

import io

import pytest
from rich.console import Console
from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.errors import ApiError, ExitCode, render_api_error

# code -> (ApiError to render, exact stderr message sans the "error: " prefix, exit code)
CASES: dict[ErrorCode, tuple[ApiError, str, ExitCode]] = {
    ErrorCode.NOT_FOUND: (
        ApiError(ErrorCode.NOT_FOUND, message="Track abc"),
        "not found: Track abc",
        ExitCode.DOWNLOAD_FAILURES,
    ),
    ErrorCode.NO_MATCH_FOUND: (
        ApiError(ErrorCode.NO_MATCH_FOUND, detail={"track": "Foo - Bar"}),
        'no matching audio found for "Foo - Bar" — try `spotdl search`, '
        "or submit a match URL for it",
        ExitCode.DOWNLOAD_FAILURES,
    ),
    ErrorCode.UNSUPPORTED_URL: (
        ApiError(ErrorCode.UNSUPPORTED_URL, message="not a spotify link"),
        "unsupported URL or query: not a spotify link",
        ExitCode.DOWNLOAD_FAILURES,
    ),
    ErrorCode.UNSUPPORTED_ENTITY: (
        ApiError(ErrorCode.UNSUPPORTED_ENTITY, detail={"entity_type": "artist"}),
        "can't download a artist — pass a track, album, or playlist",
        ExitCode.DOWNLOAD_FAILURES,
    ),
    ErrorCode.NOT_AN_AUDIO_TARGET: (
        ApiError(ErrorCode.NOT_AN_AUDIO_TARGET, message="youtube channel"),
        "that URL isn't a downloadable audio source: youtube channel",
        ExitCode.USAGE,
    ),
    ErrorCode.DOWNLOAD_FAILED: (
        ApiError(ErrorCode.DOWNLOAD_FAILED, detail={"step": "convert", "reason": "ffmpeg missing"}),
        "download failed at convert: ffmpeg missing",
        ExitCode.DOWNLOAD_FAILURES,
    ),
    ErrorCode.PROVIDER_UNAVAILABLE: (
        ApiError(ErrorCode.PROVIDER_UNAVAILABLE, detail={"provider": "spotify"}),
        "provider spotify is unavailable right now — results may be degraded; try again later",
        ExitCode.TRANSPORT,
    ),
    ErrorCode.PROVIDER_AUTH_ERROR: (
        ApiError(ErrorCode.PROVIDER_AUTH_ERROR, detail={"provider": "spotify"}),
        "provider spotify rejected the server's credentials — "
        "the server operator needs to fix this",
        ExitCode.TRANSPORT,
    ),
    ErrorCode.DOWNLOADS_DISABLED: (
        ApiError(ErrorCode.DOWNLOADS_DISABLED),
        "downloads are disabled on this server (hosted mode); run downloads locally",
        ExitCode.TRANSPORT,
    ),
    ErrorCode.RATE_LIMITED: (
        ApiError(ErrorCode.RATE_LIMITED, detail={"retry_after": 30}),
        "rate limited by the server; retry after 30s",
        ExitCode.TRANSPORT,
    ),
    ErrorCode.VALIDATION_ERROR: (
        ApiError(ErrorCode.VALIDATION_ERROR, message="q is required"),
        "invalid request: q is required",
        ExitCode.USAGE,
    ),
    ErrorCode.AUTHENTICATION_REQUIRED: (
        ApiError(ErrorCode.AUTHENTICATION_REQUIRED),
        "this needs an account — run `spotdl auth login`",
        ExitCode.AUTH,
    ),
    ErrorCode.FORBIDDEN: (
        ApiError(ErrorCode.FORBIDDEN, message="admins only"),
        "you don't have permission: admins only",
        ExitCode.AUTH,
    ),
    ErrorCode.INVALID_TOKEN: (
        ApiError(ErrorCode.INVALID_TOKEN),
        "your saved login is invalid or expired — run `spotdl auth login`",
        ExitCode.AUTH,
    ),
    ErrorCode.TOKEN_EXPIRED: (
        ApiError(ErrorCode.TOKEN_EXPIRED),
        "your saved login is invalid or expired — run `spotdl auth login`",
        ExitCode.AUTH,
    ),
    ErrorCode.INVALID_CREDENTIALS: (
        ApiError(ErrorCode.INVALID_CREDENTIALS),
        "wrong email or password",
        ExitCode.AUTH,
    ),
    ErrorCode.EMAIL_TAKEN: (
        ApiError(ErrorCode.EMAIL_TAKEN),
        "an account with this email already exists — log in instead",
        ExitCode.AUTH,
    ),
    ErrorCode.OAUTH_EMAIL_REQUIRED: (
        ApiError(ErrorCode.OAUTH_EMAIL_REQUIRED),
        "your OAuth account has no visible email; make one public or register with email+password",
        ExitCode.AUTH,
    ),
    ErrorCode.INTERNAL_ERROR: (
        ApiError(ErrorCode.INTERNAL_ERROR, message="boom"),
        "server error: boom",
        ExitCode.TRANSPORT,
    ),
}


def _render(err: ApiError) -> tuple[str, ExitCode]:
    buf = io.StringIO()
    console = Console(file=buf, width=10_000, no_color=True)
    exit_code = render_api_error(err, console=console)
    return buf.getvalue().strip(), exit_code


def test_every_error_code_is_covered() -> None:
    """The rendering table is exhaustive over the generated ``ErrorCode`` vocabulary."""
    assert set(CASES) == set(ErrorCode)


@pytest.mark.parametrize("code", list(CASES))
def test_render_matches_contract(code: ErrorCode) -> None:
    err, expected_message, expected_exit = CASES[code]
    output, exit_code = _render(err)
    assert output == f"error: {expected_message}"
    assert exit_code == expected_exit


def test_unknown_future_code_degrades_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    """A code with no row falls back to a generic message + TRANSPORT, not a crash.

    Simulates a server ahead of this client by dropping a row from the table and
    asserting the documented fallback (``server error ({code}): {message}``).
    """
    from spotdl_cli import errors

    patched = dict(errors._TABLE)
    del patched[ErrorCode.NOT_FOUND]
    monkeypatch.setattr(errors, "_TABLE", patched)

    output, exit_code = _render(ApiError(ErrorCode.NOT_FOUND, message="gone"))
    assert output == f"error: server error ({ErrorCode.NOT_FOUND.value}): gone"
    assert exit_code == ExitCode.TRANSPORT


def test_exit_codes_are_stable() -> None:
    """Scripts depend on these numeric values (CONTRACT E)."""
    assert (ExitCode.OK, ExitCode.DOWNLOAD_FAILURES, ExitCode.USAGE) == (0, 1, 2)
    assert (ExitCode.TRANSPORT, ExitCode.AUTH) == (3, 4)
