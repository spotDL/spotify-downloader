"""``ConnectionViewModel`` — probe the server + rewrite the connection target (§3).

The connect screen's data source. :meth:`probe` times a ``/config`` round-trip into a
:class:`ProbeResult` (reachable, latency, mode, feature flags) — always returning a
result, never raising, so an unreachable server renders inline rather than as a
toast. The ``switch_*`` methods rewrite ``api_url``/``offline`` through the
``ConfigStore`` and return the ``(api_url, offline)`` primitives the app hands to its
``rebuild_client`` seam (this layer is framework- and client-free, CONTRACT I, so it
persists config but never builds a client).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from spotdl_cli.config import DEFAULT_API_URL
from spotdl_cli.errors import ApiError
from spotdl_cli.viewmodels.base import as_connection_error, describe_error
from spotdl_cli.viewmodels.protocol import ConfigStore, SpotdlClientProtocol


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """The outcome of a ``/config`` probe against the current transport."""

    reachable: bool
    latency_ms: int | None = None
    mode: str | None = None
    matcher_version: str | None = None
    auth: bool = False
    voting: bool = False
    downloads: bool = False
    library: bool = False
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ConnectionState:
    """The persisted connection target, as the connect screen shows it."""

    api_url: str
    offline: bool
    origin: str


class ConnectionViewModel:
    def __init__(
        self,
        client: SpotdlClientProtocol,
        store: ConfigStore,
        *,
        server_origin: str,
        transport_label: str,
    ) -> None:
        self._client = client
        self._store = store
        self._server_origin = server_origin
        self._transport_label = transport_label

    @property
    def transport_label(self) -> str:
        return self._transport_label

    def current(self) -> ConnectionState:
        cfg = self._store.load()
        return ConnectionState(
            api_url=str(cfg.api_url), offline=bool(cfg.offline), origin=self._server_origin
        )

    async def probe(self) -> ProbeResult:
        """Time a ``/config`` call; on any transport/API error report unreachable."""
        start = time.monotonic()
        try:
            config = await self._client.config()
        except ApiError as exc:
            return ProbeResult(reachable=False, reason=describe_error(exc).message)
        except Exception as exc:  # noqa: BLE001 — narrowed to transport failures
            connection = as_connection_error(exc)
            if connection is None:
                raise
            return ProbeResult(reachable=False, reason=connection.message)
        latency_ms = int((time.monotonic() - start) * 1000)
        return ProbeResult(
            reachable=True,
            latency_ms=latency_ms,
            mode=config.mode,
            matcher_version=config.matcher_version,
            auth=config.features.auth,
            voting=config.features.voting,
            downloads=config.features.downloads,
            library=config.features.library,
        )

    # -- target switching (persist, then hand primitives to the app) ----------

    def switch_community(self) -> tuple[str, bool]:
        return self._apply(api_url=DEFAULT_API_URL, offline=False)

    def switch_self_hosted(self, url: str) -> tuple[str, bool]:
        """Persist a validated self-hosted URL. Raises ``ValueError`` if invalid."""
        error = validate_self_hosted(url)
        if error is not None:
            raise ValueError(error)
        return self._apply(api_url=url.strip().rstrip("/"), offline=False)

    def go_offline(self) -> tuple[str, bool]:
        return self._apply(api_url=self._store.load().api_url, offline=True)

    def _apply(self, *, api_url: str, offline: bool) -> tuple[str, bool]:
        cfg = self._store.load()
        self._store.save(cfg.model_copy(update={"api_url": api_url, "offline": offline}))
        return api_url, offline


def validate_self_hosted(url: str) -> str | None:
    """Return a one-line reason the URL is unusable, or ``None`` when it is valid."""
    candidate = url.strip()
    if not candidate:
        return "enter a server URL"
    parts = urlsplit(candidate)
    if parts.scheme not in ("http", "https"):
        return "URL must start with http:// or https://"
    if not parts.netloc:
        return "URL is missing a host"
    return None
