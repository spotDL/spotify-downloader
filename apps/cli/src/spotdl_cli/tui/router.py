"""Entity navigation: an :class:`EntityRef` → the screen that shows it (CONTRACT C).

The app funnels every ``NavigateTo`` here. Target screens live in a registry that
later tasks fill (Task 6 track, Task 7 album/artist/playlist); an unregistered kind
resolves to a :class:`PlaceholderScreen`, so ``resolve`` → open works before those
screens exist. Kept import-light (no screen imports of its own beyond the base) to
avoid a screen ↔ router cycle — screens post messages, they never call the router.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

from spotdl_cli.tui.screens.base import PlaceholderScreen, SpotdlScreen
from spotdl_cli.tui.screens.track import TrackScreen
from spotdl_cli.viewmodels.types import EntityRef

if TYPE_CHECKING:
    from spotdl_cli.tui.app import SpotdlApp

# entity_type -> (id -> screen). Later tasks register the album/artist/playlist
# screens (Task 7); the track screen lands here in Task 6.
ENTITY_SCREENS: dict[str, Callable[[UUID], SpotdlScreen]] = {
    "track": TrackScreen,
}


def entity_screen(ref: EntityRef) -> SpotdlScreen:
    builder = ENTITY_SCREENS.get(ref.entity_type)
    if builder is not None:
        return builder(ref.id)
    return PlaceholderScreen(ref.entity_type, ref.title)


def open_entity(app: SpotdlApp, ref: EntityRef) -> None:
    """Push the screen for ``ref`` onto the current section's stack."""
    app.push_screen(entity_screen(ref))
