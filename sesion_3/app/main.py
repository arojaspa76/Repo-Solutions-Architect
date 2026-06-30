"""
============================================================
LLM Gateway API — FastAPI
Sesión 3: Kubernetes, Docker y Contenedores para LLMs
BSG Institute — Diseño de Infraestructura Escalable para LLMs
============================================================

Punto de entrada principal de la aplicación.
Este archivo inicializa FastAPI, configura middleware,
registra routers y expone la API REST.

Uso:
    uvicorn app.main:app --reload --port 8000
    
    # Con host externo (para Docker)
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.utils.ollama_client import OllamaClient
from app.models.schemas import HealthResponse

# ── Configuración de logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan: startup / shutdown ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Contexto de vida de la aplicación.
    
    - STARTUP: Verificar conexión con Ollama, cargar configuración
    - SHUTDOWN: Cerrar conexiones, limpiar recursos
    
    Esto es el patrón moderno de FastAPI (reemplaza on_startup/on_shutdown).
    """
    # ── STARTUP ──────────────────────────────────────────────────────────────
    logger.info("🚀 Iniciando LLM Gateway API...")
    logger.info("🔗 Verificando conexión con Ollama...")
    
    ollama = OllamaClient()
    is_connected = await ollama.health_check()
    
    if is_connected:
        models = await ollama.list_models()
        logger.info(f"✅ Ollama conectado. Modelos disponibles: {[m['name'] for m in models]}")
    else:
        logger.warning(
            "⚠️  Ollama no está disponible en localhost:11434. "
            "Asegúrate de que Ollama está corriendo: 'ollama serve'"
        )
    
    logger.info("✅ LLM Gateway API lista en http://localhost:8000")
    logger.info("📖 Documentación: http://localhost:8000/docs")
    
    yield  # ← La aplicación corre aquí
    
    # ── SHUTDOWN ─────────────────────────────────────────────────────────────
    logger.info("🛑 Cerrando LLM Gateway API...")
    logger.info("✅ Shutdown completo.")


# ── Aplicación FastAPI ────────────────────────────────────────────────────────
app = FastAPI(
    title="LLM Gateway API",
    description="""
## 🤖 API Gateway para Modelos de Lenguaje (LLMs)

Esta API actúa como puerta de entrada unificada para consumir LLMs
tanto **locales** (via Ollama) como en **la nube** (Azure, GCP, AWS).

### Endpoints principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Estado de salud de la API |
| `/models` | GET | Modelos disponibles |
| `/chat` | POST | Enviar mensaje y recibir respuesta |
| `/chat/stream` | POST | Respuesta en streaming |
| `/embeddings` | POST | Generar embeddings de texto |

### Proveedores soportados

- **Ollama** (local): llama3.2, mistral, codellama, phi3
- **Azure OpenAI**: GPT-4o, GPT-4-turbo
- **Google Vertex AI**: Gemini 1.5 Pro/Flash
- **AWS Bedrock**: Claude 3.5, Llama 3.1, Titan

### Uso en clase

Para la práctica de esta sesión, usaremos principalmente **Ollama local**
ya que no requiere API keys ni costos de nube.

```bash
# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Descargar modelo (2GB aprox)
ollama pull llama3.2:3b

# Probar chat
curl -X POST http://localhost:8000/chat \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Hola, ¿qué es Kubernetes?"}'
```
    """,
    version="1.0.0",
    contact={
        "name": "BSG Institute",
        "url": "https://bsginstitute.com",
    },
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Middleware ────────────────────────────────────────────────────────────────

# CORS: permite peticiones desde el frontend / otras apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # En producción: lista específica de dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware de logging.
    
    Registra cada request con:
    - Método HTTP y path
    - Tiempo de respuesta
    - Status code
    
    Útil para debugging y monitoreo en producción.
    """
    start_time = time.perf_counter()
    
    # Procesar request
    response = await call_next(request)
    
    # Calcular tiempo
    duration_ms = (time.perf_counter() - start_time) * 1000
    
    # Log estructurado
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} "
        f"[{duration_ms:.1f}ms]"
    )
    
    # Agregar header con tiempo de respuesta
    response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Manejador global de excepciones.
    
    Captura cualquier error no manejado y retorna una respuesta JSON
    con un mensaje amigable (en producción no se exponen los detalles).
    """
    logger.error(f"❌ Error no manejado: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Error interno del servidor",
            "detail": str(exc),  # Remover en producción
            "path": str(request.url.path),
        }
    )


# ── Registrar routers ─────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")

# Router raíz (sin prefijo) para compatibilidad
app.include_router(router)


# ── Endpoint raíz ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    """
    Endpoint raíz — información básica de la API.
    
    Útil para verificar rápidamente que el servicio está corriendo.
    """
    return {
        "service": "LLM Gateway API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
        "curso": "BSG Institute — Diseño de Infraestructura Escalable para LLMs",
        "sesion": "Sesión 3: Kubernetes, Docker y Contenedores",
    }
