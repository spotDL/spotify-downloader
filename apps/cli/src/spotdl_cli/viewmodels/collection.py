"""``CollectionViewModel`` — album/artist/playlist detail + enqueue (CONTRACT A)."""

from __future__ import annotations

from uuid import UUID

from spotdl_cli.viewmodels.app_state import SessionSnapshot
from spotdl_cli.viewmodels.base import ErrorDisplay, Loadable, guard
from spotdl_cli.viewmodels.mappers import (
    album_header,
    artist_header,
    batch_ref,
    playlist_header,
    track_row,
)
from spotdl_cli.viewmodels.protocol import SpotdlClientProtocol
from spotdl_cli.viewmodels.types import BatchRef, CollectionDetail
from spotdl_cli.views import DownloadSubmit

_COLLECTION_KINDS = ("album", "artist", "playlist")

_DOWNLOAD_BLOCKED = ErrorDisplay(
    "downloads aren't available on this server", code=None, severity="error"
)
_NOT_LOADED = ErrorDisplay("no collection loaded yet", code=None, severity="error")


class CollectionViewModel:
    def __init__(self, client: SpotdlClientProtocol, session: SessionSnapshot) -> None:
        self._client = client
        self._session = session
        self._entity_id: UUID | None = None

    async def load(self, entity_type: str, entity_id: UUID) -> Loadable[CollectionDetail]:
        if entity_type not in _COLLECTION_KINDS:
            return Loadable.failed(
                ErrorDisplay(f"unknown collection type: {entity_type}", code=None, severity="error")
            )
        self._entity_id = entity_id
        return await guard(self._fetch(entity_type, entity_id))

    async def _fetch(self, entity_type: str, entity_id: UUID) -> CollectionDetail:
        if entity_type == "album":
            album = await self._client.album(entity_id)
            return CollectionDetail(
                header=album_header(album),
                kind="album",
                tracks=tuple(track_row(track) for track in album.tracks),
            )
        if entity_type == "artist":
            artist = await self._client.artist(entity_id)
            return CollectionDetail(
                header=artist_header(artist),
                kind="artist",
                tracks=tuple(track_row(track) for track in artist.tracks),
            )
        playlist = await self._client.playlist(entity_id)
        return CollectionDetail(
            header=playlist_header(playlist),
            kind="playlist",
            tracks=tuple(track_row(track) for track in playlist.tracks),
        )

    async def enqueue_all(self) -> Loadable[BatchRef]:
        if not self._session.can_download:
            return Loadable.failed(_DOWNLOAD_BLOCKED)
        if self._entity_id is None:
            return Loadable.failed(_NOT_LOADED)
        entity_id = self._entity_id

        async def _run() -> BatchRef:
            batch = await self._client.submit_download(DownloadSubmit(query=str(entity_id)))
            return batch_ref(batch)

        return await guard(_run())

    async def enqueue_track(self, track_id: UUID) -> Loadable[BatchRef]:
        if not self._session.can_download:
            return Loadable.failed(_DOWNLOAD_BLOCKED)

        async def _run() -> BatchRef:
            batch = await self._client.submit_download(DownloadSubmit(query=str(track_id)))
            return batch_ref(batch)

        return await guard(_run())
