"""
Command palette provider for spotDL, inspired by OpenCode.
"""

from functools import partial
from typing import Any, Callable, Dict

from textual.command import DiscoveryHit, Hit, Hits, Provider

from spotdl.console.tui import i18n
from spotdl.console.tui.navigation.appbar import refresh_all_screens
from spotdl.console.tui.user_presets import load_presets

TR = i18n.tr


class SpotdlCommands(Provider):
    """
    Command provider offering fuzzy actions and navigation across spotDL.
    """

    async def discover(self) -> Hits:
        """
        Commands shown before typing a query.
        """

        for title, help_text, action in self._get_commands():
            yield DiscoveryHit(
                display=title,
                command=action,
                help=help_text,
            )

    async def search(self, query: str) -> Hits:
        """
        Search commands using Textual fuzzy matcher.
        """

        matcher = self.matcher(query)
        for title, help_text, action in self._get_commands():
            score = matcher.match(title)
            if score > 0:
                yield Hit(
                    score=score,
                    match_display=matcher.highlight(title),
                    command=action,
                    help=help_text,
                )

    def _get_commands(self) -> list[tuple[str, str, Callable[[], Any]]]:
        """
        Build the list of active commands.
        """

        app = self.app
        commands: list[tuple[str, str, Callable[[], Any]]] = [
            (
                f"{TR('commands.nav_home')}",
                TR("commands.nav_home_help"),
                partial(self._nav_to, "home"),
            ),
            (
                f"{TR('commands.nav_download')}",
                TR("commands.nav_download_help"),
                partial(self._nav_to, "download"),
            ),
            (
                f"{TR('commands.nav_downloads')}",
                TR("commands.nav_downloads_help"),
                partial(self._nav_to, "downloads"),
            ),
            (
                f"{TR('commands.nav_history')}",
                TR("commands.nav_history_help"),
                partial(self._nav_to, "history"),
            ),
            (
                f"{TR('commands.nav_settings')}",
                TR("commands.nav_settings_help"),
                partial(self._nav_to, "settings"),
            ),
            (
                f"{TR('commands.nav_builder')}",
                TR("commands.nav_builder_help"),
                partial(self._nav_to, "builder"),
            ),
            (
                f"{TR('commands.nav_guide')}",
                TR("commands.nav_guide_help"),
                partial(self._nav_to, "guide"),
            ),
            (
                f"{TR('commands.nav_web')}",
                TR("commands.nav_web_help"),
                partial(self._nav_to, "web"),
            ),
            (
                f"{TR('commands.nav_setup')}",
                TR("commands.nav_setup_help"),
                partial(self._nav_to, "setup"),
            ),
            (
                f"{TR('commands.lang_en')}",
                TR("commands.lang_en_help"),
                partial(self._switch_language, "en"),
            ),
            (
                f"{TR('commands.lang_es')}",
                TR("commands.lang_es_help"),
                partial(self._switch_language, "es"),
            ),
            (
                f"{TR('commands.app_exit')}",
                TR("commands.app_exit_help"),
                partial(app.exit),
            ),
        ]

        # Add preset activation commands
        presets = load_presets()
        for name in presets:
            preset_title = f"{TR('commands.apply_preset')}: {name.capitalize()}"
            preset_help = TR("commands.apply_preset_help", name=name)
            commands.append(
                (
                    preset_title,
                    preset_help,
                    partial(self._apply_preset_and_open, name),
                )
            )

        return commands

    def _nav_to(self, target: str) -> None:
        """
        Navigate to a target screen.
        """

        # pylint: disable=import-outside-toplevel
        from spotdl.console.tui.screens.download.downloads import DownloadsScreen
        from spotdl.console.tui.screens.download.history_screen import HistoryScreen
        from spotdl.console.tui.screens.download.query import QueryScreen
        from spotdl.console.tui.screens.help import HelpScreen
        from spotdl.console.tui.screens.home import MainMenuScreen
        from spotdl.console.tui.screens.settings import SettingsScreen
        from spotdl.console.tui.screens.web import WebScreen
        from spotdl.console.tui.setup_app import open_setup_screen

        screens: Dict[str, Callable[[], Any]] = {
            "home": MainMenuScreen,
            "download": partial(QueryScreen, "download"),
            "downloads": DownloadsScreen,
            "history": HistoryScreen,
            "settings": SettingsScreen,
            "builder": partial(HelpScreen, initial_tab="help-builder"),
            "guide": partial(HelpScreen, initial_tab="help-guide"),
            "web": WebScreen,
        }

        if target == "setup":
            open_setup_screen(self.app)
        elif target in screens:
            self.app.push_screen(screens[target]())

    def _apply_preset_and_open(self, preset_name: str) -> None:
        """
        Open the download screen with the specified preset active.
        """

        # pylint: disable=import-outside-toplevel
        from spotdl.console.tui.screens.download.query import QueryScreen

        screen = QueryScreen("download")
        self.app.push_screen(screen)
        # Apply the preset once the screen is mounted
        self.app.call_later(self._set_screen_preset, screen, preset_name)

    @staticmethod
    def _set_screen_preset(screen: Any, preset_name: str) -> None:
        if hasattr(screen, "apply_preset_by_name"):
            screen.apply_preset_by_name(preset_name)

    def _switch_language(self, lang_code: str) -> None:
        """
        Switch the active language.
        """

        if lang_code in i18n.available_languages():
            i18n.set_language(lang_code)
            refresh_all_screens(self.app)
            if hasattr(self.app, "notify"):
                self.app.notify(
                    TR("commands.lang_switched"),
                    title="spotDL",
                    severity="information",
                )
