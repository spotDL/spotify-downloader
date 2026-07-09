"""``spotdl server`` — run a long-lived server (selfhost by default).

Unlike ``web`` (embedded, loopback, browser), ``server`` runs a standalone
uvicorn process an operator points a reverse proxy or LAN clients at. It builds
``Settings`` from the ``--mode`` flag (the rest come from the ``SPOTDL_*`` env),
runs migrations, fails fast on an inconsistent download-auth config, then serves.
"""

from __future__ import annotations

import typer
import uvicorn
from spotdl_server.app import create_app
from spotdl_server.bootstrap import upgrade_to_head
from spotdl_server.settings import DeploymentMode, Settings


def _migrate(settings: Settings) -> None:
    """Bring the database to head (seam: patched in tests)."""
    upgrade_to_head(settings)


def server(
    mode: DeploymentMode = typer.Option(DeploymentMode.SELFHOST, "--mode", help="Deployment mode."),
    host: str = typer.Option("127.0.0.1", "--host", help="Interface to bind."),
    port: int = typer.Option(8800, "--port", help="Port to bind."),
) -> None:
    """Run a standalone spotdl server."""
    settings = Settings(mode=mode)
    _migrate(settings)
    # Fail fast before binding a socket on a nonsensical download-auth config.
    settings.require_download_auth_consistency()

    app = create_app(settings)
    uvicorn.run(app, host=host, port=port)


def register(app: typer.Typer) -> None:
    """Attach ``server`` to the root Typer app."""
    app.command("server")(server)
