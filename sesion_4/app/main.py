"""
============================================================
LLM Gateway API — FastAPI  (Sesión 4: Serverless + HA)
BSG Institute — Diseño de Infraestructura Escalable para LLMs
============================================================

Evolución del Gateway de Sesión 3 con:
  - Cache en memoria / Redis (reduce latencia hasta 95%)
  - Circuit breaker (alta disponibilidad)
  - Rate limiting (protección contra abuso)
  - Métricas OpenTelemetry + Prometheus
  - Endpoint /metrics listo para Prometheus scraping

Uso local:
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
from app.models.schemas import HealthResponse

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── Métricas Prometheus ───────────────────────────────────────────────────────
try:
    from prometheus_client import (
        Counter, Histogram, Gauge,
        generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True

    REQUEST_COUNT = Counter(
        "llm_requests_total",
        "Total de requests al LLM Gateway",
        ["method", "endpoint", "status"]
    )
    REQUEST_LATENCY = Histogram(
        "llm_request_duration_seconds",
        "Latencia de requests en segundos",
        ["endpoint"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
    )
    CACHE_HITS = Counter(
        "llm_cache_hits_total",
        "Total de hits en cache"
    )
    CACHE_MISSES = Counter(
        "llm_cache_misses_total",
        "Total de misses en cache"
    )
    ACTIVE_CONNECTIONS = Gauge(
        "llm_active_connections",
        "Conexiones activas al momento"
    )
    CIRCUIT_BREAKER_STATE = Gauge(
        "llm_circuit_breaker_open",
        "Estado del circuit breaker (1=abierto/fallo, 0=cerrado/ok)"
    )

except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client no instalado — métricas desactivadas")


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / Shutdown del servidor.

    STARTUP:
        1. Verificar Ollama
        2. Inicializar cache (Redis si disponible, dict en memoria si no)
        3. Warm-up del modelo (optional)

    SHUTDOWN:
        1. Vaciar cache
        2. Cerrar conexiones
    """
    # ── STARTUP ──────────────────────────────────────────────────────────────
    logger.info("🚀 Iniciando LLM Gateway API v2 (Sesión 4)...")

    # Cache
    cache = CacheManager()
    await cache.connect()
    app.state.cache = cache
    logger.info(f"✅ Cache inicializado: {cache.backend}")

    # Ollama
    ollama = OllamaClient()
    is_connected = await ollama.health_check()
    if is_connected:
        models = await ollama.list_models()
        logger.info(f"✅ Ollama conectado — modelos: {[m['name'] for m in models]}")
    else:
        logger.warning("⚠️  Ollama no disponible — ejecutar: ollama serve")

    logger.info("📊 Métricas: http://localhost:8000/metrics")
    logger.info("📖 Docs:     http://localhost:8000/docs")

    yield  # ← App corriendo

    # ── SHUTDOWN ─────────────────────────────────────────────────────────────
    logger.info("🛑 Cerrando LLM Gateway API...")
    await app.state.cache.disconnect()
    logger.info("✅ Shutdown completo.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="LLM Gateway API — Sesión 4",
    description="""
## 🤖 LLM Gateway con Alta Disponibilidad

Evolución del gateway de Sesión 3 con:

### Nuevas características (Sesión 4)
- ⚡ **Cache multinivel** (Redis + memoria) — reduce latencia hasta 95%
- 🔒 **Circuit Breaker** — alta disponibilidad ante fallos del LLM
- 🚦 **Rate Limiting** — 60 req/min por IP
- 📊 **Métricas Prometheus** — endpoint `/metrics` listo para Grafana
- 🔍 **Tracing OpenTelemetry** — trazabilidad distribuida

### Endpoints

| Endpoint | Descripción |
|----------|-------------|
| `GET /health` | Estado completo (Ollama + Cache + Circuit Breaker) |
| `POST /chat` | Chat con LLM (con cache automático) |
| `POST /chat/stream` | Chat en streaming |
| `POST /summarize` | Resumir texto (función serverless-like) |
| `GET /metrics` | Métricas Prometheus |
| `GET /cache/stats` | Estadísticas del cache |
    """,
    version="2.0.0",
    lifespan=lifespan,
)

# ── Rate Limiting middleware ───────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware: métricas + latencia ───────────────────────────────────────────
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """
    Middleware que:
    1. Mide latencia de cada request
    2. Registra métricas en Prometheus
    3. Añade header X-Process-Time a la respuesta
    4. Cuenta conexiones activas
    """
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
            status=str(response.status_code)
        ).inc()
        REQUEST_LATENCY.labels(endpoint=request.url.path).observe(duration)

    response.headers["X-Process-Time"] = f"{duration * 1000:.2f}ms"

    # Log de cada request
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} [{duration * 1000:.1f}ms]"
    )

    return response


# ── Exception handler global ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"❌ Error: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Error interno del servidor",
            "type": type(exc).__name__,
            "detail": str(exc),
        }
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")
app.include_router(router)


# ── Endpoints extra ───────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    return {
        "service": "LLM Gateway API",
        "version": "2.0.0",
        "sesion": "Sesión 4 — Serverless y Alta Disponibilidad",
        "docs": "/docs",
        "metrics": "/metrics",
        "health": "/health",
    }


@app.get("/metrics", tags=["Observabilidad"])
async def metrics():
    """
    Endpoint de métricas en formato Prometheus.

    Prometheus hace scraping de este endpoint cada 15 segundos.
    Grafana visualiza las métricas en dashboards.

    Métricas expuestas:
    - llm_requests_total           — conteo por endpoint y status
    - llm_request_duration_seconds — histograma de latencia
    - llm_cache_hits_total         — efectividad del cache
    - llm_active_connections       — concurrencia actual
    - llm_circuit_breaker_open     — estado del circuit breaker
    """
    if not PROMETHEUS_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={"error": "prometheus_client no instalado"}
        )
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/cache/stats", tags=["Cache"])
async def cache_stats(request: Request):
    """
    Estadísticas del cache.

    Muestra:
    - Backend usado (Redis o memoria)
    - Número de entradas activas
    - Hit rate aproximado
    """
    cache: CacheManager = request.app.state.cache
    return await cache.stats()
