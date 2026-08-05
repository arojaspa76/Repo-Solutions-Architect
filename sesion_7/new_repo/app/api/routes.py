"""
Routes — Sesión 7
==================
Endpoints REST del LLM Agent Gateway.

Endpoints nuevos en Sesión 7:
  POST /agent/run      — Ejecutar el agente LLM con herramientas
  DELETE /agent/memory — Limpiar memoria de una sesión
  GET  /agent/tools    — Listar herramientas disponibles
"""

import time
import logging
from typing import Any
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    AgentRequest, AgentResponse, AgentStepResponse,
    ChatRequest, ChatResponse, HealthResponse,
)
from app.utils.ollama_client import OllamaClient
from app.utils.cache import CacheManager
from agents.llm_agent.agent import LLMAgent

logger = logging.getLogger(__name__)

router = APIRouter()
ollama = OllamaClient()

# Agente singleton (se reutiliza entre requests — mantiene la memoria de sesiones)
_agent: LLMAgent | None = None


def get_agent() -> LLMAgent:
    global _agent
    if _agent is None:
        _agent = LLMAgent()
    return _agent


# ── /health ───────────────────────────────────────────────────────────────────
@router.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check(request: Request) -> HealthResponse:
    """Health check completo: Ollama + Cache + Agente."""
    components = {}

    # Ollama
    ollama_ok = await ollama.health_check()
    agent = get_agent()
    components["ollama"] = {
        "status": "healthy" if ollama_ok else "unhealthy",
        "url": ollama.base_url,
        "circuit_breaker": ollama.circuit_breaker.state,
    }

    # Cache
    try:
        cache: CacheManager = request.app.state.cache
        stats = await cache.stats()
        components["cache"] = {
            "status": "healthy",
            "backend": stats.get("backend"),
            "hit_rate": stats.get("hit_rate_percent"),
        }
    except Exception as e:
        components["cache"] = {"status": "degraded", "error": str(e)}

    # Agente
    components["agent"] = {
        "status": "healthy",
        "tools": list(agent.tools.keys()),
        "active_sessions": len(agent._memory),
    }

    status = "healthy" if ollama_ok else "degraded"
    return HealthResponse(status=status, components=components)


# ── /models ───────────────────────────────────────────────────────────────────
@router.get("/models", tags=["Modelos"])
async def list_models() -> dict[str, Any]:
    """Listar modelos Ollama disponibles."""
    models = await ollama.list_models()
    return {
        "provider": "ollama",
        "models": models,
        "recommended": "llama3.2:3b",
    }


# ── /agent/tools ──────────────────────────────────────────────────────────────
@router.get("/agent/tools", tags=["Agente"])
async def list_tools() -> dict[str, Any]:
    """Listar herramientas disponibles para el agente."""
    agent = get_agent()
    return {
        "tools": [
            {"name": name, "description": tool.description}
            for name, tool in agent.tools.items()
        ]
    }


# ── /agent/run ────────────────────────────────────────────────────────────────
@router.post("/agent/run", response_model=AgentResponse, tags=["Agente"])
async def run_agent(req: AgentRequest, request: Request) -> AgentResponse:
    """
    Ejecutar el agente LLM con herramientas (patrón ReAct).

    El agente:
    1. Analiza el input del usuario
    2. Decide qué herramientas usar
    3. Ejecuta las herramientas paso a paso
    4. Combina los resultados en una respuesta final

    Herramientas disponibles:
    - calculator: cálculos matemáticos
    - weather: clima de ciudades
    - search: búsqueda de información técnica
    """
    agent = get_agent()

    # Verificar que el LLM está disponible
    ollama_ok = await ollama.health_check()
    if not ollama_ok and ollama.circuit_breaker.is_open:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "LLM no disponible",
                "hint": "Verificar que Ollama está corriendo: ollama serve",
                "circuit_breaker": ollama.circuit_breaker.state,
            }
        )

    # Ejecutar el agente con timeout
    result = await agent.run(
        user_input=req.input,
        session_id=req.session_id,
        model=req.model,
    )

    # Registrar métricas Prometheus
    try:
        from app.main import (
            AGENT_RUNS, AGENT_DURATION, AGENT_STEPS, AGENT_TOOL_CALLS,
            PROMETHEUS_AVAILABLE
        )
        if PROMETHEUS_AVAILABLE:
            AGENT_RUNS.labels(
                success=str(result.success),
                session=req.session_id[:10],
            ).inc()
            AGENT_DURATION.observe(result.total_duration_ms / 1000)
            AGENT_STEPS.observe(result.total_steps)
            for step in result.steps:
                if step.action:
                    AGENT_TOOL_CALLS.labels(tool=step.action).inc()
    except ImportError:
        pass

    return AgentResponse(
        input=result.input,
        output=result.output,
        session_id=result.session_id,
        steps=[
            AgentStepResponse(
                step=s.step_number,
                thought=s.thought,
                action=s.action,
                action_input=s.action_input,
                observation=s.observation,
                duration_ms=s.duration_ms,
            )
            for s in result.steps
        ],
        total_steps=result.total_steps,
        total_duration_ms=result.total_duration_ms,
        model=result.model,
        success=result.success,
        error=result.error,
    )


# ── /agent/memory ─────────────────────────────────────────────────────────────
@router.delete("/agent/memory/{session_id}", tags=["Agente"])
async def clear_memory(session_id: str) -> dict:
    """Limpiar historial de conversación de una sesión."""
    agent = get_agent()
    agent.clear_memory(session_id)
    return {"message": f"Memoria de sesión '{session_id}' limpiada", "success": True}


# ── /chat ─────────────────────────────────────────────────────────────────────
@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    """Chat directo con LLM (sin agente ni herramientas)."""
    start = time.perf_counter()

    # Cache
    cache: CacheManager = request.app.state.cache
    if req.use_cache:
        cache_key = cache._make_key(req.message, req.model)
        cached = await cache.get(cache_key)
        if cached:
            return ChatResponse(
                message=cached,
                model=req.model,
                provider="ollama-cache",
                cached=True,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

    try:
        response_text = await ollama.chat(
            prompt=req.message,
            model=req.model,
            temperature=req.temperature,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if req.use_cache:
        await cache.set(cache_key, response_text)

    return ChatResponse(
        message=response_text,
        model=req.model,
        cached=False,
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )


# ── /chat/stream ──────────────────────────────────────────────────────────────
@router.post("/chat/stream", tags=["Chat"])
async def chat_stream(req: ChatRequest):
    """Chat con streaming (Server-Sent Events)."""
    async def generate():
        try:
            async for token in ollama.stream_chat(
                prompt=req.message,
                model=req.model,
                temperature=req.temperature,
            ):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: ERROR: {e}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── /cache/stats ──────────────────────────────────────────────────────────────
@router.get("/cache/stats", tags=["Cache"])
async def cache_stats(request: Request) -> dict:
    """Estadísticas del cache."""
    cache: CacheManager = request.app.state.cache
    return await cache.stats()


@router.delete("/cache/flush", tags=["Cache"])
async def flush_cache(request: Request) -> dict:
    """Vaciar el cache (para demos)."""
    cache: CacheManager = request.app.state.cache
    await cache.flush()
    return {"success": True, "message": "Cache vaciado"}
