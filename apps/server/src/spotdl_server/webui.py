"""Serve the bundled single-page web UI (Plan 10).

The web app is built (``pnpm -C apps/web build``) and its ``dist`` copied into
``spotdl_server/webui`` at wheel-build time (``make web-embed``); the wheel ships
that directory. :func:`mount_webui` locates it via ``importlib.resources`` and,
when present, serves it with SPA fallback: hashed build assets and real
top-level files are served verbatim, and every other non-``/api`` path returns
``index.html`` so the client-side router owns routing.

It is a **no-op when the directory is absent** (an API-only install, or a source
checkout that never ran ``make web-embed``), so importing/serving the API never
depends on the UI being built. ``create_app`` calls it last in every deployment
mode — the SPA self-gates on ``GET /config``, so one build serves hosted,
selfhost, and embedded alike.

The SPA handler is mounted as a *root ASGI app* rather than a catch-all ``GET``
route on purpose: a method-typed catch-all would turn a POST to an unmounted
``/api`` path (e.g. downloads in hosted mode) into a ``405`` instead of the real
``404``. A bare mount carries no method constraint, so unmatched ``/api`` paths
keep their true status and only genuinely unrouted paths reach the fallback.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.types import Receive, Scope, Send


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
    root mount only ever sees paths no API route claimed.
    """
    webui = _webui_dir()
    if webui is None:
        return

    root = webui.resolve()
    index_file = root / "index.html"

    async def spa(scope: Scope, receive: Receive, send: Send) -> None:
        # Reached only for paths no earlier (API) route matched. Receives the full
        # untouched path; no method constraint, so an unmounted /api path is a real
        # 404 here rather than a catch-all's 405.
        path = scope.get("path", "/")
        method = scope.get("method", "GET")
        response: Response
        if path.startswith("/api") or method not in ("GET", "HEAD"):
            # Mirror the framework's default unmatched-route 404 verbatim, so an
            # unrouted /api path behaves identically whether or not the SPA is
            # embedded (no behavior drift between API-only and bundled installs).
            response = JSONResponse({"detail": "Not Found"}, status_code=404)
        else:
            # A real top-level file (favicon, assets, manifest, …) wins over the
            # shell; guard against path traversal escaping the webui root.
            candidate = (root / path.lstrip("/")).resolve()
            if path != "/" and candidate.is_file() and candidate.is_relative_to(root):
                response = FileResponse(candidate)
            else:
                # Everything else is a client-side route → the SPA entrypoint.
                response = FileResponse(index_file)
        await response(scope, receive, send)

    app.mount("/", spa)
