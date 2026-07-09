"""Shared helpers for the ``spotdl`` command modules.

Two seams every command leans on:

* :func:`run` — drive an ``async`` command body from a sync Typer callback and
  turn a :class:`~spotdl_cli.errors.ApiError` into the CONTRACT E stderr message
  + process exit code (the single translation point until Task 13 installs the
  global handler).
* :func:`open_client` — acquire a configured :class:`SpotdlClient`. Production
  wires it to ``SpotdlClient.from_config`` (Tasks 4/5) over the CLI config
  (Task 3); tests monkeypatch this to yield a client built from fake transports,
  so the command modules never depend on those sibling tracks having landed.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Coroutine
from contextlib import asynccontextmanager
from typing import Any, TypeVar

import typer
from rich.console import Console

from spotdl_cli.client import SpotdlClient
from spotdl_cli.errors import ApiError, render_api_error

_T = TypeVar("_T")

console = Console()
"""Shared stdout console (Rich tables / summaries)."""

err_console = Console(stderr=True)
"""Shared stderr console (warnings + CONTRACT E error copy)."""


def run(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run an async command body, translating ``ApiError`` to a clean exit.

    A raised :class:`ApiError` is rendered with the CONTRACT E copy and re-raised
    as ``typer.Exit`` carrying the mapped exit code, so a command body can call
    the façade without every method sprouting its own error handling.
    """
    try:
        return asyncio.run(coro)
    except ApiError as exc:
        code = render_api_error(exc, console=err_console)
        raise typer.Exit(int(code)) from exc


@asynccontextmanager
async def open_client(
    *,
    offline: bool = False,
    need_downloads: bool = False,
    require_remote: bool = False,
) -> AsyncIterator[SpotdlClient]:
    """Yield a configured :class:`SpotdlClient` per the CONTRACT C policy.

    Wired to ``SpotdlClient.from_config`` over the CLI config; the config load and
    the ``from_config`` transports land on Tasks 3/4/5. Tests monkeypatch this
    whole function, so importing this module never requires those to exist yet.
    """
    from spotdl_cli.config import load_config  # type: ignore[import-not-found]  # lazy: Task 3

    async with SpotdlClient.from_config(
        load_config(),
        offline=offline,
        need_downloads=need_downloads,
        require_remote=require_remote,
    ) as client:
        yield client
