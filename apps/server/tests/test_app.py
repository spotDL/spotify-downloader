from pathlib import Path

import httpx
import pytest
from spotdl_core.model import ProviderId, Track
from spotdl_server.app import create_app
from spotdl_server.settings import DeploymentMode, Settings

from apps.server.tests.fakes import FakeResolver, build_fake_registry


def make_client(settings: Settings | None = None) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=create_app(settings))
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

    app = create_app(_sqlite_settings(tmp_path), registry=fake)
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

    app = create_app(_sqlite_settings(tmp_path))
    async with app.router.lifespan_context(app):
        assert app.state.registry is fake

    assert closed == [True]  # app-built registry IS closed on shutdown


# --------------------------------------------------------------------------
# Startup-time mode gating + layering guards
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode", [DeploymentMode.HOSTED, DeploymentMode.SELFHOST, DeploymentMode.EMBEDDED]
)
def test_no_download_routes_mounted_in_any_mode(mode: DeploymentMode) -> None:
    """The download router is a Plan 7 concern: no ``/api/v1/downloads*`` route
    exists in any deployment mode (guards against Plan 7 always-mounting it)."""
    app = create_app(Settings(mode=mode))
    paths = {getattr(route, "path", "") for route in app.routes}
    assert not any(path.startswith("/api/v1/downloads") for path in paths)


# The router ≤200-line guard and the source-level ORM/FastAPI import checks now
# live in ``tests/test_layering.py`` (the single home for the layering guards).
