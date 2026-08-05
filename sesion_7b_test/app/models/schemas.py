"""
Pydantic Schemas — Sesión 7
Request/Response models para la API del agente LLM.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ── Requests ──────────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    """Request para ejecutar el agente LLM."""
    input: str = Field(..., min_length=1, max_length=2000,
                       description="La pregunta o tarea para el agente")
    session_id: str = Field(default="default",
                            description="ID de sesión para memoria conversacional")
    model: str = Field(default="llama3.2:3b")
    max_steps: Optional[int] = Field(default=None, ge=1, le=15)

    model_config = {
        "json_schema_extra": {
            "example": {
                "input": "¿Cuánto es 1234 × 5678 y qué clima hay en Bogotá?",
                "session_id": "session-abc123",
                "model": "llama3.2:3b"
            }
        }
    }


class ChatRequest(BaseModel):
    """Request para chat directo con LLM (sin agente)."""
    message: str = Field(..., min_length=1, max_length=4000)
    model: str = Field(default="llama3.2:3b")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    use_cache: bool = Field(default=True)

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Explica el patrón ReAct en 3 oraciones.",
                "model": "llama3.2:3b"
            }
        }
    }


# ── Responses ─────────────────────────────────────────────────────────────────

class AgentStepResponse(BaseModel):
    """Un paso del agente en la respuesta."""
    step: int
    thought: str
    action: Optional[str] = None
    action_input: str = ""
    observation: str
    duration_ms: float


class AgentResponse(BaseModel):
    """Response del agente LLM."""
    input: str
    output: str
    session_id: str
    steps: list[AgentStepResponse] = []
    total_steps: int
    total_duration_ms: float
    model: str
    success: bool
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatResponse(BaseModel):
    """Response de chat directo."""
    message: str
    model: str
    provider: str = "ollama"
    cached: bool = False
    latency_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check del sistema."""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str = "3.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    components: dict = {}
