"""Entity navigation: an :class:`EntityRef` → the screen that shows it (CONTRACT C).

The app funnels every ``NavigateTo`` here. Target screens live in a registry that
later tasks fill (Task 6 track, Task 7 album/artist/playlist); an unregistered kind
resolves to a :class:`PlaceholderScreen`, so ``resolve`` → open works before those
screens exist. The collection screens are imported here to register, which is safe:
they post messages and never import the router, so no screen ↔ router cycle forms.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

from spotdl_cli.tui.screens.album import AlbumScreen
from spotdl_cli.tui.screens.artist import ArtistScreen
from spotdl_cli.tui.screens.base import PlaceholderScreen, SpotdlScreen
from spotdl_cli.tui.screens.playlist import PlaylistScreen
from spotdl_cli.tui.screens.track import TrackScreen
from spotdl_cli.viewmodels.types import EntityRef

if TYPE_CHECKING:
    from spotdl_cli.tui.app import SpotdlApp

# entity_type -> (id -> screen). All four entity kinds are registered.
ENTITY_SCREENS: dict[str, Callable[[UUID], SpotdlScreen]] = {
    "track": TrackScreen,
    "album": AlbumScreen,
    "artist": ArtistScreen,
    "playlist": PlaylistScreen,
}


def entity_screen(ref: EntityRef) -> SpotdlScreen:
    builder = ENTITY_SCREENS.get(ref.entity_type)
    if builder is not None:
        return builder(ref.id)
    return PlaceholderScreen(ref.entity_type, ref.title)


def open_entity(app: SpotdlApp, ref: EntityRef) -> None:
    """Push the screen for ``ref`` onto the current section's stack."""
    app.push_screen(entity_screen(ref))
