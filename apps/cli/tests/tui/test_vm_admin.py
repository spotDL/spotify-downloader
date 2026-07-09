"""``AdminViewModel`` — reports queue + approve/reject + stats, gated by is_admin."""

from __future__ import annotations

from uuid import uuid4

import pytest
from spotdl_cli.viewmodels.admin import AdminViewModel
from spotdl_cli.viewmodels.base import LoadState

from .fakes import FakeSpotdlClient, make_report, make_session, make_stats


def _admin(client: FakeSpotdlClient) -> AdminViewModel:
    return AdminViewModel(client, make_session(is_admin=True))


async def test_load_reports_maps_rows() -> None:
    client = FakeSpotdlClient()
    report_id = uuid4()
    client.admin_reports_list = [make_report(id=report_id, reason="wrong title")]
    result = await _admin(client).load_reports(status="pending")

    assert result.state is LoadState.READY
    assert result.data is not None
    (row,) = result.data
    assert row.id == report_id
    assert row.reason == "wrong title"
    assert client.calls[-1] == ("admin_reports", (), {"status": "pending"})


async def test_approve_and_reject() -> None:
    client = FakeSpotdlClient()
    report_id = uuid4()
    client.report_result = make_report(id=report_id, status="approved")
    approved = await _admin(client).approve(report_id, "looks good")
    assert approved.state is LoadState.READY
    assert approved.data is not None
    assert approved.data.status == "approved"
    assert client.calls[-1] == ("approve_report", (report_id,), {"note": "looks good"})

    client.report_result = make_report(id=report_id, status="rejected")
    rejected = await _admin(client).reject(report_id, None)
    assert rejected.data is not None
    assert rejected.data.status == "rejected"


async def test_stats_maps_row() -> None:
    client = FakeSpotdlClient()
    client.stats_result = make_stats()
    result = await AdminViewModel(client, make_session(is_admin=True, matcher_version="m9")).stats()

    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.users == 10
    assert result.data.matches == 20
    assert result.data.pending_reports == 3
    assert result.data.matcher_version == "m9"


@pytest.mark.parametrize("action", ["load_reports", "approve", "reject", "stats"])
async def test_non_admin_refuses_without_client_call(action: str) -> None:
    client = FakeSpotdlClient()
    vm = AdminViewModel(client, make_session(is_admin=False))

    if action == "load_reports":
        result = await vm.load_reports()
    elif action == "approve":
        result = await vm.approve(uuid4(), None)
    elif action == "reject":
        result = await vm.reject(uuid4(), None)
    else:
        result = await vm.stats()

    assert result.state is LoadState.ERROR
    assert client.calls == []
