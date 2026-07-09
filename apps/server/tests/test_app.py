from pathlib import Path

import httpx
import pytest
from spotdl_core.model import ProviderId, Track
from spotdl_server.app import create_app
from spotdl_server.auth.clock import SystemClock
from spotdl_server.db.base import Base
from spotdl_server.db.engine import build_engine
from spotdl_server.ratelimit.memory import InMemoryRateLimiter
from spotdl_server.settings import DeploymentMode, Settings

from apps.server.tests.fakes import FakeResolver, build_fake_registry
from tests.conftest import FakeDownloadEngine


async def _precreate_schema(settings: Settings) -> None:
    """Create the schema before the lifespan starts (Plan 7 pool boots a query)."""
    engine = build_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def make_client(settings: Settings | None = None) -> httpx.AsyncClient:
    app = create_app(settings)
    # These config tests skip the lifespan (they only read startup-fixed feature
    # flags), so provide the process-scoped state the rate-limit middleware reads
    # in HOSTED mode where it is mounted (built by the lifespan in production).
    app.state.clock = SystemClock()
    app.state.rate_limiter = InMemoryRateLimiter(app.state.clock)
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_health() -> None:
    async with make_client() as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_config_defaults_to_selfhost_with_downloads() -> None:
    async with make_client() as client:
        resp = await client.get("/api/v1/config")
    body = resp.json()
    assert body["mode"] == "selfhost"
    assert body["features"]["downloads"] is True


async def test_config_hosted_disables_downloads() -> None:
    async with make_client(Settings(mode=DeploymentMode.HOSTED)) as client:
        resp = await client.get("/api/v1/config")
    body = resp.json()
    assert body["mode"] == "hosted"
    assert body["features"]["downloads"] is False


def test_mode_reads_spotdl_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SPOTDL_MODE", "embedded")
    assert Settings().mode is DeploymentMode.EMBEDDED


def _sqlite_settings(tmp_path: Path) -> Settings:
    return Settings(mode=DeploymentMode.SELFHOST, data_dir=tmp_path)


async def test_create_app_uses_injected_registry_and_does_not_close_it(tmp_path: Path) -> None:
    """The ``registry=`` seam: the injected registry is used and NOT closed on
    shutdown (the caller owns its lifetime)."""
    track = Track(name="Song", artists=("Artist",), duration_ms=1000)
    fake = build_fake_registry(FakeResolver(id=ProviderId.SPOTIFY, track=track))

    closed: list[bool] = []
    original_aclose = fake.aclose

    async def recording_aclose() -> None:
        closed.append(True)
        await original_aclose()

    fake.aclose = recording_aclose  # type: ignore[method-assign]

    settings = _sqlite_settings(tmp_path)
    await _precreate_schema(settings)
    engine = FakeDownloadEngine(config=settings.download_config())
    app = create_app(settings, registry=fake, download_engine=engine)
    async with app.router.lifespan_context(app):
        assert app.state.registry is fake
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/health")
        assert resp.status_code == 200

    assert closed == []  # caller-owned registry is never closed by the app


async def test_create_app_builds_and_closes_its_own_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the kwarg, the app builds a default registry and closes it on
    shutdown."""
    fake = build_fake_registry(
        FakeResolver(
            id=ProviderId.SPOTIFY, track=Track(name="Song", artists=("Artist",), duration_ms=1000)
        )
    )
    closed: list[bool] = []
    original_aclose = fake.aclose

    async def recording_aclose() -> None:
        closed.append(True)
        await original_aclose()

    fake.aclose = recording_aclose  # type: ignore[method-assign]

    import spotdl_server.app as app_module

    monkeypatch.setattr(app_module, "build_default_registry", lambda _ctx: fake)

    settings = _sqlite_settings(tmp_path)
    await _precreate_schema(settings)
    engine = FakeDownloadEngine(config=settings.download_config())
    app = create_app(settings, download_engine=engine)
    async with app.router.lifespan_context(app):
        assert app.state.registry is fake

    assert closed == [True]  # app-built registry IS closed on shutdown


# --------------------------------------------------------------------------
# Startup-time mode gating + layering guards
# --------------------------------------------------------------------------


def _mounted_paths(app: object) -> set[str]:
    """Every mounted route path, resolving FastAPI's lazy ``_IncludedRouter`` wrappers."""
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


@pytest.mark.parametrize(
    ("mode", "downloads_mounted"),
    [
        (DeploymentMode.HOSTED, False),
        (DeploymentMode.SELFHOST, True),
        (DeploymentMode.EMBEDDED, True),
    ],
)
def test_download_routes_mounted_only_outside_hosted(
    mode: DeploymentMode, downloads_mounted: bool
) -> None:
    """Plan 7 mode gating: ``/api/v1/downloads*`` + ``/ws/progress`` mount in
    selfhost/embedded, never in hosted (spec §4)."""
    paths = _mounted_paths(create_app(Settings(mode=mode)))
    has_downloads = any(path.startswith("/api/v1/downloads") for path in paths)
    assert has_downloads is downloads_mounted
    assert ("/ws/progress" in paths) is downloads_mounted


# The router ≤200-line guard and the source-level ORM/FastAPI import checks now
# live in ``tests/test_layering.py`` (the single home for the layering guards).
