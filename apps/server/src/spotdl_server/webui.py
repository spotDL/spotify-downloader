"""Serve the bundled single-page web UI (Plan 10).

The web app is built (``pnpm -C apps/web build``) and its ``dist`` copied into
``spotdl_server/webui`` at wheel-build time (``make web-embed``); the wheel
force-includes that directory. :func:`mount_webui` locates it via
``importlib.resources`` and, when present, serves it with SPA fallback: hashed
build assets and real top-level files are served verbatim, and every other
non-``/api`` path returns ``index.html`` so the client-side router owns routing.

It is a **no-op when the directory is absent** (an API-only install, or a source
checkout that never ran ``make web-embed``), so importing/serving the API never
depends on the UI being built. ``create_app`` calls it last in every deployment
mode — the SPA self-gates on ``GET /config``, so one build serves hosted,
selfhost, and embedded alike.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles


def _webui_dir() -> Path | None:
    """The embedded ``webui`` directory, or ``None`` when it wasn't shipped.

    Resolved relative to the installed ``spotdl_server`` package (never the CWD),
    so it works the same from a wheel install and a source checkout.
    """
    resource = resources.files("spotdl_server").joinpath("webui")
    path = Path(str(resource))
    return path if (path / "index.html").is_file() else None


def mount_webui(app: FastAPI) -> None:
    """Mount the bundled SPA on ``app`` with client-side-routing fallback.

    A no-op when the assets are absent. Call **after** the API routers so the
    catch-all never shadows a real endpoint.
    """
    webui = _webui_dir()
    if webui is None:
        return

    root = webui.resolve()
    index_file = root / "index.html"

    # Hashed build assets (``dist/assets/*``) are served as real files.
    assets_dir = root / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="webui-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> Response:
        # The API surface is owned by the routers; a GET to an unknown ``/api``
        # path is a real 404, never the SPA shell.
        if full_path == "api" or full_path.startswith("api/"):
            return Response(status_code=404)
        # A real top-level file (favicon, manifest, robots.txt, …) wins over the
        # shell; guard against path traversal escaping the webui root.
        if full_path:
            candidate = (root / full_path).resolve()
            if candidate.is_file() and candidate.is_relative_to(root):
                return FileResponse(candidate)
        # Everything else is a client-side route → the SPA entrypoint.
        return FileResponse(index_file)
