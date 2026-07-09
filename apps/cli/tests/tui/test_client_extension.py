"""CONTRACT H: the thin passthrough façade methods the TUI needs.

Each new ``SpotdlClient`` method is a coroutine that calls one generated op and maps
the success body to a hand-written ``*View`` (or translates a non-2xx envelope into a
typed :class:`ApiError`) — the exact Plan 8 CONTRACT B pattern, no logic added.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import AsyncIterator
from uuid import UUID

import httpx
import pytest
import respx
from spotdl_cli.client import RemoteTransport, SpotdlClient
from spotdl_cli.errors import ApiError
from spotdl_cli.views import ConfigView, ReportView, StatsView, Tokens

BASE = "https://api.test"
REPORT_ID = UUID("22222222-2222-2222-2222-222222222222")
SUBJECT_ID = UUID("33333333-3333-3333-3333-333333333333")

CONFIG_JSON = {
    "features": {"auth": False, "downloads": True, "library": True, "voting": False},
    "matcher_version": "1.2.3",
    "mode": "embedded",
    "oauth_providers": [],
}
USER_JSON = {
    "id": "44444444-4444-4444-4444-444444444444",
    "email": "user@example.com",
    "is_admin": False,
    "created_at": "2024-01-01T00:00:00+00:00",
}
TOKEN_JSON = {
    "access_token": "access-jwt",
    "refresh_token": "refresh-jwt",
    "expires_in": 3600,
    "token_type": "bearer",
    "user": USER_JSON,
}
REPORT_JSON = {
    "created_at": "2024-01-02T00:00:00+00:00",
    "id": str(REPORT_ID),
    "status": "pending",
    "subject_id": str(SUBJECT_ID),
    "subject_type": "track",
    "field": "title",
    "proposed_value": "Correct Title",
    "reason": "typo",
}
STATS_JSON = {
    "community_verified_matches": 5,
    "matches_total": 20,
    "rejected_matches": 2,
    "reports_pending": 3,
    "reports_total": 7,
    "users_total": 10,
    "votes_total": 42,
}


@pytest.fixture
async def client() -> AsyncIterator[SpotdlClient]:
    transport = RemoteTransport(BASE)
    try:
        yield SpotdlClient(resolution=transport, downloads=transport)
    finally:
        await transport.aclose()


CONTRACT_H_METHODS = [
    "download_config",
    "register",
    "submit_report",
    "my_reports",
    "admin_reports",
    "approve_report",
    "reject_report",
    "admin_stats",
]


@pytest.mark.parametrize("name", CONTRACT_H_METHODS)
def test_method_exists_and_is_coroutine(name: str) -> None:
    method = getattr(SpotdlClient, name, None)
    assert method is not None, f"SpotdlClient is missing CONTRACT H method {name!r}"
    assert inspect.iscoroutinefunction(method), f"{name} must be async"


async def test_download_config_uses_download_transport(client: SpotdlClient) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/config").mock(return_value=httpx.Response(200, json=CONFIG_JSON))
        view = await client.download_config()
    assert isinstance(view, ConfigView)
    assert view.features.downloads is True


async def test_register_returns_tokens(client: SpotdlClient) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        route = router.post("/api/v1/auth/register").mock(
            return_value=httpx.Response(201, json=TOKEN_JSON)
        )
        tokens = await client.register("user@example.com", "hunter2hunter2")
    assert route.called
    assert isinstance(tokens, Tokens)
    assert tokens.access_token == "access-jwt"
    assert tokens.user.email == "user@example.com"


async def test_submit_report_maps_str_subject_type(client: SpotdlClient) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        route = router.post("/api/v1/reports").mock(
            return_value=httpx.Response(201, json=REPORT_JSON)
        )
        report = await client.submit_report(
            "track", SUBJECT_ID, field="title", proposed_value="Correct Title", reason="typo"
        )
    assert route.called
    sent = json.loads(route.calls.last.request.read())
    assert sent["subject_type"] == "track"
    assert sent["subject_id"] == str(SUBJECT_ID)
    assert isinstance(report, ReportView)
    assert report.subject_type == "track"
    assert report.field == "title"
    assert report.reporter is None


async def test_submit_report_invalid_subject_type_surfaces_server_validation(
    client: SpotdlClient,
) -> None:
    """An unknown ``subject_type`` reaches the server (422), never a client crash."""
    envelope = {"code": "validation_error", "message": "bad subject_type"}
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.post("/api/v1/reports").mock(return_value=httpx.Response(422, json=envelope))
        with pytest.raises(ApiError) as excinfo:
            await client.submit_report("not_an_entity", SUBJECT_ID)
    assert excinfo.value.code.value == "validation_error"


async def test_my_reports_maps_list(client: SpotdlClient) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/reports/me").mock(return_value=httpx.Response(200, json=[REPORT_JSON]))
        reports = await client.my_reports()
    assert [type(r) for r in reports] == [ReportView]
    assert reports[0].id == str(REPORT_ID)


async def test_admin_reports_unwraps_paged(client: SpotdlClient) -> None:
    body = {"items": [REPORT_JSON], "total": 1}
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        route = router.get("/api/v1/admin/reports").mock(
            return_value=httpx.Response(200, json=body)
        )
        reports = await client.admin_reports(status="pending")
    assert route.called
    assert route.calls.last.request.url.params["status"] == "pending"
    assert [type(r) for r in reports] == [ReportView]


async def test_approve_and_reject_report(client: SpotdlClient) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.post(f"/api/v1/admin/reports/{REPORT_ID}/approve").mock(
            return_value=httpx.Response(200, json={**REPORT_JSON, "status": "approved"})
        )
        router.post(f"/api/v1/admin/reports/{REPORT_ID}/reject").mock(
            return_value=httpx.Response(200, json={**REPORT_JSON, "status": "rejected"})
        )
        approved = await client.approve_report(REPORT_ID, note="ok")
        rejected = await client.reject_report(REPORT_ID)
    assert approved.status == "approved"
    assert rejected.status == "rejected"


async def test_admin_stats_maps_view(client: SpotdlClient) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/admin/stats").mock(return_value=httpx.Response(200, json=STATS_JSON))
        stats = await client.admin_stats()
    assert isinstance(stats, StatsView)
    assert stats.users_total == 10
    assert stats.reports_pending == 3


async def test_forbidden_envelope_becomes_api_error(client: SpotdlClient) -> None:
    envelope = {"code": "forbidden", "message": "admins only"}
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/admin/stats").mock(return_value=httpx.Response(403, json=envelope))
        with pytest.raises(ApiError) as excinfo:
            await client.admin_stats()
    assert excinfo.value.code.value == "forbidden"
    assert excinfo.value.status == 403
