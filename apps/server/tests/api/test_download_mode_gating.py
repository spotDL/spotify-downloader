"""Task 8 — download mode gating, startup fail-fast, and the auth-access gate.

Fully offline: apps are built via the ``create_app(..., download_engine=...)``
seam with a ``FakeDownloadEngine`` so the lifespan never constructs a real engine
or touches the network. The mode/auth matrix (spec §4) and the startup gating
(router mounted or not; pool built or not) are the contract under test.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr
from spotdl_server.api.deps import require_download_access
from spotdl_server.app import create_app
from spotdl_server.auth.context import ANONYMOUS, AuthContext
from spotdl_server.db.base import Base
from spotdl_server.db.engine import build_engine
from spotdl_server.services.errors import AuthRequired
from spotdl_server.settings import DeploymentMode, Settings

from tests.conftest import FakeDownloadEngine


async def _create_schema(settings: Settings) -> None:
    """Create the full schema on the app's DB before the pool starts.

    The download pool's ``start()`` recovers orphaned jobs (a ``download_jobs``
    query) the instant the lifespan runs, so the tables must exist first — exactly
    as a real deployment runs Alembic before boot.
    """
    engine = build_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def _route_paths(app: object) -> set[str]:
    """Every mounted route path, resolving FastAPI's lazy ``_IncludedRouter`` wrappers.

    Recent FastAPI stores ``include_router`` results as lazy wrappers whose real
    routes live under ``original_router``; a plain ``app.routes`` walk misses them,
    so this recurses into that attribute to see the download + WS routes.
    """
    paths: set[str] = set()

    def _walk(routes: object) -> None:
        for route in routes:  # type: ignore[attr-defined]
            path = getattr(route, "path", None)
            if path:
                paths.add(path)
            original = getattr(route, "original_router", None)
            if original is not None:
                _walk(original.routes)

    _walk(app.router.routes)  # type: ignore[attr-defined]
    return paths


def _fake_request(settings: Settings) -> SimpleNamespace:
    """A stand-in ``Request`` exposing only ``app.state.settings`` (all deps need)."""
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)))


def test_hosted_mounts_no_download_routes() -> None:
    app = create_app(Settings(mode=DeploymentMode.HOSTED))
    paths = _route_paths(app)
    assert not any(path.startswith("/api/v1/downloads") for path in paths)
    assert "/ws/progress" not in paths


def test_selfhost_mounts_download_routes() -> None:
    app = create_app(Settings(mode=DeploymentMode.SELFHOST))
    paths = _route_paths(app)
    assert any(path.startswith("/api/v1/downloads") for path in paths)
    assert "/ws/progress" in paths


def test_embedded_mounts_download_routes() -> None:
    app = create_app(Settings(mode=DeploymentMode.EMBEDDED))
    paths = _route_paths(app)
    assert any(path.startswith("/api/v1/downloads") for path in paths)
    assert "/ws/progress" in paths


def test_selfhost_requires_auth_when_configured() -> None:
    settings = Settings(
        mode=DeploymentMode.SELFHOST,
        downloads_require_auth=True,
        auth_enabled=True,
        auth_secret_key=SecretStr("secret"),
    )
    request = _fake_request(settings)

    with pytest.raises(AuthRequired):
        require_download_access(request, auth=ANONYMOUS)  # type: ignore[arg-type]

    user = AuthContext(kind="user", user_id=uuid4(), is_admin=False)
    assert require_download_access(request, auth=user) is user  # type: ignore[arg-type]


def test_embedded_allows_anonymous_downloads() -> None:
    settings = Settings(mode=DeploymentMode.EMBEDDED)
    request = _fake_request(settings)
    # Even with the require flag set, embedded auth is inactive so the derived
    # gate never engages (it keys on auth_active(), never raw auth_enabled).
    assert require_download_access(request, auth=ANONYMOUS) is ANONYMOUS  # type: ignore[arg-type]


def test_selfhost_require_auth_without_active_auth_fails_startup() -> None:
    with pytest.raises(RuntimeError, match="downloads_require_auth"):
        create_app(
            Settings(
                mode=DeploymentMode.SELFHOST,
                downloads_require_auth=True,
                auth_enabled=False,
            )
        )


async def test_lifespan_builds_and_drains_pool_with_injected_engine(tmp_path: Path) -> None:
    settings = Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=tmp_path,
        library_path=tmp_path / "music",
        download_temp_dir=tmp_path / "temp",
    )
    await _create_schema(settings)
    engine = FakeDownloadEngine(config=settings.download_config())
    app = create_app(settings, download_engine=engine)

    async with app.router.lifespan_context(app):
        assert app.state.download_pool is not None
        assert app.state.download_hub is not None
    # After the lifespan exits, the pool has been drained/closed cleanly.
    assert app.state.download_pool._closed is True


async def test_hosted_lifespan_builds_no_pool(tmp_path: Path) -> None:
    # Hosted with auth active needs a secret to start (Plan 6 fail-fast); the point
    # here is only that no download pool/hub is built even once the lifespan runs.
    settings = Settings(
        mode=DeploymentMode.HOSTED,
        data_dir=tmp_path,
        auth_secret_key=SecretStr("secret"),
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        assert getattr(app.state, "download_pool", None) is None
