"""Task 10 — ``WS /ws/progress`` fan-out + per-mode auth (CONTRACT 3).

Offline via Starlette's ``TestClient.websocket_connect`` against the ASGI app with
a ``FakeDownloadEngine`` and a faked registry. The schema is pre-created (the pool
boots a crash-recovery query); ``TestClient`` runs the lifespan, so the download
pool actually executes submitted jobs on the app's event loop and the WS client
observes the live ``hello`` → ``job_queued`` → ``job_started`` → ``progress`` →
``job_finished`` sequence.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest
from spotdl_core.model import AudioCandidate, ProviderId, Track
from spotdl_server.app import create_app
from spotdl_server.auth.clock import SystemClock
from spotdl_server.auth.tokens import TokenService
from spotdl_server.db.base import Base
from spotdl_server.settings import DeploymentMode, Settings
from sqlalchemy import create_engine
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from apps.server.tests.conftest import FakeDownloadEngine
from apps.server.tests.fakes import FakeAudioProvider, FakeResolver, build_fake_registry

TRACK_URL = "https://open.spotify.com/track/track123"
_SECRET = "ws-progress-test-secret-0123456789-abcdef"


def _track_registry() -> Any:
    candidate = AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt1",
        url="https://audio/yt1",
        name="Song",
        artists=("Artist",),
        duration_ms=200_000,
    )
    return build_fake_registry(
        FakeResolver(
            id=ProviderId.SPOTIFY,
            track=Track(name="Song", artists=("Artist",), duration_ms=200_000, isrc="USABC1234567"),
        ),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=[candidate]),
    )


def _precreate_schema(settings: Settings) -> None:
    """Create the schema synchronously before ``TestClient`` runs the lifespan."""
    sync_url = settings.effective_database_url().replace("+aiosqlite", "")
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    engine.dispose()


def _build_app(tmp_path: Path, *, mode: DeploymentMode = DeploymentMode.EMBEDDED, **kw: Any) -> Any:
    settings = Settings(mode=mode, data_dir=tmp_path, **kw)
    _precreate_schema(settings)
    engine = FakeDownloadEngine(config=settings.download_config())
    return create_app(settings, registry=_track_registry(), download_engine=engine)


def test_first_frame_is_hello(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    with client, client.websocket_connect("/ws/progress") as ws:
        assert ws.receive_json() == {"type": "hello", "protocol_version": 1}


def test_receives_job_lifecycle_in_order(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    with client, client.websocket_connect("/ws/progress") as ws:
        assert ws.receive_json()["type"] == "hello"

        resp = client.post("/api/v1/downloads", json={"query": TRACK_URL})
        assert resp.status_code == 201

        seen: list[str] = []
        for _ in range(50):
            msg = ws.receive_json()
            seen.append(msg["type"])
            if msg["type"] in ("job_finished", "job_failed"):
                break

    assert "job_queued" in seen
    assert seen.index("job_started") < seen.index("progress") < seen.index("job_finished")
    assert seen.index("job_queued") < seen.index("job_started")


def test_two_clients_both_receive_and_survive_a_disconnect(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    with client, client.websocket_connect("/ws/progress") as ws_a:  # noqa: SIM117
        with client.websocket_connect("/ws/progress") as ws_b:
            assert ws_a.receive_json()["type"] == "hello"
            assert ws_b.receive_json()["type"] == "hello"

            client.post("/api/v1/downloads", json={"query": TRACK_URL})
            # both clients see the same broadcasts
            for ws in (ws_a, ws_b):
                types: list[str] = []
                for _ in range(50):
                    msg = ws.receive_json()
                    types.append(msg["type"])
                    if msg["type"] == "job_finished":
                        break
                assert "job_finished" in types
        # ws_b is now disconnected; the surviving client still receives new events
        client.post("/api/v1/downloads", json={"query": TRACK_URL})
        types_a: list[str] = []
        for _ in range(50):
            msg = ws_a.receive_json()
            types_a.append(msg["type"])
            if msg["type"] == "job_finished":
                break
        assert "job_finished" in types_a


def test_embedded_connects_without_token(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path, mode=DeploymentMode.EMBEDDED))
    with client, client.websocket_connect("/ws/progress") as ws:
        assert ws.receive_json()["type"] == "hello"


def test_selfhost_requires_token_when_configured(tmp_path: Path) -> None:
    from pydantic import SecretStr

    app = _build_app(
        tmp_path,
        mode=DeploymentMode.SELFHOST,
        auth_enabled=True,
        auth_secret_key=SecretStr(_SECRET),
        ws_progress_require_auth=True,
    )
    with TestClient(app) as client:
        # No token → the server closes with 4401 before the hello frame.
        with pytest.raises(WebSocketDisconnect) as excinfo:  # noqa: PT012, SIM117
            with client.websocket_connect("/ws/progress") as ws:
                ws.receive_json()
        assert excinfo.value.code == 4401

        # A valid access JWT (verified against the app's secret) connects.
        token = TokenService(secret=_SECRET, clock=SystemClock()).mint_access(
            user_id=uuid.uuid4(), is_admin=False
        )
        with client.websocket_connect(f"/ws/progress?token={token}") as ws:
            assert ws.receive_json() == {"type": "hello", "protocol_version": 1}
