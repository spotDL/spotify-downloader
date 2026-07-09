"""``spotdl auth login|logout|status`` — PAT flow against the community server.

Auth is **remote-only** (CONTRACT C rule 5): the embedded server is authless, so
targeting it would silently "succeed" against nothing. These commands therefore
never fall back to the embedded transport — with ``--offline`` or an unreachable
server they fail fast with pinned copy and a stable exit code, and no embedded
server is ever booted.

``login`` (no ``--token``) does the interactive password flow: ``POST
/auth/login`` for a session, then ``POST /auth/tokens`` to mint a long-lived PAT
(named ``spotdl-cli <hostname>``) which is what gets stored. ``login --token``
stores a pasted PAT after validating it with ``GET /auth/me``. ``status`` reports
the logged-in identity via ``GET /auth/me`` (a 401 ⇒ "not logged in", exit OK).
``logout`` removes the stored credential and best-effort revokes the PAT
server-side when its id was recorded.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from uuid import UUID

import httpx
import typer
from rich.console import Console

from spotdl_cli.client import RemoteTransport, SpotdlClient
from spotdl_cli.config import (
    delete_token,
    get_token,
    load_config,
    merge_flag,
    store_token,
)
from spotdl_cli.errors import ApiError, ExitCode, render_api_error

auth_app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Log in to the spotDL community server.",
)

_err = Console(stderr=True)

_HEALTH_PATH = "/api/v1/health"
_PROBE_CONNECT_TIMEOUT = 2.0

_OFFLINE_COPY = "`spotdl auth` needs the community server and can't run with --offline."


def _unreachable_copy(api_url: str, reason: str) -> str:
    return (
        f"can't reach the spotDL server at {api_url} ({reason}) — "
        "`spotdl auth` needs it. Check your connection or set a server with "
        "`spotdl config set api_url <url>`."
    )


def _fail(message: str, code: ExitCode) -> None:
    # soft_wrap so the pinned copy is emitted verbatim (no width-based wrapping).
    _err.print(f"error: {message}", style="red", markup=False, highlight=False, soft_wrap=True)
    raise typer.Exit(code=int(code))


def _origin(api_url: str) -> str:
    """The ``scheme://host[:port]`` key a credential is stored under."""
    parts = urlsplit(api_url)
    return f"{parts.scheme}://{parts.netloc}"


def _pat_name() -> str:
    return f"spotdl-cli {socket.gethostname()}"


def _mask(token: str) -> str:
    """A display form of a secret that never reveals it in full."""
    if len(token) <= 8:
        return "…"
    return f"{token[:8]}…{token[-4:]}"


async def _probe(transport: RemoteTransport) -> str | None:
    """Return ``None`` if the server is reachable, else a short failure reason.

    Reachable = any non-5xx HTTP response (a 4xx still means the server is up).
    Unreachable = a connection/timeout/DNS error or a 5xx (CONTRACT C rule 2/5).
    """
    timeout = httpx.Timeout(30.0, connect=_PROBE_CONNECT_TIMEOUT)
    try:
        resp = await transport.http_client().get(_HEALTH_PATH, timeout=timeout)
    except httpx.HTTPError as exc:
        return str(exc) or type(exc).__name__
    if resp.status_code >= 500:
        return f"HTTP {resp.status_code}"
    return None


@asynccontextmanager
async def _connect_remote(*, api_url: str, offline: bool) -> AsyncIterator[SpotdlClient]:
    """Yield a community-server-only client, or fail fast (CONTRACT C rule 5).

    Never touches the embedded transport: the yielded client's ``downloads``
    transport is the same remote one (auth never downloads), so no SQLite file is
    created and no fallback warning is printed.
    """
    if offline:
        _fail(_OFFLINE_COPY, ExitCode.USAGE)
    transport = RemoteTransport(api_url)
    try:
        reason = await _probe(transport)
        if reason is not None:
            _fail(_unreachable_copy(api_url, reason), ExitCode.TRANSPORT)
        yield SpotdlClient(resolution=transport, downloads=transport)
    finally:
        await transport.aclose()


def _resolve_target(api_url: str | None, offline: bool) -> tuple[str, bool]:
    """Fold CLI flags over the config file: effective ``(api_url, offline)``."""
    cfg = load_config()
    effective_url = merge_flag(api_url, config_default=cfg.api_url)
    return str(effective_url), (offline or cfg.offline)


# ---- login ------------------------------------------------------------------


@auth_app.command("login")
def login(
    token: str | None = typer.Option(
        None, "--token", help="Store a pasted PAT instead of the email/password flow."
    ),
    offline: bool = typer.Option(False, "--offline", help="(auth cannot run offline)"),
    api_url: str | None = typer.Option(None, "--api-url", help="Override the server URL."),
) -> None:
    """Log in and store a personal access token for the community server."""
    effective_url, effective_offline = _resolve_target(api_url, offline)
    try:
        asyncio.run(_do_login(effective_url, effective_offline, token))
    except ApiError as err:
        raise typer.Exit(code=int(render_api_error(err))) from err


async def _do_login(api_url: str, offline: bool, token: str | None) -> None:
    origin = _origin(api_url)
    async with _connect_remote(api_url=api_url, offline=offline) as client:
        if token is not None:
            user = await client.me(token=token)
            store_token(origin, token, email=user.email)
            _confirm(origin, user.email, token)
            return
        email = typer.prompt("Email")
        password = typer.prompt("Password", hide_input=True)
        tokens = await client.login_password(email, password)
        pat = await client.create_pat(_pat_name(), access_token=tokens.access_token)
    store_token(origin, pat.token, email=tokens.user.email, token_id=pat.id)
    _confirm(origin, tokens.user.email, pat.token)


def _confirm(origin: str, email: str, token: str) -> None:
    typer.echo(f"logged in to {origin} as {email}")
    typer.echo(f"stored a personal access token ({_mask(token)}) — keep it secret")


# ---- status -----------------------------------------------------------------


@auth_app.command("status")
def status(
    offline: bool = typer.Option(False, "--offline", help="(auth cannot run offline)"),
    api_url: str | None = typer.Option(None, "--api-url", help="Override the server URL."),
) -> None:
    """Show the logged-in identity for the community server."""
    effective_url, effective_offline = _resolve_target(api_url, offline)
    cred = get_token(_origin(effective_url))
    if cred is None:
        typer.echo("not logged in")
        return
    asyncio.run(_do_status(effective_url, effective_offline, cred.token))


async def _do_status(api_url: str, offline: bool, token: str) -> None:
    async with _connect_remote(api_url=api_url, offline=offline) as client:
        try:
            user = await client.me(token=token)
        except ApiError as err:
            if err.status == 401:
                typer.echo("not logged in")
                return
            raise typer.Exit(code=int(render_api_error(err))) from err
    typer.echo(f"logged in to {api_url} as {user.email}")


# ---- logout -----------------------------------------------------------------


@auth_app.command("logout")
def logout(
    api_url: str | None = typer.Option(None, "--api-url", help="Override the server URL."),
) -> None:
    """Remove the stored credential (best-effort server-side revoke)."""
    effective_url, _ = _resolve_target(api_url, offline=False)
    origin = _origin(effective_url)
    cred = get_token(origin)
    if cred is None:
        typer.echo("not logged in")
        return
    if cred.token_id is not None:
        _best_effort_revoke(effective_url, cred.token, cred.token_id)
    delete_token(origin)
    typer.echo(f"logged out of {origin}")


def _best_effort_revoke(api_url: str, token: str, token_id: str) -> None:
    """Revoke the PAT server-side; any failure is ignored (local logout wins)."""
    with contextlib.suppress(ApiError, httpx.HTTPError, ValueError):
        asyncio.run(_do_revoke(api_url, token, token_id))


async def _do_revoke(api_url: str, token: str, token_id: str) -> None:
    transport = RemoteTransport(api_url, token=token)
    try:
        client = SpotdlClient(resolution=transport, downloads=transport)
        await client.revoke_pat(UUID(token_id), access_token=token)
    finally:
        await transport.aclose()


__all__ = ["auth_app"]
