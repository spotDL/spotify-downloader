"""CONTRACT A3 — correlation-id request middleware (pure ASGI).

A pure-ASGI middleware (not ``BaseHTTPMiddleware``) so it can read the mutated
``scope`` after the router has run and recover the matched *route template* for
the metric/log ``path`` label — Starlette does not put the route object in
``scope``, so the template is recovered by re-matching against ``app.routes``.

Each request gets a correlation id (a validated inbound ``X-Request-ID`` or a
fresh uuid), bound to structlog's contextvars so every log line emitted during
the request carries it, echoed back on the response header, and written to a
single JSON access-log line with ``request_id, method, path, status_code,
duration_ms``. The counter/latency histogram move on the same boundary.
"""

from __future__ import annotations

import re
import time
import uuid

import structlog
from starlette.datastructures import MutableHeaders
from starlette.routing import Match
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from spotdl_server.observability.metrics import observe_http_request

# A conservative correlation-id shape: printable, bounded, no header-injection
# risk. Anything else is treated as absent and replaced with a fresh id.
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,200}$")

# Requests that do not match any route (404s from scanners) collapse to a single
# label value so a hostile client cannot explode metric/log cardinality.
_UNMATCHED = "<unmatched>"

_log = structlog.get_logger("spotdl_server.access")


def _resolve_request_id(scope: Scope) -> str:
    for key, value in scope["headers"]:
        if key == b"x-request-id":
            candidate: str = value.decode("latin-1")
            if _REQUEST_ID_RE.match(candidate):
                return candidate
            break
    return uuid.uuid4().hex


def _route_template(scope: Scope) -> str:
    """Recover the matched route template from the post-routing scope."""
    app = scope.get("app")
    concrete: str = scope.get("path", _UNMATCHED)
    if app is None:
        return concrete
    for route in app.routes:
        match, _child = route.matches(scope)
        if match is Match.FULL:
            template: str = getattr(route, "path", concrete)
            return template
    return _UNMATCHED


class RequestObservabilityMiddleware:
    """Assign/echo a correlation id, emit the access log, move HTTP metrics."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _resolve_request_id(scope)
        method: str = scope["method"]
        status = 500
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
            await send(message)

        tokens = structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            path = _route_template(scope)
            observe_http_request(
                method=method,
                path=path,
                status=status,
                duration_seconds=duration_ms / 1000.0,
            )
            _log.info(
                "request",
                request_id=request_id,
                method=method,
                path=path,
                status_code=status,
                duration_ms=round(duration_ms, 2),
            )
            structlog.contextvars.reset_contextvars(**tokens)
