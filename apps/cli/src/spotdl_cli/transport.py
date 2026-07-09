"""The transport seam ``SpotdlClient`` sits on, and its implementations.

A :class:`Transport` yields an ``httpx.AsyncClient`` for request/response and a
``ws_connect`` for progress frames. Two implementations back it:

  * :class:`RemoteTransport` — a remote HTTPS community server (the HTTP half
    lives here; the PAT/WebSocket half is layered on in a sibling task).
  * :class:`EmbeddedTransport` — the in-process server the CLI runs itself. It
    boots the shared SQLite database (migrations + WAL) and then serves the app
    either over the zero-socket **ASGITransport fast path** (metadata-only use)
    or, when WebSocket progress is needed, over a **loopback uvicorn** bound to
    ``127.0.0.1`` on an ephemeral port.

Migrations run once per boot through :mod:`spotdl_cli.bootstrap` (flock-
serialized across processes), and WAL + busy-timeout are enabled on the SQLite
file so concurrent ``spotdl`` read invocations against one data dir block
briefly instead of failing with ``database is locked``. Concurrent *download*
runs against one data dir are not supported (Plan 7's queue is single-process-
owned): one download run at a time per data dir; a cross-process job lock is a
noted future enhancement.
"""

from __future__ import annotations

import asyncio
import inspect
import socket
import sqlite3
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import TracebackType
from typing import Any, Protocol

import httpx
import uvicorn
from fastapi import FastAPI
from httpx_ws import AsyncWebSocketSession, aconnect_ws
from spotdl_server.app import create_app
from spotdl_server.settings import Settings

from spotdl_cli.bootstrap import migrate

# Seam guard: the embedded transport injects a fake/real registry through the
# Plan 5 ``create_app(settings, *, registry=...)`` hook. If that keyword ever
# disappears upstream, fail loudly at import — do NOT patch apps/server here.
if "registry" not in inspect.signature(create_app).parameters:  # pragma: no cover - guard
    raise RuntimeError("Plan 5 seam missing — fix upstream, do not patch apps/server here")

# Mirror ``spotdl_server.db.engine``: WAL so readers never block the writer and a
# read→write upgrade never deadlocks; busy_timeout so a second writer waits
# briefly instead of failing instantly on contention.
_SQLITE_BUSY_TIMEOUT_MS = 5000

# How long ``start()`` waits for the loopback server to report startup complete.
_LOOPBACK_START_TIMEOUT_S = 10.0


class Transport(Protocol):
    """The seam ``SpotdlClient`` sits on.

    Yields an ``httpx.AsyncClient`` for request/response and a ``ws_connect`` for
    progress. The TUI and view-models (Plan 9) depend on ``SpotdlClient``, not on
    this protocol. :class:`RemoteTransport` and :class:`EmbeddedTransport` are the
    two implementors.
    """

    @property
    def http_base(self) -> str: ...

    @property
    def ws_base(self) -> str: ...

    def http_client(self) -> httpx.AsyncClient: ...

    def ws_connect(self, path: str) -> AbstractAsyncContextManager[AsyncWebSocketSession]: ...

    async def aclose(self) -> None: ...


def _http_to_ws(base_url: str) -> str:
    if base_url.startswith("https://"):
        return "wss://" + base_url[len("https://") :]
    if base_url.startswith("http://"):
        return "ws://" + base_url[len("http://") :]
    return base_url


class RemoteTransport:
    """A remote HTTPS server: an ``httpx.AsyncClient`` + an optional Bearer PAT.

    The request/response half (Task 2). The WebSocket half (``ws_connect`` over
    ``wss`` via httpx-ws) is wired in a sibling task; its structure is kept ready
    for that here without any semantic change.
    """

    def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 30.0) -> None:
        self._http_base = base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.AsyncClient(base_url=self._http_base, headers=headers, timeout=timeout)

    @property
    def http_base(self) -> str:
        return self._http_base

    @property
    def ws_base(self) -> str:
        return _http_to_ws(self._http_base)

    def http_client(self) -> httpx.AsyncClient:
        return self._client

    @asynccontextmanager
    async def ws_connect(self, path: str) -> AsyncIterator[AsyncWebSocketSession]:
        """Open a ``wss`` session on ``self._client`` (httpx-ws over the same client).

        Reusing the transport's ``httpx.AsyncClient`` means the optional Bearer PAT
        set in ``__init__`` rides the WebSocket handshake headers too — the CLI
        (unlike a browser) can send ``Authorization`` on the upgrade request.
        """
        session: AsyncWebSocketSession
        async with aconnect_ws(self.ws_base + path, self._client) as session:
            yield session

    async def aclose(self) -> None:
        await self._client.aclose()


def _enable_wal(settings: Settings) -> None:
    """Persist WAL + busy-timeout on the embedded SQLite file, once per boot.

    WAL is a durable property of the database file, so a single connection at
    boot is enough for every later engine connection (the server's ``build_engine``
    re-asserts the same pragmas per connection anyway). A no-op for a non-SQLite
    ``database_url`` (Postgres has no journal-mode pragma) or an in-memory URL.
    """
    url = settings.effective_database_url()
    if not url.startswith("sqlite"):
        return
    _, _, path = url.partition(":///")
    if not path:  # in-memory (``sqlite+aiosqlite://``) — nothing to persist
        return
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
    finally:
        conn.close()


class EmbeddedTransport:
    """The in-process server the CLI runs itself.

    On :meth:`start` it boots the shared database (migrations + WAL) and then
    serves the app one of two ways:

      * ``enable_downloads=False`` (default) — the **ASGITransport fast path**: no
        socket, no background server; the app's lifespan is entered directly and
        requests are dispatched in-process. ``ws_connect`` is unavailable.
      * ``enable_downloads=True`` — a **loopback uvicorn** on ``127.0.0.1`` at an
        ephemeral port, so WebSocket progress works over a real socket. uvicorn
        owns the app lifespan (and thus the single download pool). Signal handlers
        are disabled so the CLI keeps sole ownership of SIGINT/SIGTERM.

    Use as an async context manager (``async with EmbeddedTransport(...) as t``);
    :meth:`aclose` tears down the server/lifespan and disposes resources.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        app_factory: Callable[[Settings], FastAPI] | None = None,
        enable_downloads: bool = False,
        run_migrations: bool = True,
    ) -> None:
        self._settings = settings
        self._app_factory = app_factory or create_app
        self._enable_downloads = enable_downloads
        self._run_migrations = run_migrations

        self._app: FastAPI | None = None
        self._client: httpx.AsyncClient | None = None
        self._http_base: str = ""
        # ASGI path: the manually-entered lifespan context we must exit on close.
        # (``lifespan_context`` may yield app state, hence the ``Any`` value type.)
        self._lifespan_cm: AbstractAsyncContextManager[Any] | None = None
        # Loopback path: the uvicorn server + its serve() task + bound socket.
        self._server: uvicorn.Server | None = None
        self._serve_task: asyncio.Task[None] | None = None
        self._socket: socket.socket | None = None
        self._started = False

    async def __aenter__(self) -> EmbeddedTransport:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def start(self) -> None:
        """Boot the database and stand up the chosen serving path (idempotent)."""
        if self._started:
            return
        # Migrations + WAL are blocking (Alembic + a sync sqlite3 connection);
        # run them off the event loop so we never block the running loop.
        await asyncio.to_thread(self._bootstrap_db)
        self._app = self._app_factory(self._settings)
        if self._enable_downloads:
            await self._start_loopback(self._app)
        else:
            await self._start_asgi(self._app)
        self._started = True

    def _bootstrap_db(self) -> None:
        if self._run_migrations:
            migrate(self._settings)
        _enable_wal(self._settings)

    async def _start_asgi(self, app: FastAPI) -> None:
        # Enter the app's lifespan so ``app.state`` holds the engine/session
        # factory/registry (and the download pool) exactly as a real boot would,
        # then dispatch over the in-process ASGITransport (no socket).
        self._lifespan_cm = app.router.lifespan_context(app)
        await self._lifespan_cm.__aenter__()
        self._http_base = "http://embedded"
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        self._client = httpx.AsyncClient(transport=transport, base_url=self._http_base)

    async def _start_loopback(self, app: FastAPI) -> None:
        # Bind our own ephemeral loopback socket so the port is known before the
        # server starts (and hand it to uvicorn to serve).
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        self._socket = sock

        config = uvicorn.Config(app, log_level="warning")
        server = uvicorn.Server(config)
        self._server = server
        # The CLI owns process signals: it must keep sole ownership of
        # SIGINT/SIGTERM so the user's Ctrl-C cancels the download run, not the
        # embedded server. uvicorn's public ``serve()`` wraps ``_serve()`` in
        # ``capture_signals()`` (this version dropped the old
        # ``install_signal_handlers`` config knob), so we drive the inner
        # ``_serve()`` directly to skip that signal capture.
        self._serve_task = asyncio.create_task(server._serve(sockets=[sock]))

        # Wait for uvicorn to signal startup complete (lifespan up, socket
        # accepting) before handing back a client — with a bounded budget so a
        # wedged boot surfaces instead of hanging.
        deadline = asyncio.get_running_loop().time() + _LOOPBACK_START_TIMEOUT_S
        while not server.started:
            if self._serve_task.done():  # startup failed — re-raise its error
                self._serve_task.result()
                raise RuntimeError("embedded loopback server exited during startup")
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("embedded loopback server did not start in time")
            await asyncio.sleep(0.02)

        self._http_base = f"http://127.0.0.1:{port}"
        self._client = httpx.AsyncClient(base_url=self._http_base)

    @property
    def http_base(self) -> str:
        return self._http_base

    @property
    def ws_base(self) -> str:
        return _http_to_ws(self._http_base)

    def http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("EmbeddedTransport.start() must be awaited before use")
        return self._client

    @asynccontextmanager
    async def ws_connect(self, path: str) -> AsyncIterator[AsyncWebSocketSession]:
        if not self._enable_downloads or self._client is None:
            raise NotImplementedError(
                "EmbeddedTransport WebSockets require the loopback server "
                "(construct with enable_downloads=True)"
            )
        ws: AsyncWebSocketSession
        async with aconnect_ws(self.ws_base + path, self._client) as ws:
            yield ws

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._server is not None:  # loopback: ask uvicorn to drain + stop
            self._server.should_exit = True
            if self._serve_task is not None:
                await self._serve_task
            self._server = None
            self._serve_task = None
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self._lifespan_cm is not None:  # ASGI: exit the lifespan we entered
            await self._lifespan_cm.__aexit__(None, None, None)
            self._lifespan_cm = None
        self._started = False
