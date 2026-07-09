"""Exit codes, the typed :class:`ApiError`, and server-envelope rendering.

This is CONTRACT E of Plan 8: the closed ``ErrorCode`` vocabulary (owned by the
server, surfaced through the generated client) is mapped **exhaustively** to a
human message + a process :class:`ExitCode`. ``render_api_error`` is the single
top-level handler the CLI installs so every command turns a server error into
consistent copy on stderr and a stable exit status. ``test_errors.py`` iterates
the generated ``ErrorCode`` members and asserts every one has a row here, so a
new server error code can never ship without CLI copy for it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import IntEnum
from typing import Any

from rich.console import Console

from spotdl_cli._generated.api.models.error_code import ErrorCode


class ExitCode(IntEnum):
    """Process exit statuses (CONTRACT E). Stable — scripts depend on them."""

    OK = 0  # success
    DOWNLOAD_FAILURES = 1  # >=1 track/entity failed, or NoMatch/NotFound for the requested item
    USAGE = 2  # bad arguments (Typer default for BadParameter/UsageError)
    TRANSPORT = 3  # server unreachable and offline resolve also failed; 5xx; disabled; rate-limited
    AUTH = 4  # authentication_required / forbidden / invalid_token / token_expired


class ApiError(Exception):
    """A non-2xx ``ErrorEnvelope`` from the server, raised by ``SpotdlClient``.

    Carries the machine-readable ``code`` (used to look up the CONTRACT E row),
    the server ``message``, the optional structured ``detail`` (used to fill in
    per-code message fields), and the HTTP ``status``.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str = "",
        detail: Mapping[str, Any] | None = None,
        status: int = 0,
    ) -> None:
        self.code = code
        self.message = message
        self.detail = dict(detail) if detail is not None else None
        self.status = status
        super().__init__(f"{code.value}: {message}")


def _detail(err: ApiError) -> dict[str, Any]:
    return err.detail or {}


# CONTRACT E — the code -> (human message, exit code) table. Each message builder
# is a pure function of the ApiError so per-code `detail` fields (track, provider,
# step, ...) can be interpolated, falling back to the server message when absent.
_TABLE: dict[ErrorCode, tuple[Callable[[ApiError], str], ExitCode]] = {
    ErrorCode.NOT_FOUND: (
        lambda e: f"not found: {_detail(e).get('what') or e.message}",
        ExitCode.DOWNLOAD_FAILURES,
    ),
    ErrorCode.NO_MATCH_FOUND: (
        lambda e: (
            f'no matching audio found for "{_detail(e).get("track") or e.message}" — '
            "try `spotdl search`, or submit a match URL for it"
        ),
        ExitCode.DOWNLOAD_FAILURES,
    ),
    ErrorCode.UNSUPPORTED_URL: (
        lambda e: f"unsupported URL or query: {e.message}",
        ExitCode.DOWNLOAD_FAILURES,
    ),
    ErrorCode.UNSUPPORTED_ENTITY: (
        lambda e: (
            f"can't download a {_detail(e).get('entity_type') or 'that'} — "
            "pass a track, album, or playlist"
        ),
        ExitCode.DOWNLOAD_FAILURES,
    ),
    ErrorCode.NOT_AN_AUDIO_TARGET: (
        lambda e: f"that URL isn't a downloadable audio source: {e.message}",
        ExitCode.USAGE,
    ),
    ErrorCode.DOWNLOAD_FAILED: (
        lambda e: (
            f"download failed at {_detail(e).get('step') or '?'}: "
            f"{_detail(e).get('reason') or e.message}"
        ),
        ExitCode.DOWNLOAD_FAILURES,
    ),
    ErrorCode.PROVIDER_UNAVAILABLE: (
        lambda e: (
            f"provider {_detail(e).get('provider') or '?'} is unavailable right now — "
            "results may be degraded; try again later"
        ),
        ExitCode.TRANSPORT,
    ),
    ErrorCode.PROVIDER_AUTH_ERROR: (
        lambda e: (
            f"provider {_detail(e).get('provider') or '?'} rejected the server's credentials — "
            "the server operator needs to fix this"
        ),
        ExitCode.TRANSPORT,
    ),
    ErrorCode.DOWNLOADS_DISABLED: (
        lambda e: "downloads are disabled on this server (hosted mode); run downloads locally",
        ExitCode.TRANSPORT,
    ),
    ErrorCode.RATE_LIMITED: (
        lambda e: (
            f"rate limited by the server; retry after {_detail(e).get('retry_after') or '?'}s"
        ),
        ExitCode.TRANSPORT,
    ),
    ErrorCode.VALIDATION_ERROR: (
        lambda e: f"invalid request: {e.message}",
        ExitCode.USAGE,
    ),
    ErrorCode.AUTHENTICATION_REQUIRED: (
        lambda e: "this needs an account — run `spotdl auth login`",
        ExitCode.AUTH,
    ),
    ErrorCode.FORBIDDEN: (
        lambda e: f"you don't have permission: {e.message}",
        ExitCode.AUTH,
    ),
    ErrorCode.INVALID_TOKEN: (
        lambda e: "your saved login is invalid or expired — run `spotdl auth login`",
        ExitCode.AUTH,
    ),
    ErrorCode.TOKEN_EXPIRED: (
        lambda e: "your saved login is invalid or expired — run `spotdl auth login`",
        ExitCode.AUTH,
    ),
    ErrorCode.INVALID_CREDENTIALS: (
        lambda e: "wrong email or password",
        ExitCode.AUTH,
    ),
    ErrorCode.EMAIL_TAKEN: (
        lambda e: "an account with this email already exists — log in instead",
        ExitCode.AUTH,
    ),
    ErrorCode.OAUTH_EMAIL_REQUIRED: (
        lambda e: (
            "your OAuth account has no visible email; "
            "make one public or register with email+password"
        ),
        ExitCode.AUTH,
    ),
    ErrorCode.INTERNAL_ERROR: (
        lambda e: f"server error: {e.message}",
        ExitCode.TRANSPORT,
    ),
}


def format_api_error(err: ApiError) -> tuple[str, ExitCode]:
    """Return the ``(human message, exit code)`` for ``err`` per CONTRACT E.

    An unknown/future code (a server ahead of this client) degrades gracefully to
    ``server error ({code}): {message}`` with exit ``TRANSPORT`` rather than
    crashing.
    """
    row = _TABLE.get(err.code)
    if row is None:
        return f"server error ({err.code.value}): {err.message}", ExitCode.TRANSPORT
    builder, exit_code = row
    return builder(err), exit_code


def render_api_error(err: ApiError, *, console: Console | None = None) -> ExitCode:
    """Print ``err``'s CONTRACT E message to stderr (Rich) and return its exit code.

    The single top-level error handler the CLI wires in. Server-supplied text is
    printed with markup disabled so it can't inject Rich markup.
    """
    message, exit_code = format_api_error(err)
    out = console if console is not None else Console(stderr=True)
    out.print(f"error: {message}", style="red", markup=False, highlight=False)
    return exit_code
