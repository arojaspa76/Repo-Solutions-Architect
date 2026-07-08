"""
Google Cloud Function — LLM Summarizer
=======================================
Cloud Function gen2 (HTTP trigger) que recibe texto y retorna
un resumen generado por un LLM (Vertex AI Gemini o Ollama local).

MISMO EJERCICIO que Azure y AWS — solo cambia el wrapper de nube.

Ejecución local:
    pip install functions-framework
    functions-framework --target llm_summarize --port 8080

Deploy a GCP:
    ./deploy.sh

Endpoint local:
    POST http://localhost:8080

Endpoint en nube:
    POST https://REGION-PROJECT.cloudfunctions.net/llm-summarize
"""

import json
import logging
import os
import time
import functions_framework
import httpx

# ── Configuración ─────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GCP_REGION  = os.getenv("GCP_REGION", "us-central1")
VERTEX_MODEL = os.getenv("VERTEX_AI_MODEL", "gemini-1.5-flash")
OLLAMA_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
USE_OLLAMA   = os.getenv("USE_OLLAMA", "true").lower() == "true"


# ── Función principal ──────────────────────────────────────────────────────────
@functions_framework.http
def llm_summarize(request):
    """
    Google Cloud Function gen2: Summarize texto con LLM.

    Arquitectura Serverless GCP:
      - Scale to zero: $0 sin requests
      - Escala automática hasta 3000 instancias simultáneas
      - Pay-per-use: ~$0.0000004/invocación (primeras 2M gratis/mes)
      - Timeout máximo: 60 min (gen2)
      - RAM máxima: 32GB (gen2) → viable para modelos medianos
      - CPU máxima: 8 vCPU (gen2)

    Para LLMs grandes:
      - Cloud Run: más control, imagen Docker custom con Ollama
      - Vertex AI: servicio gestionado de Gemini/PaLM/Llama
    """
    start_time = time.perf_counter()
    logger.info("🟡 GCP Cloud Function invocada: llm-summarize")

    # CORS — necesario para llamadas desde browser
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
        return ("", 204, headers)

    cors_headers = {"Access-Control-Allow-Origin": "*"}

    # ── GET: health check ─────────────────────────────────────────────────────
    if request.method == "GET":
        return (
            json.dumps({
                "status": "healthy",
                "function": "llm-summarize",
                "provider": "google-cloud-functions",
                "llm_backend": "ollama" if USE_OLLAMA else "vertex-ai",
                "runtime": "python3.12",
            }),
            200,
            {**cors_headers, "Content-Type": "application/json"},
        )

    # ── POST: procesar ────────────────────────────────────────────────────────
    if request.content_type != "application/json":
        return (
            json.dumps({"error": "Content-Type debe ser application/json"}),
            415,
            cors_headers,
        )

    body = request.get_json(silent=True)
    if not body:
        return (
            json.dumps({"error": "Body JSON inválido o vacío"}),
            400,
            cors_headers,
        )

    text = body.get("text", "").strip()
    language = body.get("language", "es")
    max_length = body.get("max_length", 150)

    if not text or len(text) < 10:
        return (
            json.dumps({"error": "'text' debe tener al menos 10 caracteres"}),
            400,
            cors_headers,
        )

    # ── Generar resumen ────────────────────────────────────────────────────────
    try:
        import asyncio
        if USE_OLLAMA:
            # Para Cloud Functions, asyncio.run() funciona en gen2
            summary = asyncio.run(_summarize_with_ollama(text, language, max_length))
            llm_provider = "ollama-local"
        else:
            summary = _summarize_with_vertex_ai(text, language, max_length)
            llm_provider = f"vertex-ai-{VERTEX_MODEL}"

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return (
            json.dumps({"error": f"Error del LLM: {str(e)}"}),
            500,
            cors_headers,
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
            "cloud_provider": "google-cloud-functions",
        }
    }

    logger.info(f"✅ Resumen generado en {latency_ms}ms")
    return (
        json.dumps(response_body, ensure_ascii=False),
        200,
        {**cors_headers, "Content-Type": "application/json; charset=utf-8"},
    )


# ── Helpers LLM ───────────────────────────────────────────────────────────────

async def _summarize_with_ollama(text: str, language: str, max_length: int) -> str:
    """Ollama — para desarrollo local y demos sin costo."""
    lang_str = "en español" if language == "es" else "in English"
    prompt = (
        f"Resume el siguiente texto {lang_str} en máximo {max_length} palabras. "
        f"Solo el resumen:\n\n{text}"
    )
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "llama3.2:3b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.3},
            },
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()


def _summarize_with_vertex_ai(text: str, language: str, max_length: int) -> str:
    """
    Vertex AI (Gemini) — para producción en GCP.

    Ventajas de Vertex AI vs OpenAI API en GCP:
    - Sin costo de egress de red (mismo datacenter)
    - Integración nativa con IAM (sin API keys)
    - Gemini 1.5 Flash: muy rápido y económico
    - Gemini 1.5 Pro: para tareas complejas
    """
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel

        vertexai.init(project=GCP_PROJECT, location=GCP_REGION)
        model = GenerativeModel(VERTEX_MODEL)

        lang_str = "en español" if language == "es" else "in English"
        prompt = (
            f"Resume el siguiente texto {lang_str} en máximo {max_length} palabras. "
            f"Solo el resumen, sin introducción:\n\n{text}"
        )

        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.3, "max_output_tokens": max_length * 3},
        )
        return response.text.strip()

    except ImportError:
        raise RuntimeError(
            "google-cloud-aiplatform no instalado. "
            "Para desarrollo local, usar USE_OLLAMA=true"
        )
