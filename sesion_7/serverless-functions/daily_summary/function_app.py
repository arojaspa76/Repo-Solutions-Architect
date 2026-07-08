"""
serverless-functions/daily_summary/function_app.py
====================================================
Azure Function con Timer Trigger que ejecuta a las 18:00 LT
de lunes a viernes y genera un resumen del día con GPT-4o.

Adicionalmente expone un HTTP Trigger para pruebas manuales
desde el portal Azure (ejercicio del Capítulo 3).

Variables de entorno requeridas (Azure Function App Settings):
  AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_KEY
  AZURE_OPENAI_CHAT_MODEL
  COSMOS_ENDPOINT
  COSMOS_KEY
  COSMOS_DATABASE
  SENDGRID_API_KEY          — Para envío de correo del resumen
  SUMMARY_RECIPIENTS        — Emails separados por coma
"""

import azure.functions as func
import logging
import os
import json
from datetime import datetime, timezone
from openai import AzureOpenAI
from azure.cosmos import CosmosClient
import httpx

app = func.FunctionApp()
logger = logging.getLogger(__name__)

# ── Clientes compartidos (se reutilizan entre invocaciones en caliente) ─────────
_openai_client = None
_cosmos_client = None


def get_openai_client() -> AzureOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_KEY"],
            api_version="2024-08-01-preview",
        )
    return _openai_client


def get_cosmos_container():
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = CosmosClient(
            os.environ["COSMOS_ENDPOINT"],
            credential=os.environ["COSMOS_KEY"],
        )
    db = _cosmos_client.get_database_client(
        os.getenv("COSMOS_DATABASE", "techcorp-chatbot")
    )
    return db.get_container_client("conversations")


# ── Lógica de negocio ──────────────────────────────────────────────────────────

def fetch_todays_conversations() -> list[dict]:
    """
    Recupera todas las conversaciones del día de Cosmos DB.
    Filtra por la fecha actual (campo updated_at).
    """
    container = get_cosmos_container()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    query = f"""
        SELECT c.session_id, c.user_id, c.messages, c.tokens_total, c.updated_at
        FROM c
        WHERE STARTSWITH(c.updated_at, '{today}')
    """
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    logger.info("Conversaciones del día: %d", len(items))
    return items


def generate_summary(conversations: list[dict]) -> str:
    """Llama a GPT-4o para generar el resumen ejecutivo."""
    client = get_openai_client()
    model  = os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-4o")

    # Preparar datos compactos (solo la primera pregunta de cada sesión)
    sessions_text = []
    for conv in conversations[:50]:   # Límite de 50 sesiones por resumen
        msgs = conv.get("messages", [])
        first_q = next((m["content"] for m in msgs if m["role"] == "user"), "")
        sessions_text.append(f"- {first_q[:120]}")
    sessions_str = "\n".join(sessions_text) or "Sin conversaciones hoy."

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres analista de soporte IT de TechCorp. "
                    "Genera un resumen ejecutivo diario conciso (máximo 300 palabras) "
                    "de las consultas de los empleados. Identifica los 3 temas más frecuentes "
                    "y recomienda acciones preventivas."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Fecha: {datetime.now(timezone.utc).strftime('%d/%m/%Y')}\n"
                    f"Total de sesiones: {len(conversations)}\n\n"
                    f"Primeras preguntas del día:\n{sessions_str}"
                ),
            },
        ],
        max_tokens=500,
        temperature=0.4,
    )
    return response.choices[0].message.content


def send_email_summary(summary: str, session_count: int):
    """Envía el resumen por correo usando SendGrid."""
    api_key    = os.getenv("SENDGRID_API_KEY", "")
    recipients = os.getenv("SUMMARY_RECIPIENTS", "it-manager@techcorp.com").split(",")

    if not api_key:
        logger.warning("SENDGRID_API_KEY no configurado. Resumen no enviado.")
        return

    payload = {
        "personalizations": [{"to": [{"email": r.strip()} for r in recipients]}],
        "from": {"email": "chatbot@techcorp.com", "name": "TechCorp Chatbot"},
        "subject": f"Resumen IT del {datetime.now(timezone.utc).strftime('%d/%m/%Y')} ({session_count} sesiones)",
        "content": [{"type": "text/plain", "value": summary}],
    }

    with httpx.Client() as http:
        resp = http.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
    logger.info("Email enviado. Status=%d", resp.status_code)


# ── Triggers ────────────────────────────────────────────────────────────────────

@app.timer_trigger(
    schedule="0 0 18 * * 1-5",   # Lunes–Viernes a las 18:00 UTC
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def daily_summary_timer(timer: func.TimerRequest) -> None:
    """
    Timer Trigger: se ejecuta automáticamente de lunes a viernes a las 18:00 UTC.
    """
    logger.info("Timer disparado. past_due=%s", timer.past_due)
    conversations = fetch_todays_conversations()
    summary       = generate_summary(conversations)
    send_email_summary(summary, len(conversations))
    logger.info("Resumen diario completado.")


@app.route(route="summary", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def daily_summary_http(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP Trigger: permite ejecutar el resumen manualmente para pruebas.
    Usar desde el portal Azure → Functions → Test/Run.

    URL: GET https://fn-techcorp-summary.azurewebsites.net/api/summary?code=<function-key>
    """
    logger.info("HTTP Trigger: generando resumen bajo demanda.")
    try:
        conversations = fetch_todays_conversations()
        summary       = generate_summary(conversations)
        return func.HttpResponse(
            body=json.dumps({
                "date":      datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "sessions":  len(conversations),
                "summary":   summary,
            }, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as exc:
        logger.exception("Error al generar resumen: %s", exc)
        return func.HttpResponse(
            body=json.dumps({"error": str(exc)}),
            mimetype="application/json",
            status_code=500,
        )
