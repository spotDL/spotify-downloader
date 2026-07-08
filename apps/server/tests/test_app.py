import httpx
from spotdl_server.app import create_app
from spotdl_server.settings import DeploymentMode, Settings


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
