"""Pilot tests for the admin-lite reports queue (Plan 9 Task 10).

Runs headless via ``App.run_test`` with an admin fake session (a stored token whose
``me`` reports ``is_admin``). The contract: list pending reports + a stats panel from
``AdminViewModel``; ``a``/``x`` approve/reject the focused report and update its row;
and the section stays unreachable for a non-admin (re-asserting the Task 4 gate).
"""

from __future__ import annotations

from uuid import uuid4

from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.viewmodels.factory import ViewModelFactory
from textual.widgets import DataTable, Static

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import FakeSpotdlClient, make_report, make_stats, make_user

_ORIGIN = "https://api.example.test"
_TRANSPORT = "remote · api.example.test"


def _factory(
    client: FakeSpotdlClient | None = None,
    creds: FakeCredentialStore | None = None,
) -> ViewModelFactory:
    return ViewModelFactory(
        client if client is not None else FakeSpotdlClient(),
        creds if creds is not None else FakeCredentialStore(),
        FakeConfigStore(),
        server_origin=_ORIGIN,
        transport_label=_TRANSPORT,
    )


def _admin_client() -> tuple[FakeSpotdlClient, FakeCredentialStore]:
    client = FakeSpotdlClient()
    creds = FakeCredentialStore()
    creds.store_token(_ORIGIN, "tok", "admin@example.com")
    client.users_by_token["tok"] = make_user(email="admin@example.com", is_admin=True)
    client.stats_result = make_stats()
    return client, creds


async def test_lists_pending_reports_and_stats() -> None:
    client, creds = _admin_client()
    client.admin_reports_list = [make_report(id=uuid4(), reason="wrong title")]
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("5")
        assert app.current_mode == "admin"
        await pilot.pause()
        assert app.screen.query_one("#admin-reports", DataTable).row_count == 1
        assert "matcher m1" in str(app.screen.query_one("#admin-stats", Static).render())


async def test_approve_updates_focused_row() -> None:
    client, creds = _admin_client()
    report_id = uuid4()
    client.admin_reports_list = [make_report(id=report_id, status="pending", reason="x")]
    client.report_result = make_report(id=report_id, status="resolved", reason="x")
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("5")
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        assert client.called("approve_report")
        row = app.screen.query_one("#admin-reports", DataTable).get_row_at(0)
        assert "resolved" in row


async def test_reject_updates_focused_row() -> None:
    client, creds = _admin_client()
    report_id = uuid4()
    client.admin_reports_list = [make_report(id=report_id, status="pending", reason="x")]
    client.report_result = make_report(id=report_id, status="rejected", reason="x")
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("5")
        await pilot.pause()
        await pilot.press("x")
        await pilot.pause()
        assert client.called("reject_report")
        row = app.screen.query_one("#admin-reports", DataTable).get_row_at(0)
        assert "rejected" in row


async def test_admin_section_unreachable_for_non_admin() -> None:
    app = SpotdlApp(_factory())  # guest session: is_admin False
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("5")  # gated off — no-op (CONTRACT F, re-asserted)
        assert app.current_mode == "home"
