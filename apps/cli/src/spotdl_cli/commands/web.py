"""``spotdl web`` — the local web UI (embedded server + browser).

Boots the embedded server (loopback, downloads on by mode), runs migrations, and
opens the browser at the SPA root. The server serves the bundled single-page app
from ``spotdl_server/webui`` (embedded into the wheel by ``make web-embed`` /
``make dist``); the app self-gates on ``GET /config``, so the same build serves
every deployment mode. Fully offline — no GitHub fetch (spec §8).
"""

from __future__ import annotations

import webbrowser

import typer
import uvicorn
from fastapi import FastAPI
from spotdl_server.app import create_app
from spotdl_server.bootstrap import upgrade_to_head
from spotdl_server.settings import DeploymentMode, Settings

from spotdl_cli.commands import _support


def build_web_app(settings: Settings) -> FastAPI:
    """Build the embedded app that serves the bundled SPA at ``/``.

    Thin factory so a test can drive the ASGI app without binding a socket. The
    SPA static mount lives in ``create_app`` (Plan 10, :func:`mount_webui`), so
    ``web`` boots exactly the app every deployment serves.
    """
    return create_app(settings)


def _migrate(settings: Settings) -> None:
    """Bring the embedded database to head (seam: patched in tests)."""
    upgrade_to_head(settings)


def web(
    host: str = typer.Option("127.0.0.1", "--host", help="Interface to bind."),
    port: int = typer.Option(8800, "--port", help="Port to bind."),
    open_browser: bool = typer.Option(
        True, "--open/--no-open", help="Open the web UI in a browser."
    ),
) -> None:
    """Run the local web UI (embedded server + browser)."""
    settings = Settings(mode=DeploymentMode.EMBEDDED)
    _migrate(settings)

    app = build_web_app(settings)

    url = f"http://{host}:{port}/"
    _support.console.print(f"serving the spotDL web UI at {url}")
    if open_browser:
        webbrowser.open(url)

    uvicorn.run(app, host=host, port=port)


def register(app: typer.Typer) -> None:
    """Attach ``web`` to the root Typer app."""
    app.command("web")(web)
