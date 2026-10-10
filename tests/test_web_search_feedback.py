"""Regression tests for search response feedback."""

import logging

import pytest

from spotdl.utils.web import app_state
from spotdl.web import routes


@pytest.mark.parametrize("outcome", ["empty", "error", "timeout"])
async def test_search_replaces_loading_on_empty_or_failure(monkeypatch, outcome):
    monkeypatch.setattr(app_state, "logger", logging.getLogger("test"), raising=False)

    def search(_):
        if outcome == "error":
            raise RuntimeError("Provider unavailable")
        return []

    monkeypatch.setattr(routes, "get_search_results", search)
    if outcome == "timeout":

        async def timeout(awaitable, timeout):
            awaitable.close()
            raise TimeoutError()

        monkeypatch.setattr(routes.asyncio, "wait_for", timeout)
    events = [
        event
        async for event in routes.handle_get_client_search.__wrapped__(
            {"search_term": "artist and title", "client_id": "test"}
        )
    ]
    assert len(events) == 1
    assert 'id="search-list"' in str(events[0])
    assert "LOADING" not in str(events[0])
