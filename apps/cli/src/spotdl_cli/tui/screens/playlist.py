"""``PlaylistScreen`` — the playlist variant of :class:`CollectionScreen` (CONTRACT C)."""

from __future__ import annotations

from spotdl_cli.tui.screens.collection import CollectionScreen


class PlaylistScreen(CollectionScreen):
    KIND = "playlist"
