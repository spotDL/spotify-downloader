"""Textual screens for SpotDL CLI."""

from spotdl_cli.screens.main import MainScreen
from spotdl_cli.screens.onboarding import OnboardingScreen, should_show_onboarding
from spotdl_cli.screens.queue import QueueScreen
from spotdl_cli.screens.settings import SettingsScreen

__all__ = [
    "MainScreen",
    "OnboardingScreen",
    "QueueScreen",
    "SettingsScreen",
    "should_show_onboarding",
]
