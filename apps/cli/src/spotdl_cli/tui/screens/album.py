"""``AlbumScreen`` — the album variant of :class:`CollectionScreen` (CONTRACT C)."""

from __future__ import annotations

from spotdl_cli.tui.screens.collection import CollectionScreen


class AlbumScreen(CollectionScreen):
    KIND = "album"
