"""``spotdl tui`` — the interactive terminal UI (Plan 9 Task 11).

The single construction site that wires the Plan 9 TUI: it builds a
:class:`~spotdl_cli.client.SpotdlClient` over the connectivity policy, wraps Plan 8's
``config.py`` in the ``CredentialStore``/``ConfigStore`` adapters the view-models
expect, bundles them into a :class:`~spotdl_cli.viewmodels.factory.ViewModelFactory`
(CONTRACT A), and runs :class:`~spotdl_cli.tui.app.SpotdlApp` (CONTRACT C).

Layering: this module is the bridge between the client/transport half and the
``tui``/``viewmodels`` presentation half. The ``tui`` package itself may never import
the client, transport, or generated code (import-linter ``tui_presentation`` + the
AST guard in ``tests/tui/test_import_guards.py``); it reaches the server only through
the view-models the factory hands it. Downloads always run on the embedded transport
(``need_downloads=True``, CONTRACT C rule 3); ``--offline`` forces the metadata
transport embedded too. ``from_config``'s context manager closes both transports on
exit, so the TUI shuts down cleanly even if the app raises.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

import typer

from spotdl_cli import config as _config
from spotdl_cli.client import DEFAULT_API_URL, RemoteTransport, SpotdlClient
from spotdl_cli.config import CliConfig
from spotdl_cli.errors import ApiError, render_api_error
from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.viewmodels.factory import ViewModelFactory


class _CredentialStoreAdapter:
    """A ``CredentialStore`` over Plan 8's origin-keyed ``credentials.toml``."""

    def get_token(self, origin: str) -> str | None:
        cred = _config.get_token(origin)
        return cred.token if cred is not None else None

    def store_token(self, origin: str, token: str, email: str) -> None:
        _config.store_token(origin, token, email=email)

    def delete_token(self, origin: str) -> None:
        _config.delete_token(origin)


class _ConfigStoreAdapter:
    """A ``ConfigStore`` over Plan 8's ``config.toml`` load/save."""

    def load(self) -> CliConfig:
        return _config.load_config()

    def save(self, cfg: CliConfig) -> None:
        _config.save_config(cfg)


def _server_origin(api_url: str) -> str:
    """The ``scheme://netloc`` credential-store key for ``api_url``.

    Mirrors ``commands/auth.py``'s origin derivation so a token stored by
    ``spotdl auth login`` is found by the TUI's ``AppStateViewModel``.
    """
    parts = urlsplit(api_url)
    if not parts.scheme or not parts.netloc:
        return api_url
    return f"{parts.scheme}://{parts.netloc}"


def _transport_label(client: SpotdlClient, *, offline: bool, api_url: str) -> str:
    """A human label for the resolution transport, shown in the status bar.

    Reads the transport the policy actually selected (remote when reachable, else
    the embedded fallback) rather than assuming the request, so the label stays
    honest when a silent fallback happens.
    """
    resolution = getattr(client, "_resolution", None)
    if isinstance(resolution, RemoteTransport):
        return f"remote · {urlsplit(api_url).netloc or api_url}"
    return "offline · embedded" if offline else "embedded (server unreachable)"


def build_factory(client: SpotdlClient, cfg: CliConfig, *, offline: bool) -> ViewModelFactory:
    """Bundle the client + config-backed stores into the one ``ViewModelFactory``.

    Split out from :func:`_run` so the end-to-end pilot can drive ``SpotdlApp`` with
    this exact wiring over a fake client (``run_test``), no real transport involved.
    """
    api_url = str(getattr(cfg, "api_url", None) or DEFAULT_API_URL)
    return ViewModelFactory(
        client,
        _CredentialStoreAdapter(),
        _ConfigStoreAdapter(),
        server_origin=_server_origin(api_url),
        transport_label=_transport_label(client, offline=offline, api_url=api_url),
    )


@asynccontextmanager
async def _open_client(cfg: CliConfig, *, offline: bool) -> AsyncIterator[SpotdlClient]:
    """Boot the TUI's client (metadata per policy, downloads always embedded).

    Production seam: the pilot patches this to inject a fake client at the
    ``from_config`` boundary without a real terminal or network.
    """
    async with SpotdlClient.from_config(cfg, offline=offline, need_downloads=True) as client:
        yield client


async def _run_app(factory: ViewModelFactory) -> None:
    """Run ``SpotdlApp`` to completion (seam: patched to skip the real terminal)."""
    await SpotdlApp(factory).run_async()


async def _run(cfg: CliConfig, *, offline: bool) -> None:
    """Open the client, build the factory, and run the app to completion."""
    async with _open_client(cfg, offline=offline) as client:
        await _run_app(build_factory(client, cfg, offline=offline))


def tui(
    offline: bool = typer.Option(
        False, "--offline", help="Use the embedded server for metadata (no network)."
    ),
) -> None:
    """Launch the interactive terminal UI."""
    cfg = _config.load_config()
    effective_offline = bool(offline or getattr(cfg, "offline", False))
    try:
        asyncio.run(_run(cfg, offline=effective_offline))
    except ApiError as exc:
        # A dead server / rejected startup call exits with the CONTRACT E code
        # instead of dumping a Textual traceback.
        raise SystemExit(render_api_error(exc)) from exc


def register(app: typer.Typer) -> None:
    """Attach ``tui`` to the root Typer app."""
    app.command("tui")(tui)
