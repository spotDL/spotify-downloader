"""Pilot tests for the track screen + gauge/lyrics widgets (Plan 9 Task 6).

Headless ``App.run_test()`` over :class:`FakeSpotdlClient`. Contract (CONTRACT A/D):
the screen projects a ``TrackDetail`` into an :class:`EntityCard`, a list of
:class:`MatchGauge`, and a :class:`LyricsPane`; the widgets are dumb and emit
messages. Voting (``u``) runs ``TrackViewModel.vote_match`` and merges the fresh
tallies onto the gauge; it is inert when ``can_vote`` is False. ``m`` submits a
match URL, ``e`` enqueues (only when ``can_download``), ``[``/``]`` cycle lyrics
sources, and ``space`` follows synced lyrics. An ``ApiError`` on vote is a toast.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.errors import ApiError
from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.tui.screens.track import TrackScreen
from spotdl_cli.tui.widgets.entity_card import EntityCard
from spotdl_cli.tui.widgets.lyrics_pane import LyricsPane
from spotdl_cli.tui.widgets.match_gauge import MatchGauge
from spotdl_cli.viewmodels.factory import ViewModelFactory

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import (
    FakeSpotdlClient,
    make_config,
    make_features,
    make_lyrics,
    make_match,
    make_track,
)

_ORIGIN = "https://api.example.test"
_TRANSPORT = "remote · api.example.test"


def _factory(client: FakeSpotdlClient) -> ViewModelFactory:
    return ViewModelFactory(
        client,
        FakeCredentialStore(),
        FakeConfigStore(),
        server_origin=_ORIGIN,
        transport_label=_TRANSPORT,
    )


def _client_with_track(
    track_id: UUID,
    *,
    matches: list | None = None,
    lyrics: list | None = None,
    voting: bool = True,
    downloads: bool = True,
) -> FakeSpotdlClient:
    config = make_config(features=make_features(voting=voting, downloads=downloads))
    client = FakeSpotdlClient(config=config, download_config=config)
    client.tracks[str(track_id)] = make_track(id=track_id, name="Harder Better")
    client.matches_by_track[str(track_id)] = (
        matches if matches is not None else [make_match(provider="youtube")]
    )
    client.lyrics_by_track[str(track_id)] = lyrics if lyrics is not None else [make_lyrics()]
    return client


async def _mount_track(app: SpotdlApp, track_id: UUID) -> TrackScreen:
    from textual.pilot import Pilot  # noqa: F401 — typing only

    screen = TrackScreen(track_id)
    await app.push_screen(screen)
    return screen


async def test_mounts_card_gauges_and_pane() -> None:
    track_id = uuid4()
    client = _client_with_track(
        track_id,
        matches=[make_match(provider="youtube"), make_match(provider="soundcloud")],
    )
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _mount_track(app, track_id)
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert len(app.screen.query(EntityCard)) == 1
        assert len(app.screen.query(MatchGauge)) == 2
        assert len(app.screen.query(LyricsPane)) == 1
        card = app.screen.query_one(EntityCard)
        assert "Harder Better" in card.summary


async def test_vote_up_merges_fresh_tallies_onto_gauge() -> None:
    track_id = uuid4()
    match_id = uuid4()
    client = _client_with_track(
        track_id, matches=[make_match(id=match_id, provider="youtube", upvotes=4, downvotes=1)]
    )
    # Mimic the real façade: a vote returns tallies only (blank structural fields).
    client.vote_match_result = make_match(
        id=match_id, provider="", url="", score=0.0, upvotes=10, downvotes=2, net_score=8
    )
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _mount_track(app, track_id)
        await app.workers.wait_for_complete()
        await pilot.pause()

        gauge = app.screen.query_one(MatchGauge)
        gauge.focus()
        await pilot.press("u")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert client.calls[-1] == ("vote_match", (match_id, "up"), {})
        # fresh tallies applied, structural fields (provider) preserved from before
        assert "youtube" in gauge.summary
        assert "10" in gauge.summary and "2" in gauge.summary


async def test_gauge_has_no_vote_affordance_when_cannot_vote() -> None:
    track_id = uuid4()
    match_id = uuid4()
    client = _client_with_track(
        track_id, matches=[make_match(id=match_id, provider="youtube")], voting=False
    )
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _mount_track(app, track_id)
        await app.workers.wait_for_complete()
        await pilot.pause()

        gauge = app.screen.query_one(MatchGauge)
        assert gauge.can_vote is False
        gauge.focus()
        await pilot.press("u")  # the vote binding is absent — a no-op
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert not client.called("vote_match")


async def test_m_submits_a_match_url() -> None:
    track_id = uuid4()
    client = _client_with_track(track_id)
    client.submit_match_result = make_match(provider="youtube")
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _mount_track(app, track_id)
        await app.workers.wait_for_complete()
        await pilot.pause()

        await pilot.press("m")
        await pilot.pause()
        from textual.widgets import Input

        box = app.screen.query_one("#match-url", Input)
        box.value = "https://youtu.be/abc"
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert client.calls[-1] == ("submit_match", (track_id, "https://youtu.be/abc"), {})


async def test_e_enqueues_only_when_downloads_enabled() -> None:
    track_id = uuid4()
    from .fakes import make_batch

    client = _client_with_track(track_id, downloads=True)
    client.submit_download_result = make_batch()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _mount_track(app, track_id)
        await app.workers.wait_for_complete()
        await pilot.pause()
        await pilot.press("e")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert client.called("submit_download")


async def test_e_is_inert_when_downloads_disabled() -> None:
    track_id = uuid4()
    client = _client_with_track(track_id, downloads=False)
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _mount_track(app, track_id)
        await app.workers.wait_for_complete()
        await pilot.pause()
        await pilot.press("e")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert not client.called("submit_download")


async def test_bracket_keys_cycle_lyrics_sources() -> None:
    track_id = uuid4()
    synced = make_lyrics(kind="synced", source="musixmatch", text="[00:00.00]a\n[00:05.00]b")
    plain = make_lyrics(kind="plain", source="genius", text="a\nb")
    client = _client_with_track(track_id, lyrics=[synced, plain])
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _mount_track(app, track_id)
        await app.workers.wait_for_complete()
        await pilot.pause()

        pane = app.screen.query_one(LyricsPane)
        pane.focus()
        assert pane.choice is not None
        first_source = pane.choice.source  # synced sorts first
        await pilot.press("right_square_bracket")
        await pilot.pause()
        assert pane.choice is not None
        assert pane.choice.source != first_source
        await pilot.press("left_square_bracket")
        await pilot.pause()
        assert pane.choice is not None
        assert pane.choice.source == first_source


async def test_space_follow_highlights_active_synced_line() -> None:
    track_id = uuid4()
    synced = make_lyrics(kind="synced", source="musixmatch", text="[00:00.00]a\n[00:05.00]b")
    client = _client_with_track(track_id, lyrics=[synced])
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _mount_track(app, track_id)
        await app.workers.wait_for_complete()
        await pilot.pause()

        pane = app.screen.query_one(LyricsPane)
        pane.focus()
        pane.set_position(6000)
        assert pane.active_line is None  # not following yet
        await pilot.press("space")  # enable follow
        await pilot.pause()
        pane.set_position(6000)
        assert pane.active_line == 1


async def test_vote_api_error_toasts_without_crashing() -> None:
    track_id = uuid4()
    match_id = uuid4()
    client = _client_with_track(track_id, matches=[make_match(id=match_id, provider="youtube")])
    client.errors["vote_match"] = ApiError(ErrorCode.INTERNAL_ERROR, message="boom")
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _mount_track(app, track_id)
        await app.workers.wait_for_complete()
        await pilot.pause()

        gauge = app.screen.query_one(MatchGauge)
        gauge.focus()
        await pilot.press("u")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert app._notifications  # surfaced as a toast, screen still alive
        assert isinstance(app.screen, TrackScreen)
