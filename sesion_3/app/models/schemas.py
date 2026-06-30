"""
============================================================
schemas.py — Modelos de datos Pydantic
Sesión 3: Kubernetes, Docker y Contenedores para LLMs
============================================================

Pydantic valida automáticamente los datos de entrada/salida.
Si un campo es incorrecto, FastAPI retorna un 422 con descripción detallada.

Conceptos clave:
- BaseModel: clase base de Pydantic
- Field: metadatos y validaciones de campos
- validator: validaciones personalizadas
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field, field_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class LLMProvider(str, Enum):
    """Proveedores de LLM soportados por la API."""
    OLLAMA = "ollama"       # Local — sin costo
    AZURE = "azure"         # Azure OpenAI
    GCP = "gcp"             # Google Vertex AI
    AWS = "aws"             # Amazon Bedrock


class OllamaModel(str, Enum):
    """Modelos Ollama disponibles para práctica local."""
    LLAMA_3_2_3B = "llama3.2:3b"     # ~2GB RAM — ideal para clases
    LLAMA_3_1_8B = "llama3.1:8b"     # ~5GB RAM
    MISTRAL_7B = "mistral:7b"         # ~4GB RAM
    CODELLAMA = "codellama:7b"        # Especializado en código
    PHI3_MINI = "phi3:mini"           # ~2GB — Microsoft


# ── Request Schemas ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """
    Esquema para peticiones de chat.
    
    Ejemplo:
        {
            "message": "¿Qué es Kubernetes?",
            "model": "llama3.2:3b",
            "temperature": 0.7
        }
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Mensaje del usuario al LLM",
        examples=["¿Qué es Kubernetes y para qué sirve?"],
    )
    model: str = Field(
        default="llama3.2:3b",
        description="Modelo a usar. Ver /models para opciones disponibles.",
        examples=["llama3.2:3b", "mistral:7b"],
    )
    provider: LLMProvider = Field(
        default=LLMProvider.OLLAMA,
        description="Proveedor del LLM (ollama, azure, gcp, aws)",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Creatividad de la respuesta. 0=determinista, 2=muy creativo",
    )
    max_tokens: int = Field(
        default=1024,
        ge=1,
        le=8192,
        description="Máximo de tokens en la respuesta",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Prompt del sistema que define el comportamiento del LLM",
        examples=["Eres un experto en infraestructura cloud. Responde siempre en español."],
    )

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if v.strip() == "":
            raise ValueError("El mensaje no puede estar vacío")
        return v.strip()


class EmbeddingRequest(BaseModel):
    """
    Esquema para peticiones de embeddings.
    
    Los embeddings son representaciones vectoriales del texto,
    útiles para búsqueda semántica y RAG.
    """
    text: str = Field(
        ...,
        min_length=1,
        max_length=8192,
        description="Texto a convertir en embedding",
    )
    model: str = Field(
        default="llama3.2:3b",
        description="Modelo para generar embeddings",
    )


class StreamChatRequest(ChatRequest):
    """Igual que ChatRequest pero habilita streaming."""
    stream: bool = Field(default=True, description="Activar respuesta en streaming")


# ── Response Schemas ───────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    """
    Respuesta del endpoint /chat.
    
    Incluye la respuesta del LLM y métricas de la llamada.
    """
    response: str = Field(description="Respuesta generada por el LLM")
    model: str = Field(description="Modelo que generó la respuesta")
    provider: str = Field(description="Proveedor del LLM")
    tokens_used: Optional[int] = Field(
        default=None,
        description="Tokens consumidos (prompt + completion)",
    )
    latency_ms: float = Field(description="Tiempo de respuesta en milisegundos")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp UTC de la respuesta",
    )


class ModelInfo(BaseModel):
    """Información de un modelo disponible."""
    name: str
    size: Optional[str] = None
    provider: str
    description: Optional[str] = None
    modified_at: Optional[str] = None


class ModelsResponse(BaseModel):
    """Lista de modelos disponibles."""
    models: list[ModelInfo]
    total: int
    ollama_connected: bool


class EmbeddingResponse(BaseModel):
    """Respuesta con el vector de embedding."""
    embedding: list[float]
    dimensions: int
    model: str
    text_length: int
    latency_ms: float


class HealthResponse(BaseModel):
    """
    Estado de salud de la API.
    
    Kubernetes usa este endpoint para saber si el pod está listo.
    Retorna 200 = saludable, 503 = no disponible.
    """
    status: str = Field(description="Estado: 'healthy' o 'degraded'")
    version: str = Field(description="Versión de la API")
    ollama_connected: bool = Field(description="Si Ollama está disponible")
    ollama_models: list[str] = Field(description="Modelos Ollama disponibles")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    environment: str = Field(
        default="development",
        description="Entorno: development, staging, production",
    )


class ErrorResponse(BaseModel):
    """Estructura estándar para respuestas de error."""
    error: str = Field(description="Tipo de error")
    detail: str = Field(description="Descripción detallada")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
