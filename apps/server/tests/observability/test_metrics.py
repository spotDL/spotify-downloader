"""CONTRACT A2/A3 — the Prometheus metric set and its increment helpers."""

from __future__ import annotations

from spotdl_server.observability import metrics


def _value(name: str, labels: dict[str, str] | None = None) -> float:
    val = metrics.REGISTRY.get_sample_value(name, labels or {})
    return 0.0 if val is None else val


def test_contract_a2_names_are_all_exposed() -> None:
    body, content_type = metrics.render_latest()
    text = body.decode()
    assert "text/plain" in content_type
    for name in metrics.METRIC_NAMES:
        assert name in text, f"{name} missing from /metrics body"


def test_observe_http_request_moves_the_counter_and_histogram() -> None:
    labels = {"method": "GET", "path": "/api/v1/health", "status": "200"}
    before = _value("spotdl_http_requests_total", labels)
    hist_before = _value(
        "spotdl_http_request_duration_seconds_count",
        {"method": "GET", "path": "/api/v1/health"},
    )

    metrics.observe_http_request(
        method="GET", path="/api/v1/health", status=200, duration_seconds=0.01
    )

    assert _value("spotdl_http_requests_total", labels) == before + 1
    assert (
        _value(
            "spotdl_http_request_duration_seconds_count",
            {"method": "GET", "path": "/api/v1/health"},
        )
        == hist_before + 1
    )


def test_cache_provider_and_match_helpers_move_their_metrics() -> None:
    hits = _value("spotdl_cache_hits_total", {"cache": "snapshot"})
    misses = _value("spotdl_cache_misses_total", {"cache": "snapshot"})
    errors = _value("spotdl_provider_errors_total", {"provider": "spotify"})
    served = _value("spotdl_matches_served_total", {"matcher_version": "v5"})

    metrics.record_cache_hit("snapshot")
    metrics.record_cache_miss("snapshot")
    metrics.record_provider_error("spotify")
    metrics.record_match_served("v5")

    assert _value("spotdl_cache_hits_total", {"cache": "snapshot"}) == hits + 1
    assert _value("spotdl_cache_misses_total", {"cache": "snapshot"}) == misses + 1
    assert _value("spotdl_provider_errors_total", {"provider": "spotify"}) == errors + 1
    assert _value("spotdl_matches_served_total", {"matcher_version": "v5"}) == served + 1


def test_queue_depth_gauges_default_to_zero_and_are_settable() -> None:
    assert _value("spotdl_resolve_queue_depth") == 0
    assert _value("spotdl_download_queue_depth") == 0

    metrics.set_resolve_queue_depth(3)
    metrics.set_download_queue_depth(5)
    assert _value("spotdl_resolve_queue_depth") == 3
    assert _value("spotdl_download_queue_depth") == 5

    metrics.set_resolve_queue_depth(0)
    metrics.set_download_queue_depth(0)
