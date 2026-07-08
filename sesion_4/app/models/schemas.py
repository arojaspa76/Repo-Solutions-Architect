"""
Pydantic Schemas — Sesión 4
Modelos de datos para request/response de la API.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ── Request Models ────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str


class ChatRequest(BaseModel):
    """Request para endpoint /chat"""
    message: str = Field(..., min_length=1, max_length=8000,
                         description="Mensaje del usuario")
    model: str = Field(default="llama3.2:3b",
                       description="Modelo a usar (ej: llama3.2:3b, mistral:7b)")
    system_prompt: Optional[str] = Field(
        default="Eres un asistente técnico experto en infraestructura cloud y LLMs.",
        description="Instrucción de sistema"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    use_cache: bool = Field(default=True, description="Usar cache si está disponible")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "¿Qué es el autoescalado en Kubernetes?",
                "model": "llama3.2:3b",
                "temperature": 0.7,
                "use_cache": True
            }
        }
    }


class SummarizeRequest(BaseModel):
    """Request para el ejercicio serverless de resumen de texto"""
    text: str = Field(..., min_length=10, max_length=10000,
                      description="Texto a resumir")
    language: Literal["es", "en"] = Field(default="es")
    max_length: int = Field(default=200, ge=50, le=1000,
                            description="Longitud máxima del resumen en palabras")
    model: str = Field(default="llama3.2:3b")

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Kubernetes es un sistema open source de orquestación de contenedores que automatiza el despliegue, escalado y gestión de aplicaciones contenerizadas...",
                "language": "es",
                "max_length": 100
            }
        }
    }


class EmbeddingRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    model: str = Field(default="nomic-embed-text")


# ── Response Models ───────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    """Response del endpoint /chat"""
    message: str = Field(description="Respuesta del LLM")
    model: str
    provider: str = Field(description="ollama | azure | gcp | aws")
    cached: bool = Field(default=False, description="True si la respuesta vino del cache")
    latency_ms: float = Field(description="Latencia en milisegundos")
    tokens_used: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SummarizeResponse(BaseModel):
    """Response del ejercicio serverless"""
    summary: str
    original_length: int = Field(description="Palabras en el texto original")
    summary_length: int = Field(description="Palabras en el resumen")
    compression_ratio: float = Field(description="Ratio de compresión (0-1)")
    model: str
    provider: str
    cached: bool
    latency_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Response del endpoint /health"""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    components: dict = Field(description="Estado de cada componente")


class CacheStats(BaseModel):
    backend: str
    entries: int
    hit_rate: Optional[float] = None
    memory_mb: Optional[float] = None


class ModelInfo(BaseModel):
    name: str
    size: Optional[str] = None
    family: Optional[str] = None
