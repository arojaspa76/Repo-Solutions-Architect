"""
AWS Lambda — LLM Summarizer
=============================
Función Lambda (HTTP via API Gateway) que recibe texto y retorna
un resumen generado por un LLM (Amazon Bedrock Claude o Ollama local).

MISMO EJERCICIO que Azure y GCP — solo cambia el wrapper de nube.

Test local con SAM:
    sam local invoke LLMFunction --event events/test-event.json

O con AWS CLI (si ya está desplegado):
    aws lambda invoke --function-name bsg-llm-summarize \
      --payload '{"body": "{\"text\": \"...\"}"}' output.json

Deploy:
    ./deploy.sh
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error

# ── Configuración ─────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_URL    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
USE_OLLAMA    = os.getenv("USE_OLLAMA", "true").lower() == "true"
BEDROCK_MODEL = os.getenv(
    "AWS_BEDROCK_MODEL_ID",
    "anthropic.claude-3-5-sonnet-20241022-v2:0"
)
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


# ── Handler principal ──────────────────────────────────────────────────────────
def lambda_handler(event: dict, context) -> dict:
    """
    AWS Lambda Handler: Summarize texto con LLM.

    Arquitectura Serverless AWS:
      - Scale to zero: $0 sin invocaciones
      - Escala automática hasta 1000 instancias concurrentes (configurable)
      - Pay-per-use: $0.0000166667 por GB-segundo
      - Timeout máximo: 15 minutos
      - RAM: hasta 10GB (útil para modelos pequeños en Lambda)
      - CPU: 1 vCPU por GB de RAM asignado

    Para LLMs grandes en AWS:
      - ECS Fargate: imagen Docker con Ollama
      - SageMaker: hosting gestionado de modelos
      - Bedrock: API gestionada de Claude/Llama/Titan (NO necesita GPU propia)

    Event de entrada (via API Gateway):
      {
        "httpMethod": "POST",
        "body": "{\"text\": \"...\", \"language\": \"es\"}",
        "headers": {"Content-Type": "application/json"}
      }
    """
    start_time = time.perf_counter()
    logger.info(f"🟠 Lambda invocada: {context.function_name if context else 'local'}")

    # Cabeceras CORS
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
        "Content-Type": "application/json; charset=utf-8",
    }

    # ── OPTIONS: preflight CORS ───────────────────────────────────────────────
    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "POST")
    if http_method == "OPTIONS":
        return {"statusCode": 204, "headers": cors_headers, "body": ""}

    # ── GET: health check ─────────────────────────────────────────────────────
    if http_method == "GET":
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({
                "status": "healthy",
                "function": "bsg-llm-summarize",
                "provider": "aws-lambda",
                "llm_backend": "ollama" if USE_OLLAMA else "amazon-bedrock",
                "runtime": "python3.12",
                "remaining_ms": context.get_remaining_time_in_millis() if context else "N/A",
            }),
        }

    # ── POST: procesar ────────────────────────────────────────────────────────
    # El body puede venir como string (API Gateway) o dict (invocación directa)
    raw_body = event.get("body", "{}")
    if isinstance(raw_body, str):
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "Body JSON inválido"}),
            }
    else:
        body = raw_body or {}

    text = body.get("text", "").strip()
    language = body.get("language", "es")
    max_length = body.get("max_length", 150)

    if not text or len(text) < 10:
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({"error": "'text' debe tener al menos 10 caracteres"}),
        }

    # ── Generar resumen ────────────────────────────────────────────────────────
    try:
        if USE_OLLAMA:
            summary = _summarize_with_ollama_sync(text, language, max_length)
            llm_provider = "ollama-local"
        else:
            summary = _summarize_with_bedrock(text, language, max_length)
            llm_provider = f"amazon-bedrock-{BEDROCK_MODEL.split('.')[1]}"

    except Exception as e:
        logger.error(f"❌ Error generando resumen: {e}")
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Error del LLM: {str(e)}"}),
        }

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
            "cloud_provider": "aws-lambda",
            "request_id": context.aws_request_id if context else "local",
        }
    }

    logger.info(f"✅ Resumen generado en {latency_ms}ms ({llm_provider})")
    return {
        "statusCode": 200,
        "headers": cors_headers,
        "body": json.dumps(response_body, ensure_ascii=False),
    }


# ── Helpers LLM ───────────────────────────────────────────────────────────────

def _summarize_with_ollama_sync(text: str, language: str, max_length: int) -> str:
    """
    Ollama — para desarrollo local con SAM.
    Usa urllib (stdlib) para evitar dependencias extra en Lambda.
    """
    lang_str = "en español" if language == "es" else "in English"
    prompt = (
        f"Resume el siguiente texto {lang_str} en máximo {max_length} palabras. "
        f"Solo el resumen:\n\n{text}"
    )
    payload = json.dumps({
        "model": "llama3.2:3b",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.3},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["message"]["content"].strip()


def _summarize_with_bedrock(text: str, language: str, max_length: int) -> str:
    """
    Amazon Bedrock — para producción en AWS.

    Ventajas de Bedrock vs otros LLM APIs en AWS:
    - Sin costo de egress de red (mismo datacenter)
    - Integración nativa con IAM Roles (sin API keys)
    - Acceso a Claude, Llama 3, Titan, Mistral, etc.
    - Bedrock Guardrails: filtros de contenido y PII integrados

    Configurar IAM Role de Lambda con:
      - bedrock:InvokeModel para el modelo específico
    """
    try:
        import boto3

        bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        lang_str = "en español" if language == "es" else "in English"
        prompt = (
            f"Resume el siguiente texto {lang_str} en máximo {max_length} palabras. "
            f"Solo el resumen, sin introducción:\n\n{text}"
        )

        # API de Claude en Bedrock (Messages API)
        if "anthropic" in BEDROCK_MODEL:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_length * 3,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            })
        # API de Llama en Bedrock
        elif "meta" in BEDROCK_MODEL or "llama" in BEDROCK_MODEL:
            body = json.dumps({
                "prompt": f"<s>[INST] {prompt} [/INST]",
                "max_gen_len": max_length * 3,
                "temperature": 0.3,
            })
        # Titan (Amazon nativo)
        else:
            body = json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_length * 3,
                    "temperature": 0.3,
                },
            })

        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())

        # Extraer texto según el modelo
        if "anthropic" in BEDROCK_MODEL:
            return result["content"][0]["text"].strip()
        elif "meta" in BEDROCK_MODEL or "llama" in BEDROCK_MODEL:
            return result["generation"].strip()
        else:
            return result["results"][0]["outputText"].strip()

    except ImportError:
        raise RuntimeError(
            "boto3 no instalado. Para desarrollo local, usar USE_OLLAMA=true"
        )
