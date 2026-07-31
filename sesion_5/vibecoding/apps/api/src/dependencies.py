# Project:     GenAIDemo
# Component:   API dependencies
# Description: FastAPI dependency providers pulling shared services from app.state
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from fastapi import Request
from redis.asyncio import Redis

from src.core.orchestrator import GenAIDemoOrchestrator
from src.services.cosmos import CosmosRepository


def get_cosmos(request: Request) -> CosmosRepository:
    """Return the shared CosmosRepository instance from app.state."""
    return request.app.state.cosmos


def get_redis(request: Request) -> Redis:
    """Return the shared Redis client instance from app.state."""
    return request.app.state.redis


def get_orchestrator(request: Request) -> GenAIDemoOrchestrator:
    """Return the shared GenAIDemoOrchestrator instance from app.state."""
    return request.app.state.orchestrator
