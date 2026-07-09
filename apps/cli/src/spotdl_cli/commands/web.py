"""``spotdl web`` — the local web UI (embedded server + browser).

Boots the embedded server (loopback, downloads on by mode), runs migrations, and
opens the browser. The bundled single-page app ships in Plan 10; until then ``/``
serves a stub that points at the live API, so ``web`` is usable today (the API is
real) and gains the UI without a command change.
"""

from __future__ import annotations

import webbrowser

import typer
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from spotdl_server.app import create_app
from spotdl_server.bootstrap import upgrade_to_head
from spotdl_server.settings import DeploymentMode, Settings

from spotdl_cli.commands import _support

_STUB_TITLE = "spotdl"


def _stub_html(api_url: str) -> str:
    return (
        "<!doctype html><html><head><title>spotdl</title></head>"
        "<body style='font-family:sans-serif;max-width:40rem;margin:4rem auto'>"
        "<h1>spotdl</h1>"
        "<p>The web UI ships in a later release. The API is running at "
        f"<a href='{api_url}'>{api_url}</a>.</p>"
        "</body></html>"
    )


def build_web_app(settings: Settings, *, api_url: str) -> FastAPI:
    """Build the embedded app with the ``/`` SPA stub mounted.

    Factored out so a test can assert the stub without booting a real server. The
    API routers live under ``/api/v1``; only the SPA root is added here.
    """
    app = create_app(settings)

    # Plan 10: mount bundled SPA static assets here (replacing this stub root).
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def _spa_root() -> HTMLResponse:
        return HTMLResponse(_stub_html(api_url))

    return app


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

    api_url = f"http://{host}:{port}/api/v1"
    app = build_web_app(settings, api_url=api_url)

    _support.console.print(f"the web UI ships in a later release; the API is running at {api_url}")
    if open_browser:
        webbrowser.open(f"http://{host}:{port}/")

    uvicorn.run(app, host=host, port=port)


def register(app: typer.Typer) -> None:
    """Attach ``web`` to the root Typer app."""
    app.command("web")(web)
