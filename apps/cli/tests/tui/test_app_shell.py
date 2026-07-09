"""Pilot tests for the Textual app shell (Plan 9 Task 4).

Everything runs headless through ``App.run_test()`` with a :class:`ViewModelFactory`
wired over :class:`FakeSpotdlClient` — no real client, server, network, or terminal.
The shell's contract: boot to Search with a populated status bar (CONTRACT C), gate
sections by ``SessionSnapshot`` flags (CONTRACT F), pop pushed screens on ``escape``,
open Help on ``?``, route ``NavigateTo`` (CONTRACT C), and turn an ``ErrorDisplay``
into a toast (CONTRACT G).
"""

from __future__ import annotations

from uuid import uuid4

from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.tui.messages import NavigateTo
from spotdl_cli.tui.screens.base import PlaceholderScreen
from spotdl_cli.tui.screens.help import HelpScreen
from spotdl_cli.tui.widgets.status_bar import StatusBar
from spotdl_cli.viewmodels.base import ErrorDisplay
from spotdl_cli.viewmodels.factory import ViewModelFactory
from spotdl_cli.viewmodels.types import EntityRef

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import FakeSpotdlClient, make_config, make_features, make_stats, make_user

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


def _admin_setup() -> tuple[FakeSpotdlClient, FakeCredentialStore]:
    client = FakeSpotdlClient()
    creds = FakeCredentialStore()
    creds.store_token(_ORIGIN, "tok", "admin@example.com")
    client.users_by_token["tok"] = make_user(email="admin@example.com", is_admin=True)
    # the admin section now mounts the real AdminScreen (Task 10), which loads stats.
    client.stats_result = make_stats()
    return client, creds


async def test_boots_to_home_with_populated_status_bar() -> None:
    app = SpotdlApp(_factory())
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.current_mode == "home"
        bar = app.screen.query_one(StatusBar)
        assert _TRANSPORT in bar.summary
        assert "self_host" in bar.summary  # mode
        assert "guest" in bar.summary  # not signed in


async def test_number_keys_switch_available_sections() -> None:
    app = SpotdlApp(_factory())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("2")  # queue — can_download True by default
        assert app.current_mode == "queue"
        await pilot.press("3")  # settings — always on
        assert app.current_mode == "settings"
        await pilot.press("1")  # back to search
        assert app.current_mode == "home"


async def test_queue_section_hidden_when_downloads_disabled() -> None:
    client = FakeSpotdlClient(download_config=make_config(features=make_features(downloads=False)))
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("2")  # queue gated off — no-op
        assert app.current_mode == "home"


async def test_admin_section_hidden_for_non_admin() -> None:
    app = SpotdlApp(_factory())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("5")  # admin gated off for a guest — no-op
        assert app.current_mode == "home"


async def test_admin_section_reachable_for_admin() -> None:
    client, creds = _admin_setup()
    app = SpotdlApp(_factory(client, creds))
    async with app.run_test() as pilot:
        await pilot.pause()
        bar = app.screen.query_one(StatusBar)
        assert "admin@example.com" in bar.summary  # signed-in identity shown
        await pilot.press("5")
        assert app.current_mode == "admin"


async def test_help_opens_and_escape_pops() -> None:
    app = SpotdlApp(_factory())
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app.screen_stack) == 1
        await pilot.press("?")
        assert isinstance(app.screen, HelpScreen)
        assert len(app.screen_stack) == 2
        await pilot.press("escape")
        await pilot.pause()
        assert len(app.screen_stack) == 1
        assert not isinstance(app.screen, HelpScreen)


async def test_escape_on_section_does_not_pop_base() -> None:
    app = SpotdlApp(_factory())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")  # nothing to pop; the section stays
        await pilot.pause()
        assert len(app.screen_stack) == 1
        assert app.current_mode == "home"


async def test_navigate_to_pushes_entity_screen() -> None:
    app = SpotdlApp(_factory())
    async with app.run_test() as pilot:
        await pilot.pause()
        ref = EntityRef(entity_type="track", id=uuid4(), title="One More Time")
        app.post_message(NavigateTo(ref))
        await pilot.pause()
        assert isinstance(app.screen, PlaceholderScreen)
        assert len(app.screen_stack) == 2
        await pilot.press("escape")  # escape returns from the entity to the section
        await pilot.pause()
        assert len(app.screen_stack) == 1


async def test_show_error_raises_toast() -> None:
    app = SpotdlApp(_factory())
    async with app.run_test() as pilot:
        await pilot.pause()
        app.show_error(
            ErrorDisplay("rate limited, retrying", code="rate_limited", severity="warning")
        )
        await pilot.pause()
        toasts = [(n.message, n.severity) for n in app._notifications]
        assert ("rate limited, retrying", "warning") in toasts


async def test_boot_load_failure_toasts_and_keeps_always_on_sections() -> None:
    from spotdl_cli._generated.api.models.error_code import ErrorCode
    from spotdl_cli.errors import ApiError

    client = FakeSpotdlClient()
    client.errors["config"] = ApiError(ErrorCode.INTERNAL_ERROR, message="boom")
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.current_mode == "home"  # always-on Search survives a failed boot
        assert app._notifications  # the failure surfaced as a toast
        await pilot.press("2")  # queue was gated off (no session) — no-op
        assert app.current_mode == "home"
