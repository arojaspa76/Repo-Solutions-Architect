"""
============================================================
routes.py — Endpoints REST de la LLM Gateway API
Sesión 3: Kubernetes, Docker y Contenedores para LLMs
============================================================

Este archivo define todos los endpoints de la API.
Cada endpoint está documentado con:
- Descripción de qué hace
- Parámetros de entrada (via Pydantic schemas)
- Respuestas posibles
- Ejemplos de uso con curl

FastAPI genera automáticamente /docs (Swagger UI) a partir
de estas anotaciones.
"""

import time
import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    HealthResponse,
    ModelsResponse,
    ModelInfo,
    LLMProvider,
)
from app.utils.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

# ── Router ────────────────────────────────────────────────────────────────────
router = APIRouter(tags=["LLM Gateway"])

# Instancia del cliente Ollama (compartida entre requests)
ollama = OllamaClient()


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1: Health Check
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="""
Verifica el estado de salud de la API y sus dependencias.

**Kubernetes usa este endpoint para:**
- **Liveness Probe**: Si retorna error → reiniciar el pod
- **Readiness Probe**: Si retorna error → no enviar tráfico al pod

```bash
curl http://localhost:8000/health
```
    """,
)
async def health_check() -> HealthResponse:
    """
    Estado de salud de la API.
    
    Retorna 200 con status='healthy' si todo está bien.
    Retorna 503 si Ollama no está disponible.
    """
    is_ollama_up = await ollama.health_check()
    models = []
    
    if is_ollama_up:
        raw_models = await ollama.list_models()
        models = [m.get("name", "") for m in raw_models]
    
    health = HealthResponse(
        status="healthy" if is_ollama_up else "degraded",
        version="1.0.0",
        ollama_connected=is_ollama_up,
        ollama_models=models,
        environment=os.getenv("ENVIRONMENT", "development"),
    )
    
    if not is_ollama_up:
        # Retornar 503 para que Kubernetes sepa que hay un problema
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health.model_dump(),
        )
    
    return health


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2: Listar modelos
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="Modelos disponibles",
    description="""
Lista todos los modelos LLM disponibles.

Incluye:
- Modelos locales de Ollama (ya descargados)
- Modelos cloud disponibles según configuración

```bash
curl http://localhost:8000/models
```
    """,
)
async def list_models() -> ModelsResponse:
    """Lista de modelos disponibles en Ollama y la nube."""
    ollama_models = await ollama.list_models()
    
    # Convertir al formato de respuesta
    model_list: list[ModelInfo] = []
    
    for m in ollama_models:
        # Calcular tamaño legible
        size_bytes = m.get("size", 0)
        size_str = f"{size_bytes / 1e9:.1f} GB" if size_bytes > 0 else None
        
        model_list.append(ModelInfo(
            name=m.get("name", ""),
            size=size_str,
            provider="ollama",
            description=f"Modelo local via Ollama",
            modified_at=m.get("modified_at"),
        ))
    
    # Agregar modelos cloud (si están configurados)
    if os.getenv("AZURE_OPENAI_API_KEY"):
        model_list.append(ModelInfo(
            name=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            provider="azure",
            description="Azure OpenAI — GPT-4o",
        ))
    
    if os.getenv("GCP_PROJECT_ID"):
        model_list.append(ModelInfo(
            name="gemini-1.5-pro",
            provider="gcp",
            description="Google Vertex AI — Gemini 1.5 Pro",
        ))
    
    if os.getenv("AWS_ACCESS_KEY_ID"):
        model_list.append(ModelInfo(
            name="anthropic.claude-3-5-sonnet-20241022-v2:0",
            provider="aws",
            description="Amazon Bedrock — Claude 3.5 Sonnet",
        ))
    
    return ModelsResponse(
        models=model_list,
        total=len(model_list),
        ollama_connected=len(ollama_models) > 0,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3: Chat
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat con LLM",
    description="""
Envía un mensaje al LLM y recibe la respuesta completa.

El proveedor por defecto es **Ollama** (local, gratuito).

```bash
# Chat básico con Ollama (local)
curl -X POST http://localhost:8000/chat \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "¿Qué es Kubernetes?",
    "model": "llama3.2:3b"
  }'

# Con instrucciones del sistema
curl -X POST http://localhost:8000/chat \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "Explica Docker en 3 puntos",
    "model": "llama3.2:3b",
    "system_prompt": "Eres un instructor técnico. Sé conciso y usa ejemplos.",
    "temperature": 0.3
  }'
```
    """,
    responses={
        200: {"description": "Respuesta del LLM"},
        503: {"description": "LLM no disponible"},
        422: {"description": "Error de validación en los parámetros"},
    },
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat con el LLM seleccionado.
    
    Soporta Ollama (local) y proveedores cloud (Azure, GCP, AWS).
    """
    logger.info(
        f"💬 Chat request: provider={request.provider}, "
        f"model={request.model}, message_len={len(request.message)}"
    )
    
    try:
        if request.provider == LLMProvider.OLLAMA:
            result = await ollama.chat(
                message=request.message,
                model=request.model,
                system_prompt=request.system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        
        elif request.provider == LLMProvider.AZURE:
            result = await _chat_azure(request)
        
        elif request.provider == LLMProvider.GCP:
            result = await _chat_gcp(request)
        
        elif request.provider == LLMProvider.AWS:
            result = await _chat_aws(request)
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Proveedor no soportado: {request.provider}",
            )
        
        return ChatResponse(
            response=result["response"],
            model=result["model"],
            provider=result["provider"],
            tokens_used=result.get("tokens_used"),
            latency_ms=result["latency_ms"],
        )
    
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 4: Chat Streaming
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/chat/stream",
    summary="Chat con streaming",
    description="""
Chat con respuesta en streaming (Server-Sent Events).

Los tokens se envían a medida que el modelo los genera,
creando una experiencia más fluida (como ChatGPT).

```bash
curl -X POST http://localhost:8000/chat/stream \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "Explica los pods de Kubernetes",
    "model": "llama3.2:3b"
  }'
```
    """,
)
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Chat con streaming de tokens."""
    
    async def generate():
        async for token in ollama.chat_stream(
            message=request.message,
            model=request.model,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
        ):
            # Server-Sent Events format
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 5: Embeddings
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/embeddings",
    response_model=EmbeddingResponse,
    summary="Generar embeddings",
    description="""
Convierte texto en un vector numérico (embedding).

Los embeddings capturan el significado semántico del texto
y se usan para:
- **Búsqueda semántica**: encontrar documentos similares
- **RAG**: recuperar contexto relevante para el LLM
- **Clustering**: agrupar documentos por tema

```bash
curl -X POST http://localhost:8000/embeddings \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Kubernetes orquesta contenedores Docker",
    "model": "llama3.2:3b"
  }'
```
    """,
)
async def generate_embeddings(request: EmbeddingRequest) -> EmbeddingResponse:
    """Genera un embedding vectorial del texto dado."""
    start_time = time.perf_counter()
    
    try:
        embedding = await ollama.generate_embedding(
            text=request.text,
            model=request.model,
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return EmbeddingResponse(
            embedding=embedding,
            dimensions=len(embedding),
            model=request.model,
            text_length=len(request.text),
            latency_ms=latency_ms,
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error generando embedding: {str(e)}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# Funciones internas: clientes cloud
# ══════════════════════════════════════════════════════════════════════════════

async def _chat_azure(request: ChatRequest) -> dict:
    """
    Chat con Azure OpenAI.
    
    Requiere variables de entorno:
        AZURE_OPENAI_API_KEY
        AZURE_OPENAI_ENDPOINT
        AZURE_OPENAI_DEPLOYMENT
    """
    import time
    start = time.perf_counter()
    
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    
    if not api_key or not endpoint:
        raise ValueError(
            "Azure OpenAI no configurado. "
            "Define AZURE_OPENAI_API_KEY y AZURE_OPENAI_ENDPOINT en .env"
        )
    
    # Usar el SDK de OpenAI (compatible con Azure)
    from openai import AsyncAzureOpenAI
    
    client = AsyncAzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
    )
    
    messages = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    messages.append({"role": "user", "content": request.message})
    
    response = await client.chat.completions.create(
        model=deployment,
        messages=messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    
    return {
        "response": response.choices[0].message.content,
        "model": deployment,
        "provider": "azure",
        "tokens_used": response.usage.total_tokens if response.usage else None,
        "latency_ms": (time.perf_counter() - start) * 1000,
    }


async def _chat_gcp(request: ChatRequest) -> dict:
    """
    Chat con Google Vertex AI (Gemini).
    
    Requiere:
        GCP_PROJECT_ID
        GOOGLE_APPLICATION_CREDENTIALS (path al service account JSON)
    """
    import time
    start = time.perf_counter()
    
    project_id = os.getenv("GCP_PROJECT_ID")
    region = os.getenv("GCP_REGION", "us-central1")
    model_name = os.getenv("VERTEX_AI_MODEL", "gemini-1.5-flash")
    
    if not project_id:
        raise ValueError(
            "GCP no configurado. Define GCP_PROJECT_ID y "
            "GOOGLE_APPLICATION_CREDENTIALS en .env"
        )
    
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig
    
    vertexai.init(project=project_id, location=region)
    
    model = GenerativeModel(model_name)
    
    prompt = request.message
    if request.system_prompt:
        prompt = f"{request.system_prompt}\n\n{request.message}"
    
    response = model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        ),
    )
    
    return {
        "response": response.text,
        "model": model_name,
        "provider": "gcp",
        "tokens_used": None,
        "latency_ms": (time.perf_counter() - start) * 1000,
    }


async def _chat_aws(request: ChatRequest) -> dict:
    """
    Chat con Amazon Bedrock.
    
    Requiere:
        AWS_ACCESS_KEY_ID
        AWS_SECRET_ACCESS_KEY
        AWS_DEFAULT_REGION
    """
    import time
    import json
    start = time.perf_counter()
    
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    model_id = os.getenv(
        "AWS_BEDROCK_MODEL",
        "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    
    import boto3
    
    bedrock = boto3.client(
        service_name="bedrock-runtime",
        region_name=region,
    )
    
    # Formato para modelos Anthropic en Bedrock
    messages = []
    if request.system_prompt:
        messages.append({"role": "user", "content": f"[System]: {request.system_prompt}"})
        messages.append({"role": "assistant", "content": "Entendido."})
    
    messages.append({"role": "user", "content": request.message})
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "messages": messages,
    })
    
    response = bedrock.invoke_model(body=body, modelId=model_id)
    response_body = json.loads(response.get("body").read())
    
    return {
        "response": response_body["content"][0]["text"],
        "model": model_id,
        "provider": "aws",
        "tokens_used": response_body.get("usage", {}).get("output_tokens"),
        "latency_ms": (time.perf_counter() - start) * 1000,
    }
