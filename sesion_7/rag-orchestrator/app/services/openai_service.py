"""
services/openai_service.py
===========================
Wrapper sobre el SDK de Azure OpenAI.
Gestiona tanto la generación de embeddings como las completions de chat.

Variables de entorno requeridas:
  AZURE_OPENAI_ENDPOINT     — URL del recurso, ej: https://oai-techcorp.openai.azure.com/
  AZURE_OPENAI_KEY          — API Key (o usa Managed Identity en producción)
  AZURE_OPENAI_CHAT_MODEL   — Nombre del deployment GPT-4o, ej: gpt-4o
  AZURE_OPENAI_EMBED_MODEL  — Nombre del deployment embedding, ej: text-embedding-3-small
"""

import os
import logging
import time
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el asistente de soporte técnico de TechCorp Latinoamérica.
Tu objetivo es ayudar a los empleados con problemas de IT de forma clara y concisa.

Reglas:
- Responde SOLO en base al contexto provisto. Si no tienes información suficiente, dilo.
- Usa un tono amigable y profesional.
- Si la solución requiere varios pasos, usa una lista numerada.
- Al final, pregunta si el problema fue resuelto.
- Nunca inventes información técnica que no esté en el contexto.

Contexto de la base de conocimiento:
{context}
"""


class OpenAIService:
    """Cliente para Azure OpenAI: embeddings y chat completions."""

    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_KEY"],
            api_version="2024-08-01-preview",
        )
        self.chat_model  = os.getenv("AZURE_OPENAI_CHAT_MODEL",  "gpt-4o")
        self.embed_model = os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-3-small")
        logger.info(
            "OpenAIService inicializado. Chat=%s | Embed=%s",
            self.chat_model, self.embed_model
        )

    def get_embedding(self, text: str) -> list[float]:
        """Genera un embedding vectorial de 1536 dimensiones."""
        response = self.client.embeddings.create(
            input=text.replace("\n", " "),
            model=self.embed_model,
        )
        return response.data[0].embedding

    def chat_completion(
        self,
        question: str,
        context: str,
        conversation_history: list[dict] | None = None,
    ) -> tuple[str, int, float]:
        """
        Genera una respuesta de chat enriquecida con contexto RAG.

        Returns:
            (answer, tokens_used, latency_ms)
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(context=context)}
        ]

        # Agregar historial de conversación (últimos 6 turnos)
        if conversation_history:
            messages.extend(conversation_history[-6:])

        messages.append({"role": "user", "content": question})

        start = time.time()
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            max_tokens=800,
            temperature=0.3,   # Baja temperatura: respuestas más deterministas para soporte IT
            top_p=0.95,
        )
        latency_ms = (time.time() - start) * 1000

        answer     = response.choices[0].message.content
        tokens     = response.usage.total_tokens

        logger.info(
            "Completion: tokens=%d latency=%.1fms model=%s",
            tokens, latency_ms, self.chat_model
        )
        return answer, tokens, latency_ms
