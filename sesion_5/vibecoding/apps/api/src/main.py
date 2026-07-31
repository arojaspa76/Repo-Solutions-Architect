# Project:     GenAIDemo
# Component:   FastAPI backend
# Description: App factory + lifespan — wires Key Vault secrets, Cosmos DB, Redis,
#              Semantic Kernel instances, and the orchestrator into app.state
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from redis.asyncio import Redis

from src.agents.registry import AgentRegistry
from src.config.settings import get_settings
from src.core.kernel import create_agent_kernel, create_orchestrator_kernel
from src.core.orchestrator import GenAIDemoOrchestrator
from src.services.cosmos import CosmosRepository

from .middleware.logging import LoggingMiddleware
from .middleware.request_id import RequestIDMiddleware
from .routers import conversations, health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.load_from_key_vault()

    app.state.cosmos = CosmosRepository(settings.cosmos_connection_string)
    app.state.redis = Redis(
        host=settings.redis_host,
        port=settings.redis_ssl_port,
        password=settings.redis_access_key,
        ssl=True,
        decode_responses=True,
    )

    orchestrator_kernel = create_orchestrator_kernel(settings)
    registry = AgentRegistry()
    agent_kernels = {domain: create_agent_kernel(settings, domain) for domain in registry.list_enabled()}
    app.state.orchestrator = GenAIDemoOrchestrator(orchestrator_kernel, registry, agent_kernels)

    yield

    await app.state.redis.aclose()
    await app.state.cosmos.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="GenAIDemo API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment == "dev" else [],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"] if settings.environment == "dev" else [])
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    app.include_router(conversations.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")

    return app


app = create_app()
