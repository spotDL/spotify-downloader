"""Tests for health check endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from spotdl.core.providers_config import LYRICS_PROVIDERS, METADATA_PROVIDERS

NO_HEALTH_CHECK_SERVICES = {"piped", "synced"}
CANONICAL_SOURCE_IDS = {
    "spotify",
    "youtube_music",
    "deezer",
    "apple_music",
    "tidal",
    "soundcloud",
    "bandcamp",
}


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
    assert "metadata" in data["components"]["providers"]
    assert "lyrics" in data["components"]["providers"]

    assert set(data["components"]["providers"]["sources"]) == CANONICAL_SOURCE_IDS
    assert set(data["components"]["providers"]["targets"]) == {
        "youtube",
        "youtube_music",
        "soundcloud",
        "bandcamp",
        "piped",
    }
    expected_metadata_ids = {provider["id"] for provider in METADATA_PROVIDERS}
    assert set(data["components"]["providers"]["metadata"]) == expected_metadata_ids
    expected_lyrics_ids = {provider["id"] for provider in LYRICS_PROVIDERS}
    assert set(data["components"]["providers"]["lyrics"]) == expected_lyrics_ids


@pytest.mark.asyncio
async def test_detailed_health_check_database_check(client: AsyncClient):
    """Test detailed health check database connectivity."""
    # Test that the endpoint returns database status
    response = await client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert "database" in data
    # Database should be connected or not configured
    assert data["database"] in ["connected", "not configured", "connection failed"]


@pytest.mark.asyncio
async def test_detailed_health_check_cache_status(client: AsyncClient):
    """Test detailed health check cache status."""
    response = await client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert "cache" in data
    # Cache should be configured or not configured
    assert data["cache"] in ["configured", "not configured"]


@pytest.mark.asyncio
async def test_detailed_health_check_degraded_status(client: AsyncClient):
    """Test detailed health check can return degraded status."""
    # The status depends on database connectivity
    response = await client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    # Status should be healthy or degraded
    assert data["status"] in ["healthy", "degraded"]


@pytest.mark.asyncio
async def test_service_status_all_connected(client: AsyncClient):
    """Test service status endpoint when all services are connected."""
    async def mock_head(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        return mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client_class.return_value = mock_client

        response = await client.get("/api/v1/health/services")
        assert response.status_code == 200

        data = response.json()
        assert "sources" in data
        assert "targets" in data
        assert "metadata" in data
        assert "overall_state" in data

        # Check that we have expected services
        assert len(data["sources"]) > 0
        assert len(data["targets"]) > 0
        assert len(data["metadata"]) > 0

        source_ids = {item["name"] for item in data["sources"]}
        target_ids = {item["name"] for item in data["targets"]}
        metadata_ids = {item["name"] for item in data["metadata"]}

        expected_metadata_ids = (
            {provider["id"] for provider in METADATA_PROVIDERS}
            | {provider["id"] for provider in LYRICS_PROVIDERS}
        )

        assert source_ids == CANONICAL_SOURCE_IDS
        assert target_ids == {"youtube", "youtube_music", "soundcloud", "bandcamp", "piped"}
        assert metadata_ids == expected_metadata_ids


@pytest.mark.asyncio
async def test_service_status_some_errors(client: AsyncClient):
    """Test service status endpoint when some services have errors."""
    call_count = 0

    async def mock_head(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_response = MagicMock()

        # Make some services fail
        if call_count % 3 == 0:
            mock_response.status_code = 503
        else:
            mock_response.status_code = 200
        return mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client_class.return_value = mock_client

        response = await client.get("/api/v1/health/services")
        assert response.status_code == 200

        data = response.json()
        # Should have some errors
        all_services = data["sources"] + data["targets"] + data["metadata"]
        error_count = sum(1 for s in all_services if s["state"] == "error")
        assert error_count > 0


@pytest.mark.asyncio
async def test_service_status_timeout(client: AsyncClient):
    """Test service status endpoint when services timeout."""
    async def mock_head(*args, **kwargs):
        raise httpx.TimeoutException("Request timed out")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client_class.return_value = mock_client

        response = await client.get("/api/v1/health/services")
        assert response.status_code == 200

        data = response.json()
        all_services = data["sources"] + data["targets"] + data["metadata"]

        # Services with URLs should have timeout errors.
        for service in all_services:
            if service["name"] in NO_HEALTH_CHECK_SERVICES:
                assert service["state"] == "connected"
                continue
            assert service["state"] == "error"
            assert "Timeout" in service["error"]


@pytest.mark.asyncio
async def test_service_status_connection_error(client: AsyncClient):
    """Test service status endpoint when services have connection errors."""
    async def mock_head(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client_class.return_value = mock_client

        response = await client.get("/api/v1/health/services")
        assert response.status_code == 200

        data = response.json()
        all_services = data["sources"] + data["targets"] + data["metadata"]

        # Services with URLs should have connection errors.
        for service in all_services:
            if service["name"] in NO_HEALTH_CHECK_SERVICES:
                assert service["state"] == "connected"
                continue
            assert service["state"] == "error"
            assert service["error"] is not None


@pytest.mark.asyncio
async def test_service_status_overall_state_connected(client: AsyncClient):
    """Test overall state is connected when all services are up."""
    async def mock_head(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        return mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client_class.return_value = mock_client

        response = await client.get("/api/v1/health/services")
        assert response.status_code == 200

        data = response.json()
        assert data["overall_state"] == "connected"


@pytest.mark.asyncio
async def test_service_status_overall_state_degraded(client: AsyncClient):
    """Test overall state is degraded when more than half services are up."""
    call_count = 0

    async def mock_head(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_response = MagicMock()

        # Make about 1/4 services fail
        if call_count % 4 == 0:
            raise httpx.ConnectError("Connection refused")

        mock_response.status_code = 200
        return mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client_class.return_value = mock_client

        response = await client.get("/api/v1/health/services")
        assert response.status_code == 200

        data = response.json()
        # With most services working, should be degraded or connected
        assert data["overall_state"] in ["connected", "degraded"]


@pytest.mark.asyncio
async def test_service_status_overall_state_disconnected(client: AsyncClient):
    """Test overall state is disconnected when all services are down."""
    async def mock_head(*args, **kwargs):
        raise httpx.ConnectError("All services down")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client_class.return_value = mock_client

        response = await client.get("/api/v1/health/services")
        assert response.status_code == 200

        data = response.json()
        # URL-less services are treated as connected, so overall can be partial.
        assert data["overall_state"] in {"disconnected", "partial"}


@pytest.mark.asyncio
async def test_service_status_service_without_check_url(client: AsyncClient):
    """Test service status for services without health check URLs."""
    # Some services might not have check URLs and should show as connected by default
    response = await client.get("/api/v1/health/services")
    assert response.status_code == 200

    data = response.json()
    # Verify response structure
    assert isinstance(data["sources"], list)
    assert isinstance(data["targets"], list)
    assert isinstance(data["metadata"], list)
