"""Textual screens for SpotDL CLI."""

from spotdl_cli.screens.album import AlbumScreen
from spotdl_cli.screens.artist import ArtistScreen
from spotdl_cli.screens.main import MainScreen
from spotdl_cli.screens.onboarding import OnboardingScreen, should_show_onboarding
from spotdl_cli.screens.playlist import PlaylistScreen
from spotdl_cli.screens.queue import QueueScreen
from spotdl_cli.screens.settings import SettingsScreen
from spotdl_cli.screens.track import TrackScreen

__all__ = [
    "AlbumScreen",
    "ArtistScreen",
    "MainScreen",
    "OnboardingScreen",
    "PlaylistScreen",
    "QueueScreen",
    "SettingsScreen",
    "TrackScreen",
    "should_show_onboarding",
]
