from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ready_endpoint_healthy(async_client: AsyncClient) -> None:
    with patch("app.api.v1.health.check_database_connection", return_value=True):
        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        assert "mqtt" in data


@pytest.mark.asyncio
async def test_ready_endpoint_unhealthy(async_client: AsyncClient) -> None:
    with patch("app.api.v1.health.check_database_connection", return_value=False):
        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not ready"
        assert data["database"] == "disconnected"
        assert "mqtt" in data
