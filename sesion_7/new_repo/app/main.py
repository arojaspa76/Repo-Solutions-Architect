"""
LLM Agent Gateway — FastAPI (Sesión 7)
========================================
Gateway para el Agente LLM con patrón ReAct.

Nuevas métricas Prometheus para el agente:
  agent_runs_total         — ejecuciones totales por éxito/sesión
  agent_duration_seconds   — latencia del agente (histograma)
  agent_steps_total        — pasos de razonamiento (histograma)
  agent_tool_calls_total   — llamadas por herramienta

Uso:
    uvicorn app.main:app --reload --port 8000
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.routes import router
from app.utils.ollama_client import OllamaClient
from app.utils.cache import CacheManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Métricas Prometheus ───────────────────────────────────────────────────────
try:
    from prometheus_client import (
        Counter, Histogram, Gauge,
        generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True

    REQUEST_COUNT = Counter(
        "llm_requests_total", "Total requests",
        ["method", "endpoint", "status"]
    )
    REQUEST_LATENCY = Histogram(
        "llm_request_duration_seconds", "Latencia de requests",
        ["endpoint"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
    )
    ACTIVE_CONNECTIONS = Gauge("llm_active_connections", "Conexiones activas")
    CIRCUIT_BREAKER_STATE = Gauge("llm_circuit_breaker_open", "Circuit breaker (1=abierto)")

    # Métricas específicas del AGENTE (nuevas en Sesión 7)
    AGENT_RUNS = Counter(
        "agent_runs_total", "Ejecuciones del agente",
        ["success", "session"]
    )
    AGENT_DURATION = Histogram(
        "agent_duration_seconds", "Latencia del agente en segundos",
        buckets=[1, 5, 10, 20, 30, 60, 120]
    )
    AGENT_STEPS = Histogram(
        "agent_steps_total", "Pasos de razonamiento por ejecución",
        buckets=[1, 2, 3, 5, 8, 10]
    )
    AGENT_TOOL_CALLS = Counter(
        "agent_tool_calls_total", "Llamadas a herramientas",
        ["tool"]
    )
    LLM_TOKENS = Counter(
        "llm_tokens_total", "Tokens consumidos por el LLM"
    )

except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client no instalado")


# ── Limiter ───────────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando LLM Agent Gateway (Sesión 7)...")

    # Cache
    cache = CacheManager()
    await cache.connect()
    app.state.cache = cache
    logger.info(f"✅ Cache: {cache.backend}")

    # Ollama
    ollama = OllamaClient()
    ok = await ollama.health_check()
    if ok:
        models = await ollama.list_models()
        logger.info(f"✅ Ollama: {[m['name'] for m in models]}")
    else:
        logger.warning("⚠️  Ollama no disponible — ejecutar: ollama serve && ollama pull llama3.2:3b")

    logger.info("🤖 Agente LLM ReAct: listo")
    logger.info("📖 Docs:    http://localhost:8000/docs")
    logger.info("📊 Metrics: http://localhost:8000/metrics")
    logger.info("🔍 Agente:  POST http://localhost:8000/agent/run")

    yield

    logger.info("🛑 Cerrando LLM Agent Gateway...")
    await app.state.cache.disconnect()
    logger.info("✅ Shutdown completo.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="LLM Agent Gateway — Sesión 7",
    description="""
## 🤖 Gateway para Agente LLM con ReAct

Sesión 7: Autoescalado + Pruebas de Carga de Agentes LLM

### Endpoints principales

| Endpoint | Descripción |
|----------|-------------|
| `POST /agent/run` | **Ejecutar agente ReAct** (herramientas: calculadora, clima, búsqueda) |
| `POST /chat` | Chat directo con LLM (sin agente) |
| `GET /health` | Estado del sistema |
| `GET /metrics` | Métricas Prometheus |
| `GET /agent/tools` | Listar herramientas disponibles |

### Herramientas del Agente
- **calculator**: cálculos matemáticos seguros
- **weather**: clima de ciudades (mock)
- **search**: búsqueda de información técnica (mock)

### Ejemplo de uso
```bash
curl -X POST http://localhost:8000/agent/run \\
  -H "Content-Type: application/json" \\
  -d '{"input": "¿Cuánto es 1234 * 5678 y qué clima hay en Bogotá?"}'
```
    """,
    version="3.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware de métricas ────────────────────────────────────────────────────
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    if PROMETHEUS_AVAILABLE:
        ACTIVE_CONNECTIONS.inc()

    response = await call_next(request)
    duration = time.perf_counter() - start

    if PROMETHEUS_AVAILABLE:
        ACTIVE_CONNECTIONS.dec()
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=str(response.status_code),
        ).inc()
        REQUEST_LATENCY.labels(endpoint=request.url.path).observe(duration)

    response.headers["X-Process-Time"] = f"{duration * 1000:.2f}ms"
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} [{duration * 1000:.1f}ms]"
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"❌ {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Error interno", "type": type(exc).__name__, "detail": str(exc)},
    )


app.include_router(router, prefix="/api/v1")
app.include_router(router)


@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    return {
        "service": "LLM Agent Gateway",
        "version": "3.0.0",
        "sesion": "Sesión 7 — Autoescalado + Pruebas de Carga de Agentes LLM",
        "docs": "/docs",
        "metrics": "/metrics",
        "agent": "/agent/run",
        "tools": "/agent/tools",
    }


@app.get("/metrics", tags=["Observabilidad"])
async def metrics():
    """Métricas Prometheus — scrapeadas por Grafana cada 15 segundos."""
    if not PROMETHEUS_AVAILABLE:
        return JSONResponse(status_code=503, content={"error": "Prometheus no instalado"})
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
