"""CONTRACT C — the connectivity policy: probe, embedded fallback, warning copy.

The resolution transport is chosen here (``SpotdlClient.from_config`` calls
:func:`select_resolution_transport`): remote when reachable, the offline embedded
server otherwise. The user-facing strings in this module are a CONTRACT — the
exact copy is pinned by ``test_fallback.py`` and must not drift.

This module is deliberately free of any concrete transport import so it composes
with ``RemoteTransport``/``EmbeddedTransport`` wherever they live (a sibling track
relocates them into ``transport.py``); it depends only on the ``Transport``
Protocol, under ``TYPE_CHECKING``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import httpx
from rich.console import Console

from spotdl_cli.errors import ExitCode

if TYPE_CHECKING:
    from spotdl_cli.client import Transport

# The health route the server actually mounts (spec §4). CONTRACT C describes the
# probe loosely as ``GET /health``; the server serves it under the ``/api/v1``
# prefix, so we hit the real endpoint — a probe against a 404 path could not tell
# "server up" from "server down".
HEALTH_PATH = "/api/v1/health"

# CONTRACT C rule 2: a cheap probe with a short (2 s) connect timeout.
PROBE_TIMEOUT_SECONDS = 2.0

# --- pinned user-facing copy (CONTRACT C) ------------------------------------

FALLBACK_WARNING = (
    "warning: couldn't reach the spotDL community server at {api_url} ({reason}); "
    "using the offline embedded server for this run. Metadata may be thinner and "
    "slower. Pass --offline to silence this, or set a server with "
    "`spotdl config set api_url <url>`."
)
"""Printed to stderr when the remote is unreachable and we fall back (rule 2)."""

OFFLINE_AUTH_ERROR = "error: `spotdl auth` needs the community server and can't run with --offline."
"""``require_remote`` + offline (rule 5): exit ``USAGE``."""

UNREACHABLE_AUTH_ERROR = (
    "error: can't reach the spotDL server at {api_url} ({reason}) — `spotdl auth` needs it. "
    "Check your connection or set a server with `spotdl config set api_url <url>`."
)
"""``require_remote`` + unreachable (rule 5): exit ``TRANSPORT``."""


class RemoteRequiredError(Exception):
    """The community server is required but unavailable (CONTRACT C rule 5).

    Auth commands (``require_remote=True``) never fall back to the authless
    embedded server. This carries the already-formatted CLI copy and the process
    :class:`ExitCode` so the caller prints ``message`` and exits ``exit_code``
    directly — no CONTRACT E envelope lookup.
    """

    def __init__(self, message: str, exit_code: ExitCode) -> None:
        self.message = message
        self.exit_code = exit_code
        super().__init__(message)


def _reason(exc: httpx.HTTPError) -> str:
    text = str(exc).strip()
    return text or type(exc).__name__


async def probe_remote(
    client: httpx.AsyncClient, *, timeout: float = PROBE_TIMEOUT_SECONDS
) -> str | None:
    """Probe the remote's health. Return ``None`` if reachable, else a short reason.

    Reachability (CONTRACT C rule 2): fall back only on a connection/timeout/DNS
    error or a 5xx. Any status < 500 (including a 4xx) proves the server is up.
    """
    try:
        resp = await client.get(HEALTH_PATH, timeout=httpx.Timeout(timeout))
    except httpx.HTTPError as exc:
        return _reason(exc)
    if resp.status_code >= 500:
        return f"HTTP {resp.status_code}"
    return None


async def select_resolution_transport(
    *,
    offline: bool,
    api_url: str,
    require_remote: bool,
    make_remote: Callable[[], Transport],
    make_embedded: Callable[[], Transport],
    console: Console | None = None,
) -> Transport:
    """Pick the resolution transport per CONTRACT C, warning/erroring as specified.

    * ``offline`` → embedded, no probe, no warning (rule 1); with
      ``require_remote`` it is an error instead (rule 5a).
    * otherwise → remote at ``api_url``, health-probed. Unreachable → embedded
      with the pinned warning (rule 2), or, with ``require_remote``, a
      :class:`RemoteRequiredError` and no fallback (rule 5b).
    """
    if offline:
        if require_remote:
            raise RemoteRequiredError(OFFLINE_AUTH_ERROR, ExitCode.USAGE)
        return make_embedded()

    remote = make_remote()
    reason = await probe_remote(remote.http_client())
    if reason is None:
        return remote

    await remote.aclose()
    if require_remote:
        raise RemoteRequiredError(
            UNREACHABLE_AUTH_ERROR.format(api_url=api_url, reason=reason),
            ExitCode.TRANSPORT,
        )
    err = console if console is not None else Console(stderr=True)
    err.print(
        FALLBACK_WARNING.format(api_url=api_url, reason=reason),
        style="yellow",
        markup=False,
        highlight=False,
    )
    return make_embedded()
