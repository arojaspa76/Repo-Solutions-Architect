# Project:     GenAIDemo
# Component:   Tests
# Description: Unit tests for apps/api/src/routers/health.py
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Response

from apps.api.src.routers.health import health_check


@pytest.mark.asyncio
async def test_health_all_healthy_returns_200() -> None:
    """When both dependencies respond, overall status is healthy and HTTP 200."""
    cosmos = MagicMock()
    cosmos.client.get_database_client.return_value.read = AsyncMock(return_value={})
    redis_client = MagicMock()
    redis_client.ping = AsyncMock(return_value=True)
    response = Response()

    body = await health_check(response, cosmos, redis_client)

    assert body["status"] == "healthy"
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_cosmos_down_returns_503() -> None:
    """If Cosmos DB is unreachable, overall status is degraded and HTTP 503."""
    cosmos = MagicMock()
    cosmos.client.get_database_client.return_value.read = AsyncMock(side_effect=RuntimeError("down"))
    redis_client = MagicMock()
    redis_client.ping = AsyncMock(return_value=True)
    response = Response()

    body = await health_check(response, cosmos, redis_client)

    assert body["status"] == "degraded"
    assert response.status_code == 503
    assert "unhealthy" in body["dependencies"]["cosmos_db"]


@pytest.mark.asyncio
async def test_health_redis_down_returns_503() -> None:
    """If Redis is unreachable, overall status is degraded and HTTP 503."""
    cosmos = MagicMock()
    cosmos.client.get_database_client.return_value.read = AsyncMock(return_value={})
    redis_client = MagicMock()
    redis_client.ping = AsyncMock(side_effect=RuntimeError("down"))
    response = Response()

    body = await health_check(response, cosmos, redis_client)

    assert body["status"] == "degraded"
    assert response.status_code == 503
    assert "unhealthy" in body["dependencies"]["redis"]
