import pytest
from textual.widgets import Button, OptionList

from spotdl.console.tui import (
    HelpScreen,
    LanguageScreen,
    MainMenuScreen,
    QueryScreen,
    SpotdlApp,
    build_downloader_settings,
    i18n,
)
from spotdl.download.downloader import Downloader
from spotdl.utils.config import DOWNLOADER_OPTIONS


@pytest.fixture()
def app():
    return SpotdlApp(query=None)


def test_i18n_es_en_switch():
    i18n.set_language("es", persist=False)
    assert i18n.tr("menu.download") == (
        "Descargar música (canciones, álbumes, playlists o búsquedas)"
    )
    i18n.set_language("en", persist=False)
    assert i18n.tr("menu.title") == "Main menu"


def test_i18n_fallback():
    assert i18n.tr("clave.inexistente") == "clave.inexistente"


def test_i18n_interpolation():
    i18n.set_language("es", persist=False)
    assert i18n.tr("download.overall", done="1", total="3") == ("Progreso total: 1 / 3")


def test_i18n_language_persistence_fresh(tmp_path, monkeypatch):
    import spotdl.console.tui.i18n as i18n_module

    monkeypatch.setattr(i18n_module, "_LANGUAGE_FILE", tmp_path / "language")
    i18n_module.set_language("es")
    assert (tmp_path / "language").read_text(encoding="utf-8") == "es"
    i18n_module.init()
    assert i18n_module.get_language() == "es"


@pytest.mark.asyncio
async def test_menu_screen_starts(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        assert MainMenuScreen in [type(s) for s in app.screen_stack]
        labels = [b.label.plain for b in app.screen.query(Button)]
        assert (
            i18n.tr("home.btn_add_download") in labels
            or i18n.tr("home.new_download") in labels
        )
        assert any(
            i18n.tr("home.card_sync") in lbl or i18n.tr("menu.sync") in lbl
            for lbl in labels
        )


@pytest.mark.asyncio
async def test_query_screen_prefill(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(QueryScreen("download", prefill="https://example.com/track"))
        await pilot.pause()
        await pilot.pause()
        query_input = app.screen.query_one("Input")
        assert query_input.value == "https://example.com/track"
        assert query_input is not None


@pytest.mark.asyncio
async def test_query_screen_template_applies(app):
    from textual.widgets import Input, Select, Switch

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(QueryScreen("download"))
        await pilot.pause()
        await pilot.pause()
        template_select = app.screen.query_one("#template-select", Select)
        template_select.value = "studio"
        await pilot.pause()
        await pilot.pause()
        assert app.screen.query_one("#format-select", Select).value == "opus"
        assert app.screen.query_one("#bitrate-select", Select).value == "disable"
        assert app.screen.query_one("#threads-input", Input).value == "2"
        assert (
            app.screen.query_one("#only-verified-results-checkbox", Switch).value
            is True
        )
        assert app.screen.query_one("#generate-lrc-checkbox", Switch).value is False


@pytest.mark.asyncio
async def test_history_screen_navigation(app):
    from spotdl.console.tui.history import add_download_entry
    from spotdl.console.tui.screens.download.history_screen import HistoryScreen

    add_download_entry(
        "Test Playlist", "https://open.spotify.com/playlist/test", 10, 10, 0
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(HistoryScreen())
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, HistoryScreen)
        table = app.screen.query_one("#history-table")
        assert table.row_count >= 1
        app.screen.action_redownload()
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, QueryScreen)
        assert (
            app.screen.query_one("#query-input").value
            == "https://open.spotify.com/playlist/test"
        )


@pytest.mark.asyncio
async def test_query_screen_collects_threads(app):
    from textual.widgets import Input

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(QueryScreen("download"))
        await pilot.pause()
        await pilot.pause()
        app.screen.query_one("#threads-input", Input).value = "8"
        app.screen.query_one("#query-input", Input).value = "test query"
        options = app.screen._collect_options()
        assert options["threads"] == 8


@pytest.mark.asyncio
async def test_language_selection_rebuilds_menu(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(LanguageScreen())
        await pilot.pause()
        await pilot.pause()
        option_list = app.screen.query_one(OptionList)
        option_list.highlighted = 0
        option_list.action_select()
        await pilot.pause()
        await pilot.pause()
        assert i18n.get_language() == "es"
        labels = [b.label.plain for b in app.screen.query(Button)]
        assert (
            i18n.tr("home.btn_add_download") in labels
            or i18n.tr("home.new_download") in labels
        )


@pytest.mark.asyncio
async def test_help_screen_shows_commands(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(HelpScreen())
        await pilot.pause()
        await pilot.pause()
        markdown = app.screen.query_one("Markdown")
        assert "-nogui" in markdown.source


@pytest.mark.asyncio
async def test_popover_close_button(app):
    from spotdl.console.tui.navigation.menupopover import MenuPopover

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(MenuPopover())
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, MenuPopover)
        close_btn = app.screen.query_one("#popover-close-btn", Button)
        await pilot.click(close_btn)
        await pilot.pause()
        await pilot.pause()
        assert not isinstance(app.screen, MenuPopover)


@pytest.mark.asyncio
async def test_popover_click_outside_closes(app):
    from spotdl.console.tui.navigation.menupopover import MenuPopover

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(MenuPopover())
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, MenuPopover)
        await pilot.click(app.screen, offset=(1, 1))
        await pilot.pause()
        await pilot.pause()
        assert not isinstance(app.screen, MenuPopover)


@pytest.mark.asyncio
async def test_popover_click_inside_keeps_open(app):
    from spotdl.console.tui.navigation.menupopover import MenuPopover

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(MenuPopover())
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, MenuPopover)
        card = app.screen.query_one("#popover-card")
        await pilot.click(card)
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, MenuPopover)


def test_downloader_settings_simple_tui():
    settings = build_downloader_settings(
        {
            "audio_providers": ["youtube-music"],
            "lyrics_providers": ["genius"],
            "format": "opus",
            "bitrate": "320k",
            "threads": 4,
            "output_dir": None,
            "save_file": None,
        }
    )
    assert settings["simple_tui"] is True
    assert settings["format"] == "opus"
    assert settings["bitrate"] == "320k"

    downloader = Downloader(dict(DOWNLOADER_OPTIONS))
    assert downloader.progress_handler.simple_tui is False
    downloader.progress_handler.update_callback = lambda tracker, message: None
    assert callable(downloader.progress_handler.update_callback)


@pytest.mark.asyncio
async def test_command_builder_live_update(app):
    from textual.widgets import Checkbox, Input, Select

    from spotdl.console.tui.screens.download.builder import CommandBuilder

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(HelpScreen("help-builder"))
        await pilot.pause()
        await pilot.pause()
        builder = app.screen.query_one(CommandBuilder)
        builder.query_one("#cmd-query", Input).value = (
            "https://open.spotify.com/track/123"
        )
        builder.query_one("#cmd-format", Select).value = "flac"
        builder.query_one("#cmd-generate-lrc", Checkbox).value = True
        builder.update_command()
        await pilot.pause()
        cmd = builder.command
        assert "spotdl" in cmd
        assert "--format flac" in cmd
        assert "--generate-lrc" in cmd
        assert "https://open.spotify.com/track/123" in cmd


@pytest.mark.asyncio
async def test_query_screen_operation_titles(app):
    from textual.widgets import Static

    from spotdl.console.tui.screens.download.query import QueryScreen

    i18n.set_language("es", persist=False)
    save_screen = QueryScreen("save")
    assert save_screen._get_title() == "Guardar canciones en un archivo spotdl"
    sync_screen = QueryScreen("sync")
    assert sync_screen._get_title() == "Sincronizar directorio con una playlist"
    download_screen = QueryScreen("download")
    assert download_screen._get_title() == "Descargar música"


@pytest.mark.asyncio
async def test_history_search_filter(app):
    from textual.widgets import DataTable, Input

    from spotdl.console.tui.history import add_download_entry, clear_history
    from spotdl.console.tui.screens.download.history_screen import HistoryScreen

    clear_history()
    add_download_entry("Alpha Song", "https://open.spotify.com/track/alpha", 1, 1, 0)
    add_download_entry("Beta Track", "https://open.spotify.com/track/beta", 2, 2, 0)

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(HistoryScreen())
        await pilot.pause()
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, HistoryScreen)
        table = screen.query_one("#history-table", DataTable)
        assert table.row_count >= 2

        search_input = screen.query_one("#history-search-input", Input)
        search_input.value = "Alpha"
        screen._apply_filter_and_sort()
        await pilot.pause()
        await pilot.pause()
        assert table.row_count == 1


def test_song_tracker_logger_suppression(monkeypatch):
    from unittest.mock import MagicMock

    from spotdl.download.progress_handler import ProgressHandler, SongTracker
    from spotdl.types.song import Song

    dummy_song = Song.from_missing_data(
        name="Test Song",
        artists=["Test Artist"],
        artist="Test Artist",
        genres=[],
        disc_number=1,
        disc_count=1,
        album_name="Test Album",
        album_artist="Test Artist",
        duration=200,
        year=2024,
        date="2024-01-01",
        track_number=1,
        tracks_count=1,
        song_id="123",
        explicit=False,
        publisher="",
        url="https://open.spotify.com/track/123",
        isrc="US123",
    )

    handler = ProgressHandler(simple_tui=True)
    handler.set_songs([dummy_song])
    tracker = SongTracker(handler, dummy_song)

    mock_logger = MagicMock()
    monkeypatch.setattr("spotdl.download.progress_handler.logger", mock_logger)

    # When update_callback is set, logger.info is suppressed
    handler.update_callback = lambda t, msg: None
    tracker.progress = 50
    tracker.update("Downloading")
    mock_logger.info.assert_not_called()

    # When update_callback is None, logger.info is called
    handler.update_callback = None
    tracker.progress = 75
    tracker.update("Converting")
    mock_logger.info.assert_called_once_with("%s: %s", tracker.song_name, "Converting")


def test_download_screen_copy_log(monkeypatch):
    from unittest.mock import MagicMock

    import spotdl.console.tui.screens.download.download as dl_mod
    from spotdl.console.tui.screens.download.download import DownloadScreen

    screen = DownloadScreen("download", songs=[], options={})
    screen._log_history = [
        "[10:00:00] Inició descarga de 5 canciones",
        "[10:00:05] ✓ Listo: Artist - Song 1",
    ]

    copied = []
    monkeypatch.setattr(dl_mod, "clipboard_copy", lambda text: copied.append(text))
    screen.query_one = MagicMock()

    screen.copy_log()

    assert len(copied) == 1
    assert "Strip(" not in copied[0]
    assert "Segment(" not in copied[0]
    assert "[10:00:00] Inició descarga de 5 canciones" in copied[0]
    assert "[10:00:05] ✓ Listo: Artist - Song 1" in copied[0]


@pytest.mark.asyncio
async def test_command_builder_fallback_audio(app):
    from textual.widgets import Select

    from spotdl.console.tui.screens.download.builder import CommandBuilder

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(HelpScreen("help-builder"))
        await pilot.pause()
        await pilot.pause()
        builder = app.screen.query_one(CommandBuilder)
        builder.query_one("#cmd-audio", Select).value = "youtube-music"
        builder.query_one("#cmd-fallback-audio", Select).value = "youtube"
        builder.update_command()
        await pilot.pause()
        cmd = builder.command
        assert "--audio youtube-music youtube" in cmd


def test_query_screen_fallback_audio_options():
    from unittest.mock import MagicMock

    from spotdl.console.tui.screens.download.query import QueryScreen

    screen = QueryScreen("download")

    def mock_query_one(selector, widget_type=None):
        mock_widget = MagicMock()
        if selector == "#query-input":
            mock_widget.value = "https://open.spotify.com/track/123"
        elif selector == "#threads-input":
            mock_widget.value = "4"
        elif selector == "#audio-select":
            mock_widget.value = "youtube-music"
        elif selector == "#fallback-audio-select":
            mock_widget.value = "youtube"
        elif selector == "#format-select":
            mock_widget.value = "mp3"
        elif selector == "#bitrate-select":
            mock_widget.value = "auto"
        else:
            mock_widget.value = None
        return mock_widget

    screen.query_one = mock_query_one
    options = screen._collect_options()
    assert options["audio_providers"] == ["youtube-music", "youtube"]


def _make_result(url, views=None, author="Uploader"):
    from spotdl.types.result import Result

    return Result(
        source="YouTube",
        url=url,
        verified=False,
        name="Song",
        result_id=url,
        author=author,
        duration=180,
        views=views,
    )


def test_downloader_search_primaries_does_not_run_generic_search():
    from unittest.mock import MagicMock

    downloader = Downloader(dict(DOWNLOADER_OPTIONS))
    found = MagicMock()
    found.search.return_value = "https://youtube.com/watch?v=primary"
    missing = MagicMock()
    missing.search.return_value = None
    downloader.audio_providers = [found, missing]

    assert downloader.search_primaries(MagicMock()) == [
        "https://youtube.com/watch?v=primary"
    ]

    downloader.audio_providers = [missing]
    assert downloader.search_primaries(MagicMock()) == []
    found.get_results.assert_not_called()
    missing.get_results.assert_not_called()


def test_downloader_search_lyrics_skips_failing_provider():
    from unittest.mock import MagicMock

    downloader = Downloader(dict(DOWNLOADER_OPTIONS))
    broken = MagicMock()
    broken.get_lyrics.side_effect = RuntimeError("blocked")
    working = MagicMock()
    working.get_lyrics.return_value = "lyrics"
    downloader.lyrics_providers = [broken, working]

    assert downloader.search_lyrics(MagicMock()) == "lyrics"

    working.get_lyrics.return_value = None
    assert downloader.search_lyrics(MagicMock()) is None


@pytest.mark.parametrize("unplayable", [True, False])
def test_get_best_result_ignores_unplayable_candidates(mocker, unplayable):
    from spotdl.providers.audio.base import AudioProvider, AudioProviderError

    provider = AudioProvider()
    top = _make_result("https://youtube.com/watch?v=top", author="Artist - Topic")
    popular = _make_result("https://youtube.com/watch?v=popular", views=1000)
    other = _make_result("https://youtube.com/watch?v=other", views=10)

    def fake_metadata(url, download=False):
        if unplayable:
            raise AudioProviderError(f"unavailable {url}")
        return {"view_count": 5000}

    mocker.patch.object(provider, "get_download_metadata", side_effect=fake_metadata)

    best, _ = provider.get_best_result({top: 90.0, popular: 85.0, other: 84.0})

    assert best == (popular if unplayable else top)


@pytest.mark.asyncio
async def test_appbar_buttons_open_menu_and_help(app):
    from spotdl.console.tui.navigation.menupopover import MenuPopover

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#appbar-menu")
        await pilot.pause()
        assert isinstance(app.screen, MenuPopover)

        await pilot.press("escape")
        await pilot.pause()
        await pilot.click("#appbar-help")
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_popover_builder_opens_help_on_builder_tab(app):
    from textual.widgets import TabbedContent

    from spotdl.console.tui.navigation.menupopover import MenuPopover

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(MenuPopover())
        await pilot.pause()
        await pilot.click("#popover-builder-btn")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        assert app.screen.query_one(TabbedContent).active == "help-builder"


@pytest.mark.asyncio
async def test_confirm_screen_keeps_cards_after_language_change(app):
    from spotdl.console.tui.navigation import refresh_all_screens
    from spotdl.console.tui.screens.download.confirm import ConfirmScreen

    options = {"format": "mp3", "bitrate": "auto", "m3u": "list.m3u8"}
    async with app.run_test() as pilot:
        await pilot.pause()
        i18n.set_language("en", persist=False)
        app.push_screen(ConfirmScreen("download", [], options))
        await pilot.pause()
        cards_before = len(app.screen.query(".confirm-card"))

        i18n.set_language("es", persist=False)
        refresh_all_screens(app)
        await pilot.pause()
        await pilot.pause()

        labels = [
            str(label.content) for label in app.screen.query(".confirm-card-label")
        ]
        assert len(app.screen.query(".confirm-card")) == cards_before == 6
        assert "FORMATO Y CALIDAD" in labels
    i18n.set_language("en", persist=False)


@pytest.mark.asyncio
async def test_history_columns_follow_language(app, monkeypatch):
    from textual.widgets import DataTable

    from spotdl.console.tui.navigation import refresh_all_screens
    from spotdl.console.tui.screens.download import history_screen

    monkeypatch.setattr(
        history_screen, "load_history", lambda: {"urls": [], "downloads": []}
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        i18n.set_language("en", persist=False)
        app.push_screen(history_screen.HistoryScreen())
        await pilot.pause()

        i18n.set_language("es", persist=False)
        refresh_all_screens(app)
        await pilot.pause()

        labels = [
            str(column.label)
            for column in app.screen.query_one(DataTable).columns.values()
        ]
        assert labels == [
            "Fecha / Hora",
            "Nombre / Título",
            "Pistas",
            "Estado",
            "Consulta / URL",
        ]
    i18n.set_language("en", persist=False)


@pytest.mark.asyncio
async def test_query_screen_blank_selects_and_bad_numbers(app):
    from textual.widgets import Input, Select

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(QueryScreen("download"))
        await pilot.pause()
        screen = app.screen
        screen.query_one("#query-input", Input).value = "test query"

        options = screen._collect_options()
        assert options["detect_formats"] == ["mp3"]
        assert options["album_type"] == "album"

        screen.query_one("#detect-formats-select", Select).clear()
        screen.query_one("#album-type-select", Select).clear()
        screen.query_one("#max-filename-length-input", Input).value = "abc"
        await pilot.pause()

        options = screen._collect_options()
        assert options["detect_formats"] is None
        assert options["album_type"] is None
        assert options["max_filename_length"] is None


@pytest.mark.asyncio
async def test_download_screen_back_returns_to_first_screen(app):
    from spotdl.console.tui.screens.download.download import DownloadScreen

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(QueryScreen("download"))
        app.push_screen(QueryScreen("save"))
        app.push_screen(DownloadScreen("download", [], {}, job_id="missing"))
        await pilot.pause()
        assert len(app.screen_stack) == 4

        await pilot.press("escape")
        await pilot.pause()
        assert len(app.screen_stack) == 1
        assert isinstance(app.screen, MainMenuScreen)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query, save_file, searched",
    [
        ("https://open.spotify.com/playlist/abc", "", False),
        ("https://open.spotify.com/playlist/abc", "list.spotdl", True),
        ("list.spotdl", "", True),
    ],
)
async def test_sync_requires_save_file_unless_query_is_one(
    app, monkeypatch, query, save_file, searched
):
    from textual.widgets import Input

    calls = []
    monkeypatch.setattr(
        QueryScreen, "_search_in_thread", lambda self, *args: calls.append(args)
    )
    monkeypatch.setattr(
        "spotdl.console.tui.screens.download.query.add_url_entry", lambda *args: None
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(QueryScreen("sync"))
        await pilot.pause()
        app.screen.query_one("#query-input", Input).value = query
        app.screen.query_one("#save-file-input", Input).value = save_file

        app.screen.start_search()

        assert bool(calls) is searched


def test_user_presets_persistence(tmp_path, monkeypatch):
    import spotdl.console.tui.user_presets as presets_mod

    fake_file = tmp_path / "tui_presets.json"
    monkeypatch.setattr(presets_mod, "PRESETS_FILE", fake_file)

    presets = presets_mod.load_presets()
    assert "balanced" in presets
    assert "studio" in presets

    presets_mod.save_single_preset(
        "dj_flac", {"format": "flac", "bitrate": "disable", "threads": "8"}
    )
    loaded = presets_mod.load_presets()
    assert "dj_flac" in loaded
    assert loaded["dj_flac"]["format"] == "flac"

    deleted = presets_mod.delete_custom_preset("dj_flac")
    assert deleted is True
    assert "dj_flac" not in presets_mod.load_presets()

    presets_mod.reset_presets_to_default()
    assert set(presets_mod.load_presets().keys()) == set(
        presets_mod.DEFAULT_PRESETS.keys()
    )


def test_user_settings_persistence(tmp_path, monkeypatch):
    import spotdl.console.tui.user_settings as settings_mod

    fake_file = tmp_path / "tui_settings.json"
    monkeypatch.setattr(settings_mod, "SETTINGS_FILE", fake_file)

    defaults = settings_mod.load_user_settings()
    assert defaults["threads"] == "4"

    settings_mod.save_user_settings({"threads": "12", "format": "opus"})
    loaded = settings_mod.load_user_settings()
    assert loaded["threads"] == "12"
    assert loaded["format"] == "opus"

    settings_mod.reset_user_settings()
    reset_loaded = settings_mod.load_user_settings()
    assert reset_loaded["threads"] == "4"


@pytest.mark.asyncio
async def test_settings_screen_mount_and_save(app, tmp_path, monkeypatch):
    from textual.widgets import Input

    import spotdl.console.tui.user_presets as presets_mod
    import spotdl.console.tui.user_settings as settings_mod
    from spotdl.console.tui.screens.settings import SettingsScreen

    monkeypatch.setattr(settings_mod, "SETTINGS_FILE", tmp_path / "tui_settings.json")
    monkeypatch.setattr(presets_mod, "PRESETS_FILE", tmp_path / "tui_presets.json")

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(SettingsScreen())
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)

        threads_input = app.screen.query_one("#set-threads-input", Input)
        threads_input.value = "8"
        save_btn = app.screen.query_one("#btn-save-all-settings", Button)
        save_btn.press()
        await pilot.pause()

        saved = settings_mod.load_user_settings()
        assert saved["threads"] == "8"


@pytest.mark.asyncio
async def test_command_palette_commands(app):
    from spotdl.console.tui.commands import SpotdlCommands

    async with app.run_test() as pilot:
        await pilot.pause()
        provider = SpotdlCommands(screen=app.screen)
        commands = provider._get_commands()
        command_titles = [c[0] for c in commands]

        assert any("Home" in t or "Inicio" in t for t in command_titles)
        assert any("Settings" in t or "Ajustes" in t for t in command_titles)
        assert any("Download" in t or "Descarga" in t for t in command_titles)
        assert any("Balanced" in t or "Equilibrado" in t for t in command_titles)


@pytest.mark.asyncio
async def test_help_guide_tab_displayed(app):
    from textual.widgets import Markdown

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(HelpScreen(initial_tab="help-guide"))
        await pilot.pause()
        md = app.screen.query_one("#help-guide-md", Markdown)
        assert md is not None


@pytest.mark.asyncio
async def test_downloads_screen_mounts(app):
    from textual.widgets import Static

    from spotdl.console.tui.screens import DownloadsScreen

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(DownloadsScreen())
        await pilot.pause()
        assert isinstance(app.screen, DownloadsScreen)
        status = app.screen.query_one("#downloads-status", Static)
        assert i18n.tr("downloads.empty") in str(status.render())


@pytest.mark.asyncio
async def test_appbar_shows_active_downloads(app):
    from textual.widgets import Static

    async with app.run_test() as pilot:
        await pilot.pause()
        app.downloads.aggregate = lambda: (2, 45)
        await pilot.pause(0.6)
        label = app.screen.query_one("#appbar-activity", Static)
        assert "2" in str(label.render())


@pytest.mark.asyncio
async def test_ui_renders_on_narrow_terminal(app):
    from spotdl.console.tui.screens import DownloadsScreen

    async with app.run_test(size=(60, 20)) as pilot:
        await pilot.pause()
        app.push_screen(DownloadsScreen())
        await pilot.pause()
        assert isinstance(app.screen, DownloadsScreen)


@pytest.mark.asyncio
async def test_history_screen_has_completion_actions(app):
    from spotdl.console.tui.screens.download.history_screen import HistoryScreen

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(HistoryScreen())
        await pilot.pause()
        assert app.screen.query_one("#history-retry-btn") is not None
        assert app.screen.query_one("#history-check-btn") is not None


@pytest.mark.asyncio
async def test_quit_without_downloads_exits(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.query_one("#appbar-quit", Button)
        await app.run_action("quit")
        await pilot.pause()
        assert not app.is_running


@pytest.mark.asyncio
async def test_quit_with_active_downloads_asks_first(app, monkeypatch):
    from spotdl.console.tui.widgets import ConfirmQuitModal

    monkeypatch.setattr(app.downloads, "active_count", lambda: 2)
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.run_action("quit")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmQuitModal)

        await pilot.click("#quit-no-btn")
        await pilot.pause()
        assert not isinstance(app.screen, ConfirmQuitModal)
        assert app.is_running

        await app.run_action("quit")
        await pilot.pause()
        await pilot.click("#quit-yes-btn")
        await pilot.pause()
        assert not app.is_running


def test_is_download_link():
    from spotdl.console.tui.widgets import is_download_link

    assert is_download_link("https://music.youtube.com/watch?v=abc")
    assert is_download_link("  http://youtu.be/abc ")
    assert not is_download_link("music.youtube.com/watch?v=abc")
    assert not is_download_link("javascript:alert(1)")
    assert not is_download_link("")


@pytest.mark.asyncio
async def test_failed_links_modal_returns_typed_links(app):
    from textual.widgets import Input

    from spotdl.console.tui.widgets import FailedLinksModal
    from spotdl.types.song import Song

    songs = [
        Song.from_missing_data(
            name=f"Song {index}",
            artists=["Artist"],
            artist="Artist",
            url=f"https://open.spotify.com/track/{index}",
        )
        for index in range(2)
    ]
    results = []
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(FailedLinksModal(songs), results.append)
        await pilot.pause()
        app.screen.query_one("#link-0", Input).value = "not a link"
        app.screen.query_one("#links-ok-btn", Button).press()
        await pilot.pause()
        assert results == []

        app.screen.query_one("#link-0", Input).value = "https://youtu.be/x"
        app.screen.query_one("#links-ok-btn", Button).press()
        await pilot.pause()

    assert results == [{"https://open.spotify.com/track/0": "https://youtu.be/x"}]
