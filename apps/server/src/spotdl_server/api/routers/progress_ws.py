"""``WS /ws/progress`` — the single download-progress fan-out (CONTRACT 3).

One WebSocket endpoint streams **all** job events to **every** connected client
(clients filter by ``batch_id``/``job_id`` themselves). It is server→client only:
inbound frames are ignored except to detect disconnect. On connect it sends the
:class:`WsHello` version envelope first, then a best-effort snapshot of the
currently non-terminal jobs, then relies on the :class:`ProgressHub` to deliver
live broadcasts until the client goes away.

**Auth mirrors ``require_download_access`` but reads a ``?token=`` query param**
(browsers cannot set ``Authorization`` on a WebSocket): embedded is open (auth
inactive by default); selfhost requires a valid JWT/PAT only when
``ws_progress_require_auth`` (derived from ``downloads_require_auth``) *and* the
derived ``auth_active()`` both hold; hosted never mounts the route. Auth failure
closes with code ``4401`` before any hello frame. The inconsistent
require-auth-without-active-auth combination is unrepresentable (startup
fail-fast, ``create_app``).
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from spotdl_server.api.deps import auth_context_from_token
from spotdl_server.api.schemas import WsHello, WsJobQueued, WsMessage
from spotdl_server.auth.tokens import TokenService
from spotdl_server.db.enums import DownloadStatus
from spotdl_server.repositories.downloads import DownloadJobRepository

router = APIRouter()

_WS_AUTH_FAILED = 4401
# Non-terminal statuses whose jobs are replayed to a newly-connected client.
_NON_TERMINAL = (DownloadStatus.QUEUED, DownloadStatus.RUNNING)


async def _authorized(websocket: WebSocket) -> bool:
    """Whether the connection may proceed (mirrors ``require_download_access``)."""
    settings = websocket.app.state.settings
    require = settings.ws_progress_require_auth
    if require is None:  # derive from the download gate
        require = settings.downloads_require_auth
    if not (require and settings.auth_active()):
        return True

    token = websocket.query_params.get("token")
    if not token:
        return False
    clock = websocket.app.state.clock
    try:
        token_service = TokenService(
            secret=settings.require_auth_secret(),
            clock=clock,
            access_ttl_s=settings.access_token_ttl_seconds,
            refresh_ttl_s=settings.refresh_token_ttl_seconds,
        )
    except Exception:  # noqa: BLE001 - a misconfigured secret is an auth failure
        return False
    async with websocket.app.state.sessionmaker() as session:
        ctx = await auth_context_from_token(
            token, session=session, token_service=token_service, clock=clock
        )
        await session.commit()  # persist a PAT last_used_at touch, if any
    return ctx.authenticated


async def _snapshot(websocket: WebSocket) -> list[WsMessage]:
    """Best-effort ``job_queued`` frames for the current non-terminal jobs."""
    messages: list[WsMessage] = []
    async with websocket.app.state.sessionmaker() as session:
        repo = DownloadJobRepository(session)
        for job_status in _NON_TERMINAL:
            jobs, _ = await repo.list(status=job_status, limit=1000)
            for job in jobs:
                messages.append(
                    WsJobQueued(
                        job_id=job.id,
                        batch_id=job.batch_id,
                        track_name=None,
                        list_position=job.list_position,
                        list_length=None,
                    )
                )
    return messages


@router.websocket("/ws/progress")
async def progress_ws(websocket: WebSocket) -> None:
    """Register the client, greet it, snapshot, then stream broadcasts until gone."""
    if not await _authorized(websocket):
        await websocket.close(code=_WS_AUTH_FAILED)
        return

    hub = websocket.app.state.download_hub
    await hub.register(websocket)  # accepts the connection
    try:
        await websocket.send_text(WsHello().model_dump_json())
        await hub.snapshot_to(websocket, await _snapshot(websocket))
        # Server→client only: drain inbound frames purely to detect disconnect. The
        # low-level ``receive()`` returns a ``websocket.disconnect`` message on close
        # (it does not raise), so break on it; ``receive_text``/``receive_json`` would
        # raise ``WebSocketDisconnect`` instead — caught for older Starlette paths.
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        hub.unregister(websocket)
