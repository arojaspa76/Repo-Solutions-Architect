"""
Routes — Sesión 4
==================
Endpoints REST del LLM Gateway.

Nuevos en Sesión 4:
  POST /summarize   — Resumir texto (versión serverless-like del ejercicio)
  GET  /health      — Health check extendido con estado de todos los componentes
  GET  /cache/flush — Vaciar cache (para demos en clase)
"""

import time
import logging
from typing import Any
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    ChatRequest, ChatResponse,
    SummarizeRequest, SummarizeResponse,
    HealthResponse
)
from app.utils.ollama_client import OllamaClient
from app.utils.cache import CacheManager

logger = logging.getLogger(__name__)

router = APIRouter()
ollama = OllamaClient()


# ── /health ───────────────────────────────────────────────────────────────────
@router.get("/health", response_model=HealthResponse, tags=["Salud"])
async def health_check(request: Request) -> HealthResponse:
    """
    Health check extendido.

    Verifica:
    - Ollama (LLM local)
    - Cache (Redis o memoria)
    - Circuit Breaker (estado del LLM)
    - API (siempre ok si llega aquí)
    """
    components = {}

    # Ollama
    ollama_ok = await ollama.health_check()
    components["ollama"] = {
        "status": "healthy" if ollama_ok else "unhealthy",
        "url": ollama.base_url,
        "circuit_breaker": ollama.circuit_breaker.state,
    }

    # Cache
    try:
        cache: CacheManager = request.app.state.cache
        cache_stats = await cache.stats()
        components["cache"] = {
            "status": "healthy",
            "backend": cache_stats.get("backend"),
            "hit_rate": cache_stats.get("hit_rate_percent"),
        }
    except Exception as e:
        components["cache"] = {"status": "unhealthy", "error": str(e)}

    # Determinar estado global
    if ollama_ok:
        overall = "healthy"
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        version="2.0.0",
        components=components,
    )


# ── /models ───────────────────────────────────────────────────────────────────
@router.get("/models", tags=["Modelos"])
async def list_models() -> dict[str, Any]:
    """Listar modelos disponibles en Ollama."""
    models = await ollama.list_models()
    return {
        "provider": "ollama",
        "models": models,
        "recommended": "llama3.2:3b",
        "hint": "Para descargar un modelo: ollama pull <nombre>",
    }


# ── /chat ─────────────────────────────────────────────────────────────────────
@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    """
    Chat con LLM local (Ollama).

    Features:
    - Cache automático: misma pregunta → respuesta instantánea
    - Circuit breaker: si Ollama falla, falla rápido
    - Métricas de latencia incluidas en la respuesta
    """
    start = time.perf_counter()

    # ── Verificar cache ───────────────────────────────────────────────────────
    cache: CacheManager = request.app.state.cache
    cached_response = None

    if req.use_cache:
        cache_key = cache._make_key(req.message, req.model)
        cached_response = await cache.get(cache_key)

    if cached_response:
        latency = (time.perf_counter() - start) * 1000
        logger.info(f"🎯 Cache HIT para: {req.message[:40]}...")
        return ChatResponse(
            message=cached_response,
            model=req.model,
            provider="ollama-cache",
            cached=True,
            latency_ms=round(latency, 2),
        )

    # ── Llamar al LLM ─────────────────────────────────────────────────────────
    try:
        response_text = await ollama.chat(
            prompt=req.message,
            model=req.model,
            system_prompt=req.system_prompt,
            temperature=req.temperature,
        )
    except RuntimeError as e:
        if "Circuit Breaker" in str(e):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "LLM no disponible (Circuit Breaker abierto)",
                    "hint": "Verificar que Ollama está corriendo: ollama serve",
                }
            )
        raise HTTPException(status_code=500, detail=str(e))

    # ── Guardar en cache ──────────────────────────────────────────────────────
    if req.use_cache:
        await cache.set(cache_key, response_text, ttl=300)

    latency = (time.perf_counter() - start) * 1000

    return ChatResponse(
        message=response_text,
        model=req.model,
        provider="ollama",
        cached=False,
        latency_ms=round(latency, 2),
    )


# ── /chat/stream ──────────────────────────────────────────────────────────────
@router.post("/chat/stream", tags=["Chat"])
async def chat_stream(req: ChatRequest):
    """
    Chat con streaming — tokens se envían a medida que se generan.

    Usa Server-Sent Events (SSE).
    Ideal para mostrar respuestas progresivas en la UI.
    """
    async def generate():
        try:
            async for token in ollama.stream_chat(
                prompt=req.message,
                model=req.model,
                system_prompt=req.system_prompt,
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


# ── /summarize ────────────────────────────────────────────────────────────────
@router.post("/summarize", response_model=SummarizeResponse, tags=["Serverless"])
async def summarize(req: SummarizeRequest, request: Request) -> SummarizeResponse:
    """
    Resumir texto usando LLM local.

    Este es el MISMO ejercicio que se despliega como serverless en:
    - Azure Functions
    - Google Cloud Functions
    - AWS Lambda

    La lógica de negocio es idéntica; solo cambia el wrapper de nube.
    """
    start = time.perf_counter()

    cache: CacheManager = request.app.state.cache
    cache_key = cache._make_key(f"summarize:{req.text}", req.model)

    # Cache check
    cached = await cache.get(cache_key)
    if cached:
        latency = (time.perf_counter() - start) * 1000
        original_words = len(req.text.split())
        summary_words = len(cached.split())
        return SummarizeResponse(
            summary=cached,
            original_length=original_words,
            summary_length=summary_words,
            compression_ratio=round(1 - summary_words / max(original_words, 1), 3),
            model=req.model,
            provider="ollama-cache",
            cached=True,
            latency_ms=round(latency, 2),
        )

    # Construir prompt de resumen
    lang_instruction = "en español" if req.language == "es" else "in English"
    prompt = f"""Resume el siguiente texto {lang_instruction} en máximo {req.max_length} palabras.
El resumen debe ser claro, conciso y capturar las ideas principales.

TEXTO:
{req.text}

RESUMEN:"""

    try:
        summary = await ollama.chat(
            prompt=prompt,
            model=req.model,
            system_prompt="Eres un experto en síntesis y resumen de textos técnicos.",
            temperature=0.3,  # Baja temperatura para resúmenes más precisos
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del LLM: {e}")

    # Guardar en cache
    await cache.set(cache_key, summary, ttl=600)

    latency = (time.perf_counter() - start) * 1000
    original_words = len(req.text.split())
    summary_words = len(summary.split())

    return SummarizeResponse(
        summary=summary,
        original_length=original_words,
        summary_length=summary_words,
        compression_ratio=round(1 - summary_words / max(original_words, 1), 3),
        model=req.model,
        provider="ollama",
        cached=False,
        latency_ms=round(latency, 2),
    )


# ── /cache/flush ─────────────────────────────────────────────────────────────
@router.delete("/cache/flush", tags=["Cache"])
async def flush_cache(request: Request) -> dict:
    """Vaciar el cache (útil para demos en clase)."""
    cache: CacheManager = request.app.state.cache
    success = await cache.flush()
    return {"success": success, "message": "Cache vaciado" if success else "Error vaciando cache"}


# ── __init__ files ────────────────────────────────────────────────────────────
# (se crean abajo vía bash)
