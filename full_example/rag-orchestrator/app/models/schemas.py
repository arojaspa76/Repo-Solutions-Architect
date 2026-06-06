"""
models/schemas.py
==================
Modelos Pydantic para request/response del chatbot TechCorp.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class ChatRequest(BaseModel):
    """Cuerpo del POST /chat"""
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Pregunta del empleado de TechCorp",
        examples=["¿Cómo configuro la VPN en Windows 11?"]
    )
    session_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID de sesión para mantener historial de conversación"
    )
    user_id: Optional[str] = Field(
        default="anonymous",
        description="ID del empleado (integración con Azure AD)"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Número de fragmentos a recuperar de la base de conocimiento"
    )


class SourceDocument(BaseModel):
    """Fragmento recuperado de Azure AI Search"""
    title: str
    content: str
    score: float = Field(description="Puntuación de relevancia vectorial (0-1)")
    source_file: str


class ChatResponse(BaseModel):
    """Respuesta del chatbot"""
    answer: str
    session_id: str
    sources: list[SourceDocument]
    tokens_used: int
    latency_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Respuesta del endpoint /health"""
    status: str
    version: str
    services: dict[str, str]


class IndexRequest(BaseModel):
    """Solicitud para indexar un documento en Azure AI Search"""
    document_title: str
    document_content: str
    source_file: str = "manual_it"
