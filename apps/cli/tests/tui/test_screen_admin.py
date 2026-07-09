"""Pilot tests for the admin console (Plan 9 Task 10, redesign §4).

Runs headless via ``App.run_test`` with an admin fake session (a stored token whose
``me`` reports ``is_admin``). The contract: three tabs — Stats (a StatCard grid),
Reports (the pending queue, ``a``/``x`` approve/reject the focused row through an
optional-note prompt modal), and Users (a read-only paginated roster). The section
stays unreachable for a non-admin (re-asserting the Task 4 gate).
"""

from __future__ import annotations

from uuid import uuid4

from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.tui.widgets.patterns import StatCard
from spotdl_cli.viewmodels.factory import ViewModelFactory
from textual.widgets import Button, DataTable, Input, Static, TabbedContent, TabPane

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import FakeSpotdlClient, make_admin_user, make_report, make_stats, make_user

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


async def _goto_admin(pilot: object, app: SpotdlApp) -> None:
    await pilot.pause()  # type: ignore[attr-defined]
    await pilot.press("6")  # type: ignore[attr-defined]
    assert app.current_mode == "admin"
    await pilot.pause()  # type: ignore[attr-defined]


async def _activate(app: SpotdlApp, pilot: object, tab: str) -> None:
    app.screen.query_one("#admin-tabs", TabbedContent).active = tab
    await pilot.pause()  # type: ignore[attr-defined]


async def test_three_tabs_stats_reports_users() -> None:
    client, creds = _admin_client()
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_admin(pilot, app)
        titles = {pane.id for pane in app.screen.query(TabPane)}
        assert titles == {"tab-stats", "tab-reports", "tab-users"}


async def test_stats_render_as_cards() -> None:
    client, creds = _admin_client()
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_admin(pilot, app)
        cards = app.screen.query(StatCard)
        assert len(cards) == 4
        rendered = " ".join(str(card.render()) for card in cards)
        assert "10" in rendered  # users_total from make_stats


async def test_lists_pending_reports() -> None:
    client, creds = _admin_client()
    client.admin_reports_list = [make_report(id=uuid4(), reason="wrong title")]
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_admin(pilot, app)
        assert app.screen.query_one("#admin-reports", DataTable).row_count == 1


async def test_approve_with_note_updates_row() -> None:
    client, creds = _admin_client()
    report_id = uuid4()
    client.admin_reports_list = [make_report(id=report_id, status="pending", reason="x")]
    client.report_result = make_report(id=report_id, status="resolved", reason="x")
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_admin(pilot, app)
        await _activate(app, pilot, "tab-reports")
        await pilot.press("a")
        await pilot.pause()  # the note modal mounts
        app.screen.query_one("#note-input", Input).value = "looks good"
        await pilot.click("#note-submit")
        await pilot.pause()
        await pilot.pause()
        assert client.calls[-1] == ("approve_report", (report_id,), {"note": "looks good"})
        row = app.screen.query_one("#admin-reports", DataTable).get_row_at(0)
        assert "resolved" in row


async def test_reject_modal_cancel_makes_no_call() -> None:
    client, creds = _admin_client()
    report_id = uuid4()
    client.admin_reports_list = [make_report(id=report_id, status="pending", reason="x")]
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_admin(pilot, app)
        await _activate(app, pilot, "tab-reports")
        await pilot.press("x")
        await pilot.pause()  # the note modal mounts
        await pilot.click("#note-cancel")
        await pilot.pause()
        await pilot.pause()
        assert not client.called("reject_report")


async def test_users_tab_paginates() -> None:
    client, creds = _admin_client()
    client.admin_users_list = [make_admin_user(email=f"u{i}@example.com") for i in range(25)]
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await _goto_admin(pilot, app)
        await _activate(app, pilot, "tab-users")
        table = app.screen.query_one("#admin-users", DataTable)
        assert table.row_count == 20
        count = app.screen.query_one("#users-count", Static)
        assert "1–20 of 25" in str(count.render())
        assert app.screen.query_one("#users-prev", Button).disabled is True
        await pilot.click("#users-next")
        await pilot.pause()
        assert table.row_count == 5
        assert "21–25 of 25" in str(count.render())
        assert app.screen.query_one("#users-next", Button).disabled is True


async def test_admin_section_unreachable_for_non_admin() -> None:
    app = SpotdlApp(_factory())  # guest session: is_admin False
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("6")  # gated off — no-op (CONTRACT F, re-asserted)
        assert app.current_mode == "home"
