"""Pilot tests for the connection flows (Plan 9 redesign §3, spec §5.1–5.5).

Headless through ``App.run_test()`` with a fake ``rebuild`` seam (no real client):
first-run onboarding lands on Connect; picking a target persists config, rebuilds,
and continues to Search; an involuntary embedded fallback lights the red dot + a
warning banner; a degraded resolve lights the yellow dot; and a nav-rail click
switches section.
"""

from __future__ import annotations

from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.tui.messages import NavSelected
from spotdl_cli.tui.widgets.nav_rail import NavRail
from spotdl_cli.viewmodels.factory import ViewModelFactory
from textual.widgets import Input, Static

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import FakeSpotdlClient, make_track

_ORIGIN = "https://api.example.test"


def _factory(
    client: FakeSpotdlClient | None = None,
    store: FakeConfigStore | None = None,
    *,
    label: str = "remote · api.example.test",
) -> ViewModelFactory:
    return ViewModelFactory(
        client if client is not None else FakeSpotdlClient(),
        FakeCredentialStore(),
        store if store is not None else FakeConfigStore(),
        server_origin=_ORIGIN,
        transport_label=label,
    )


def _recording_rebuild(store: FakeConfigStore):
    """A fake ``rebuild`` seam: record the switch, return a fresh offline/remote factory."""
    calls: list[tuple[str, bool]] = []

    async def rebuild(api_url: str, offline: bool) -> ViewModelFactory:
        calls.append((api_url, offline))
        label = "offline · embedded" if offline else "remote · api.example.test"
        return _factory(store=store, label=label)

    return rebuild, calls


async def test_first_run_opens_connect_then_offline_continues_to_search() -> None:
    store = FakeConfigStore()
    rebuild, calls = _recording_rebuild(store)
    app = SpotdlApp(_factory(store=store), rebuild=rebuild, first_run=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.current_mode == "connect"  # first run lands on onboarding
        await pilot.click("#use-offline")
        await pilot.pause()
        await pilot.pause()
        assert calls == [("https://api.spotdl.dev", True)]  # rebuilt offline
        assert store.saves[-1].offline is True  # persisted
        assert app.current_mode == "home"  # continued to Search


async def test_self_hosted_switch_rebuilds_with_entered_url() -> None:
    store = FakeConfigStore()
    rebuild, calls = _recording_rebuild(store)
    app = SpotdlApp(_factory(store=store), rebuild=rebuild)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("0")  # open the connect switcher
        await pilot.pause()
        app.screen.query_one("#selfhost-url", Input).value = "https://my.server:8000"
        await pilot.click("#use-selfhost")
        await pilot.pause()
        await pilot.pause()
        assert calls == [("https://my.server:8000", False)]
        assert app.current_mode == "home"


async def test_invalid_self_hosted_url_shows_inline_error_no_rebuild() -> None:
    store = FakeConfigStore()
    rebuild, calls = _recording_rebuild(store)
    app = SpotdlApp(_factory(store=store), rebuild=rebuild)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("0")
        await pilot.pause()
        app.screen.query_one("#selfhost-url", Input).value = "nonsense"
        await pilot.click("#use-selfhost")
        await pilot.pause()
        assert not calls  # never rebuilt
        error = str(app.screen.query_one("#selfhost-error", Static).render())
        assert "http" in error  # inline reason shown


async def test_remote_unreachable_lights_red_dot_and_banner() -> None:
    app = SpotdlApp(_factory(label="embedded (server unreachable)"))
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.connection_state == "unreachable"
        assert app.fallback_active is True
        assert any("unreachable" in n.message.lower() for n in app._notifications)  # banner toast
        rail = app.screen.query_one(NavRail)
        assert rail.dot_state == "unreachable"  # red dot


async def test_degraded_resolve_lights_yellow_dot() -> None:
    client = FakeSpotdlClient()
    client.search_results = [make_track(name="One More Time")]
    client.search_degraded = ["spotify"]
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.query_one(NavRail).dot_state == "ok"  # clean before search
        app.screen.query_one("#search-input", Input).value = "daft"
        await pilot.press("slash")
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.session is not None and app.session.degraded is True
        assert app.screen.query_one(NavRail).dot_state == "degraded"  # yellow dot


async def test_nav_rail_click_switches_section() -> None:
    app = SpotdlApp(_factory())
    async with app.run_test() as pilot:
        await pilot.pause()
        app.post_message(NavSelected("queue"))
        await pilot.pause()
        assert app.current_mode == "queue"


async def test_connect_screen_probe_flips_dot_when_unreachable() -> None:
    from spotdl_cli._generated.api.models.error_code import ErrorCode
    from spotdl_cli.errors import ApiError

    client = FakeSpotdlClient()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        client.errors["config"] = ApiError(ErrorCode.INTERNAL_ERROR, message="down")
        await pilot.press("0")  # connect screen probes on mount
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.connection_state == "unreachable"
        assert app.screen.query_one(NavRail).dot_state == "unreachable"
