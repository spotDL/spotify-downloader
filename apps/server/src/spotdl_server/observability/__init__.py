"""Observability surface (CONTRACT A): JSON logging, /metrics, correlation-id
middleware, optional Sentry.

The increment helpers are re-exported here so instrumentation call sites import
from ``spotdl_server.observability`` rather than reaching into ``metrics``.
"""

from __future__ import annotations

from spotdl_server.observability.logging import configure_logging
from spotdl_server.observability.metrics import (
    METRIC_NAMES,
    observe_http_request,
    record_cache_hit,
    record_cache_miss,
    record_match_served,
    record_provider_error,
    render_latest,
    set_download_queue_depth,
    set_resolve_queue_depth,
)
from spotdl_server.observability.middleware import RequestObservabilityMiddleware
from spotdl_server.observability.sentry import init_sentry

__all__ = [
    "METRIC_NAMES",
    "RequestObservabilityMiddleware",
    "configure_logging",
    "init_sentry",
    "observe_http_request",
    "record_cache_hit",
    "record_cache_miss",
    "record_match_served",
    "record_provider_error",
    "render_latest",
    "set_download_queue_depth",
    "set_resolve_queue_depth",
]
