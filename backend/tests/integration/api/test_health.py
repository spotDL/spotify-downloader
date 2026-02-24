"""Tests for unified health endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient

NO_CHECK_PROVIDERS = {"piped", "synced"}


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root_health_alias(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_detailed_health_shape(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/detailed")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] in {"healthy", "degraded"}
    assert "database" in payload
    assert "cache" in payload
    assert "components" in payload
    assert payload["components"]["unified_entity_model"] == "operational"
    assert payload["components"]["merge_engine"] == "operational"
    assert payload["components"]["capability_router"] == "operational"
    assert "providers" in payload["components"]
    assert "capabilities" in payload["components"]["providers"]

    capabilities = payload["components"]["providers"]["capabilities"]
    assert set(capabilities.keys()) == {"resolve", "match", "download", "enrich", "lyrics"}


@pytest.mark.asyncio
async def test_service_status_structure(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/services")
    assert response.status_code == 200
    payload = response.json()

    assert isinstance(payload["sources"], list)
    assert isinstance(payload["targets"], list)
    assert isinstance(payload["metadata"], list)
    assert isinstance(payload["capabilities"], dict)
    assert payload["overall_state"] in {"connected", "degraded", "partial", "disconnected"}

    capability_groups = payload["capabilities"]
    assert set(capability_groups.keys()) == {"resolve", "match", "download", "enrich", "lyrics"}


@pytest.mark.asyncio
async def test_service_status_all_connected(client: AsyncClient) -> None:
    async def mock_head(*_args, **_kwargs):
        response = MagicMock()
        response.status_code = 200
        return response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client_class.return_value = mock_client

        response = await client.get("/api/v1/health/services")
        assert response.status_code == 200
        payload = response.json()
        assert payload["overall_state"] == "connected"

        all_items = payload["sources"] + payload["targets"] + payload["metadata"]
        assert all_items
        assert all(item["state"] == "connected" for item in all_items)


@pytest.mark.asyncio
async def test_service_status_timeouts(client: AsyncClient) -> None:
    async def mock_head(*_args, **_kwargs):
        raise httpx.TimeoutException("Request timed out")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client_class.return_value = mock_client

        response = await client.get("/api/v1/health/services")
        assert response.status_code == 200
        payload = response.json()

        def assert_group(group: list[dict]) -> None:
            for item in group:
                if item["name"] in NO_CHECK_PROVIDERS:
                    assert item["state"] == "connected"
                else:
                    assert item["state"] == "error"
                    assert "Timeout" in (item["error"] or "")

        assert_group(payload["sources"])
        assert_group(payload["targets"])
        assert_group(payload["metadata"])


@pytest.mark.asyncio
async def test_service_status_connection_errors(client: AsyncClient) -> None:
    async def mock_head(*_args, **_kwargs):
        raise httpx.ConnectError("Connection refused")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client_class.return_value = mock_client

        response = await client.get("/api/v1/health/services")
        assert response.status_code == 200
        payload = response.json()

        all_items = payload["sources"] + payload["targets"] + payload["metadata"]
        assert all_items
        assert any(item["state"] == "error" for item in all_items)
