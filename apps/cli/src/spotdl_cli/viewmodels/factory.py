"""``ViewModelFactory`` — the one place client injection is wired (CONTRACT A).

The ``SpotdlApp`` holds a single factory bundling the ``client`` + ``creds`` +
``store`` + the current :class:`SessionSnapshot`; screens ask it for a constructed
view-model in ``on_mount`` and stay ignorant of how the client is built. The
factory grows one accessor per view-model as later tasks add them; Task 1 wires the
root :class:`AppStateViewModel` and the session it produces.
"""

from __future__ import annotations

from spotdl_cli.viewmodels.app_state import AppStateViewModel, SessionSnapshot
from spotdl_cli.viewmodels.collection import CollectionViewModel
from spotdl_cli.viewmodels.protocol import (
    ConfigStore,
    CredentialStore,
    SpotdlClientProtocol,
)
from spotdl_cli.viewmodels.search import SearchViewModel
from spotdl_cli.viewmodels.track import TrackViewModel


class ViewModelFactory:
    def __init__(
        self,
        client: SpotdlClientProtocol,
        creds: CredentialStore,
        store: ConfigStore,
        *,
        server_origin: str,
        transport_label: str,
    ) -> None:
        self._client = client
        self._creds = creds
        self._store = store
        self._server_origin = server_origin
        self._transport_label = transport_label
        self._session: SessionSnapshot | None = None

    @property
    def server_origin(self) -> str:
        return self._server_origin

    @property
    def session(self) -> SessionSnapshot:
        """The current session; set once ``AppStateViewModel.load`` has resolved."""
        if self._session is None:
            raise RuntimeError("session not loaded — call set_session after app_state().load()")
        return self._session

    def set_session(self, session: SessionSnapshot) -> None:
        self._session = session

    def app_state(self) -> AppStateViewModel:
        return AppStateViewModel(
            self._client,
            self._creds,
            server_origin=self._server_origin,
            transport_label=self._transport_label,
        )

    def search(self) -> SearchViewModel:
        return SearchViewModel(self._client)

    def track(self) -> TrackViewModel:
        return TrackViewModel(self._client, self.session)

    def collection(self) -> CollectionViewModel:
        return CollectionViewModel(self._client, self.session)
