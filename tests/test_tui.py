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
        "Descargar musica (tracks, albumes, playlists o busquedas)"
    )
    i18n.set_language("en", persist=False)
    assert i18n.tr("menu.title") == "Main menu"


def test_i18n_fallback():
    assert i18n.tr("clave.inexistente") == "clave.inexistente"


def test_i18n_interpolation():
    i18n.set_language("es", persist=False)
    assert i18n.tr("download.overall", done="1", total="3") == (
        "Progreso global: 1 / 3"
    )


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
        assert i18n.tr("home.new_download") in labels
        assert any(lbl.endswith(i18n.tr("menu.sync")) for lbl in labels)


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
        assert app.screen.query_one("#generate-lrc-checkbox", Switch).value is True


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
        assert i18n.tr("home.new_download") in labels


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
    from spotdl.console.tui.bar.menupopover import MenuPopover

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
    from spotdl.console.tui.bar.menupopover import MenuPopover

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
    from spotdl.console.tui.bar.menupopover import MenuPopover

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
