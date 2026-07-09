"""``EmbeddedTransport`` + CLI DB bootstrap (Plan 8 Task 4).

The embedded transport runs the in-process server two ways:

  * the **ASGITransport fast path** (no socket) for pure request/response — the
    default for metadata-only embedded use;
  * a **loopback uvicorn** on ``127.0.0.1:<ephemeral>`` when WebSocket progress is
    needed (``enable_downloads=True``) — a real HTTP/WS server the CLI owns.

Both boot the shared SQLite ``spotdl.db`` under the data dir: migrations run once
(flock-serialized so two ``spotdl`` processes never race the file), and WAL +
busy-timeout are enabled so concurrent read invocations block briefly instead of
failing with ``database is locked``.

Every provider is faked at the registry seam (reusing the server suite's fakes),
so nothing here touches the network.
"""

from __future__ import annotations

import inspect
import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI
from spotdl_cli.bootstrap import migrate
from spotdl_cli.client import SpotdlClient
from spotdl_cli.transport import EmbeddedTransport
from spotdl_cli.views import ConfigView, EntityView
from spotdl_server.settings import DeploymentMode, Settings

Factory = Callable[[Settings], FastAPI]


def _settings(tmp_path: Path) -> Settings:
    return Settings(mode=DeploymentMode.EMBEDDED, data_dir=tmp_path)


def _db_journal_mode(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    try:
        return str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Seam guards: the Plan 5 hooks this task consumes must exist upstream. If they
# regress, fail here with a pointer — do NOT patch apps/server from apps/cli.
# --------------------------------------------------------------------------


def test_plan5_create_app_registry_seam_present() -> None:
    from spotdl_server.app import create_app

    params = inspect.signature(create_app).parameters
    assert "registry" in params, "Plan 5 seam missing — fix upstream, do not patch apps/server here"


def test_plan5_upgrade_to_head_seam_present() -> None:
    try:
        from spotdl_server.bootstrap import upgrade_to_head  # noqa: F401
    except ImportError as exc:  # pragma: no cover - guard
        pytest.fail(f"Plan 5 seam missing — fix upstream, do not patch apps/server here: {exc}")


# --------------------------------------------------------------------------
# ASGITransport fast path
# --------------------------------------------------------------------------


async def test_asgi_path_answers_config(tmp_path: Path, fake_factory: Factory) -> None:
    settings = _settings(tmp_path)
    async with EmbeddedTransport(settings, app_factory=fake_factory) as transport:
        client = SpotdlClient(resolution=transport, downloads=transport)
        view = await client.config()

    assert isinstance(view, ConfigView)
    assert view.mode == "embedded"
    assert view.features.downloads is True


async def test_asgi_path_resolves_fake_entity(tmp_path: Path, fake_factory: Factory) -> None:
    settings = _settings(tmp_path)
    async with EmbeddedTransport(settings, app_factory=fake_factory) as transport:
        client = SpotdlClient(resolution=transport, downloads=transport)
        view = await client.resolve("https://open.spotify.com/track/track123")

    assert isinstance(view, EntityView)
    assert view.type == "track"
    assert view.track is not None
    assert view.track.name == "Hello"


async def test_boot_creates_db_migrated_and_wal(tmp_path: Path, fake_factory: Factory) -> None:
    settings = _settings(tmp_path)
    async with EmbeddedTransport(settings, app_factory=fake_factory):
        pass

    db_path = tmp_path / "spotdl.db"
    assert db_path.is_file()

    conn = sqlite3.connect(db_path)
    try:
        # Migrations ran: alembic stamped head, and a real schema table exists.
        (head,) = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        assert head
        conn.execute("SELECT id FROM tracks LIMIT 1")  # a §6.1 table
    finally:
        conn.close()

    assert _db_journal_mode(db_path) == "wal"


# --------------------------------------------------------------------------
# Concurrent migration (flock serialization)
# --------------------------------------------------------------------------


def test_concurrent_migrations_serialize_no_lock_error(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    errors: list[BaseException] = []

    def run() -> None:
        try:
            migrate(settings)
        except BaseException as exc:  # noqa: BLE001 - the test asserts none escape
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == [], f"concurrent migrate() raised: {errors!r}"

    conn = sqlite3.connect(tmp_path / "spotdl.db")
    try:
        rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    finally:
        conn.close()
    assert len(rows) == 1, "migration should have been applied exactly once"


# --------------------------------------------------------------------------
# Loopback uvicorn path (real HTTP + WS surface)
# --------------------------------------------------------------------------


async def test_loopback_binds_localhost_and_serves_health(
    tmp_path: Path, fake_factory: Factory
) -> None:
    settings = _settings(tmp_path)
    async with EmbeddedTransport(
        settings, app_factory=fake_factory, enable_downloads=True
    ) as transport:
        assert transport.http_base.startswith("http://127.0.0.1:")
        assert transport.ws_base.startswith("ws://127.0.0.1:")
        resp = await transport.http_client().get("/api/v1/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
