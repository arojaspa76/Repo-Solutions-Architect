"""
Azure Function — LLM Summarizer
=================================
Función HTTP trigger que recibe texto y retorna un resumen
generado por un LLM (Azure OpenAI o Ollama local).

MISMO EJERCICIO que GCP y AWS — solo cambia el wrapper de nube.

Ejecución local:
    func start

Deploy a Azure:
    ./deploy.sh

Endpoint local:
    POST http://localhost:7071/api/llm-summarize

Endpoint en nube (ejemplo):
    POST https://bsg-llm-function.azurewebsites.net/api/llm-summarize

Body de request:
    {
        "text": "Texto a resumir...",
        "language": "es",
        "max_length": 150
    }
"""

import json
import logging
import os
import time
from typing import Optional

import azure.functions as func
import httpx

# ── Configuración ─────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# Variables de entorno — configurar en local.settings.json o en Azure Portal
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY  = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ── Función principal ──────────────────────────────────────────────────────────
@app.route(route="llm-summarize", methods=["POST", "GET"])
async def llm_summarize(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure HTTP Function: Summarize texto con LLM.

    Arquitectura Serverless:
      - Scale to zero: $0 cuando no hay requests
      - Escala automática: miles de requests simultáneos
      - Pay-per-execution: ~$0.000016 por invocación (Consumption Plan)
      - Timeout default: 5 min (Consumption) / ilimitado (Premium)

    Para LLMs grandes (>7B params), usar Premium Plan o Container Apps
    ya que el Consumption Plan tiene límite de 1.5GB RAM.
    """
    start_time = time.perf_counter()
    logger.info("🔵 Azure Function invocada: llm-summarize")

    # ── GET: health check ─────────────────────────────────────────────────────
    if req.method == "GET":
        return func.HttpResponse(
            json.dumps({
                "status": "healthy",
                "function": "llm-summarize",
                "provider": "azure-functions",
                "llm_backend": "ollama" if USE_OLLAMA else "azure-openai",
                "runtime": "python3.11",
            }),
            mimetype="application/json",
            status_code=200,
        )

    # ── POST: procesar request ────────────────────────────────────────────────
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Body debe ser JSON válido"}),
            mimetype="application/json",
            status_code=400,
        )

    text = body.get("text", "").strip()
    language = body.get("language", "es")
    max_length = body.get("max_length", 150)

    if not text or len(text) < 10:
        return func.HttpResponse(
            json.dumps({"error": "El campo 'text' debe tener al menos 10 caracteres"}),
            mimetype="application/json",
            status_code=400,
        )

    # ── Generar resumen ────────────────────────────────────────────────────────
    try:
        if USE_OLLAMA:
            summary = await _summarize_with_ollama(text, language, max_length)
            llm_provider = "ollama-local"
        else:
            summary = await _summarize_with_azure_openai(text, language, max_length)
            llm_provider = "azure-openai"

    except Exception as e:
        logger.error(f"❌ Error generando resumen: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Error del LLM: {str(e)}"}),
            mimetype="application/json",
            status_code=500,
        )

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    original_words = len(text.split())
    summary_words = len(summary.split())

    response_body = {
        "summary": summary,
        "metadata": {
            "original_length": original_words,
            "summary_length": summary_words,
            "compression_ratio": round(1 - summary_words / max(original_words, 1), 3),
            "latency_ms": latency_ms,
            "llm_provider": llm_provider,
            "cloud_provider": "azure-functions",
        }
    }

    logger.info(f"✅ Resumen generado en {latency_ms}ms ({llm_provider})")

    return func.HttpResponse(
        json.dumps(response_body, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
        status_code=200,
    )


# ── Helpers LLM ───────────────────────────────────────────────────────────────

async def _summarize_with_ollama(
    text: str,
    language: str = "es",
    max_length: int = 150,
    model: str = "llama3.2:3b"
) -> str:
    """Llamar a Ollama (usado en desarrollo local o demo sin costos)."""
    lang_str = "en español" if language == "es" else "in English"
    prompt = (
        f"Resume el siguiente texto {lang_str} en máximo {max_length} palabras. "
        f"Solo el resumen, sin introducción:\n\n{text}"
    )
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.3},
            },
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()


async def _summarize_with_azure_openai(
    text: str,
    language: str = "es",
    max_length: int = 150
) -> str:
    """
    Llamar a Azure OpenAI (GPT-4o).

    Para usar Azure OpenAI en una Function:
    1. Crear recurso Azure OpenAI en el mismo Resource Group
    2. Usar Managed Identity (sin API keys hardcodeadas)
    3. O usar Key Vault para gestionar el secreto
    """
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
        raise RuntimeError(
            "AZURE_OPENAI_ENDPOINT y AZURE_OPENAI_API_KEY deben estar configuradas. "
            "Para desarrollo local, usar USE_OLLAMA=true"
        )

    lang_str = "en español" if language == "es" else "in English"
    url = (
        f"{AZURE_OPENAI_ENDPOINT}openai/deployments/{AZURE_OPENAI_DEPLOYMENT}"
        f"/chat/completions?api-version=2024-02-01"
    )
    payload = {
        "messages": [
            {"role": "system", "content": "Eres un experto en síntesis de textos técnicos."},
            {"role": "user", "content": (
                f"Resume el siguiente texto {lang_str} en máximo {max_length} palabras:\n\n{text}"
            )},
        ],
        "temperature": 0.3,
        "max_tokens": max_length * 2,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url,
            headers={"api-key": AZURE_OPENAI_API_KEY, "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
