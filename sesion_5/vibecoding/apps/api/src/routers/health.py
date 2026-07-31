# Project:     GenAIDemo
# Component:   Health router
# Description: Aggregated health check for Cosmos DB and Redis dependencies
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis

from src.config.settings import get_settings
from src.services.cosmos import CosmosRepository

from ..dependencies import get_cosmos, get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    response: Response,
    cosmos: CosmosRepository = Depends(get_cosmos),
    redis_client: Redis = Depends(get_redis),
) -> dict:
    """Return the health status of the API and its Cosmos DB / Redis dependencies."""
    checks: dict[str, str] = {}

    try:
        await cosmos.client.get_database_client("genaidemo-db").read()
        checks["cosmos_db"] = "healthy"
    except Exception as exc:  # noqa: BLE001 — dependency failures must degrade, not crash the probe
        checks["cosmos_db"] = f"unhealthy: {str(exc)[:100]}"

    try:
        await redis_client.ping()
        checks["redis"] = "healthy"
    except Exception as exc:  # noqa: BLE001 — dependency failures must degrade, not crash the probe
        checks["redis"] = f"unhealthy: {str(exc)[:100]}"

    overall = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"
    response.status_code = status.HTTP_200_OK if overall == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE

    settings = get_settings()
    return {
        "status": overall,
        "version": "0.1.0",
        "environment": settings.environment,
        "dependencies": checks,
    }
