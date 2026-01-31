"""Tests for health check endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test basic health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_detailed_health_check(client: AsyncClient):
    """Test detailed health check endpoint."""
    response = await client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "cache" in data
    assert "components" in data
    assert "matching_engine" in data["components"]
    assert "providers" in data["components"]


@pytest.mark.asyncio
async def test_detailed_health_response_structure(client: AsyncClient):
    """Test detailed health check response has all required fields."""
    response = await client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    # Verify all fields are present
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "database" in data
    assert "cache" in data
    assert "components" in data

    # Verify components structure
    assert "matching_engine" in data["components"]
    assert "providers" in data["components"]
    assert "sources" in data["components"]["providers"]
    assert "targets" in data["components"]["providers"]
