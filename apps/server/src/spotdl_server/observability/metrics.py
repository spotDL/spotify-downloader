"""CONTRACT A2/A3 — the Prometheus metric set and its increment helpers.

The metric objects are module-level so they are created exactly once per process
against the default registry (importing the module twice is a no-op — Python
caches it), which keeps repeated ``create_app`` calls in the test suite from
re-registering and blowing up. Every mutation goes through a named helper so the
call sites (middleware, resolve service, download pool) never touch a metric
object directly.

CONTRACT A2 maps spec §9's five named metrics onto concrete names, plus the
http/download extras:

===============================  ==========  =====================  ================================
metric                           type        labels                 spec §9 item
===============================  ==========  =====================  ================================
spotdl_http_requests_total       Counter     method, path, status   request rates
spotdl_http_request_duration...  Histogram   method, path           request rates (latency extra)
spotdl_cache_hits_total          Counter     cache                  cache hit ratio
spotdl_cache_misses_total        Counter     cache                  cache hit ratio
spotdl_provider_errors_total     Counter     provider               provider error rates
spotdl_resolve_queue_depth       Gauge       —                      resolve queue depth
spotdl_download_queue_depth      Gauge       —                      download queue depth (extra)
spotdl_matches_served_total      Counter     matcher_version        matcher version distribution
===============================  ==========  =====================  ================================
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

__all__ = [
    "CONTENT_TYPE_LATEST",
    "METRIC_NAMES",
    "REGISTRY",
    "observe_http_request",
    "record_cache_hit",
    "record_cache_miss",
    "record_match_served",
    "record_provider_error",
    "render_latest",
    "set_download_queue_depth",
    "set_resolve_queue_depth",
]

HTTP_REQUESTS = Counter(
    "spotdl_http_requests_total",
    "Total HTTP requests handled, by method, route template and status code.",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "spotdl_http_request_duration_seconds",
    "HTTP request latency in seconds, by method and route template.",
    ["method", "path"],
)
CACHE_HITS = Counter(
    "spotdl_cache_hits_total",
    "Cache lookups served from a fresh entry, by cache name.",
    ["cache"],
)
CACHE_MISSES = Counter(
    "spotdl_cache_misses_total",
    "Cache lookups that fell through to the source, by cache name.",
    ["cache"],
)
PROVIDER_ERRORS = Counter(
    "spotdl_provider_errors_total",
    "Provider calls that failed, by provider id.",
    ["provider"],
)
RESOLVE_QUEUE_DEPTH = Gauge(
    "spotdl_resolve_queue_depth",
    "In-flight resolve work items awaiting processing.",
)
DOWNLOAD_QUEUE_DEPTH = Gauge(
    "spotdl_download_queue_depth",
    "Download jobs queued and awaiting a worker.",
)
MATCHES_SERVED = Counter(
    "spotdl_matches_served_total",
    "Match rankings persisted, by matcher version (A/B distribution).",
    ["matcher_version"],
)

# Gauges read as 0 until a producer sets them (a bare gauge already reports 0,
# but set it explicitly so the sample is present from the first scrape).
RESOLVE_QUEUE_DEPTH.set(0)
DOWNLOAD_QUEUE_DEPTH.set(0)

#: The canonical CONTRACT A2 metric names, asserted by the /metrics test.
METRIC_NAMES: tuple[str, ...] = (
    "spotdl_http_requests_total",
    "spotdl_http_request_duration_seconds",
    "spotdl_cache_hits_total",
    "spotdl_cache_misses_total",
    "spotdl_provider_errors_total",
    "spotdl_resolve_queue_depth",
    "spotdl_download_queue_depth",
    "spotdl_matches_served_total",
)


def observe_http_request(*, method: str, path: str, status: int, duration_seconds: float) -> None:
    """Record one served HTTP request against the counter and latency histogram.

    ``path`` is the route *template* (e.g. ``/api/v1/items/{item_id}``), never a
    concrete id, so label cardinality stays bounded.
    """
    HTTP_REQUESTS.labels(method=method, path=path, status=str(status)).inc()
    HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(duration_seconds)


def record_cache_hit(cache: str) -> None:
    """Count a cache lookup that was served from a fresh entry."""
    CACHE_HITS.labels(cache=cache).inc()


def record_cache_miss(cache: str) -> None:
    """Count a cache lookup that fell through to the source."""
    CACHE_MISSES.labels(cache=cache).inc()


def record_provider_error(provider: str) -> None:
    """Count a failed provider call, keyed by provider id."""
    PROVIDER_ERRORS.labels(provider=provider).inc()


def record_match_served(matcher_version: str) -> None:
    """Count a persisted match ranking, keyed by the matcher version used."""
    MATCHES_SERVED.labels(matcher_version=matcher_version).inc()


def set_resolve_queue_depth(value: int) -> None:
    """Publish the current resolve queue depth gauge."""
    RESOLVE_QUEUE_DEPTH.set(value)


def set_download_queue_depth(value: int) -> None:
    """Publish the current download queue depth gauge."""
    DOWNLOAD_QUEUE_DEPTH.set(value)


def render_latest() -> tuple[bytes, str]:
    """Return the current metrics exposition and its ``Content-Type``."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
