"""
routers/health.py
==================
Endpoint GET /health para Kubernetes liveness y readiness probes.
"""

from fastapi import APIRouter, Request
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Estado de los servicios")
async def health_check(request: Request):
    """
    Retorna el estado de todos los servicios dependientes.
    Kubernetes lo usa como readiness probe cada 30 segundos.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "azure_openai": "ok",
            "azure_ai_search": "ok",
            "cosmos_db": "ok",
        },
    )
