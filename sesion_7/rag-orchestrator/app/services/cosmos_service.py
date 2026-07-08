"""
services/cosmos_service.py
===========================
Persiste el historial de conversaciones en Azure Cosmos DB (modo serverless).
Cada sesión de usuario es un documento JSON con la lista de turnos.

Variables de entorno requeridas:
  COSMOS_ENDPOINT    — ej: https://cosmos-techcorp.documents.azure.com:443/
  COSMOS_KEY         — Primary key del recurso
  COSMOS_DATABASE    — Nombre de la base de datos, ej: techcorp-chatbot
  COSMOS_CONTAINER   — Nombre del contenedor, ej: conversations
"""

import os
import logging
from datetime import datetime
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey, exceptions as cosmos_exc

logger = logging.getLogger(__name__)


class CosmosService:
    """Cliente async para Azure Cosmos DB."""

    def __init__(self):
        self.endpoint    = os.environ["COSMOS_ENDPOINT"]
        self.key         = os.environ["COSMOS_KEY"]
        self.db_name     = os.getenv("COSMOS_DATABASE",  "techcorp-chatbot")
        self.cont_name   = os.getenv("COSMOS_CONTAINER", "conversations")
        self.client      = None
        self.container   = None

    async def initialize(self):
        """Crea cliente, database y container si no existen."""
        self.client = CosmosClient(self.endpoint, credential=self.key)
        db = await self.client.create_database_if_not_exists(self.db_name)
        self.container = await db.create_container_if_not_exists(
            id=self.cont_name,
            partition_key=PartitionKey(path="/session_id"),
            offer_throughput=None,  # Modo serverless, sin RU/s fijo
        )
        logger.info(
            "CosmosService listo. DB=%s Container=%s",
            self.db_name, self.cont_name
        )

    async def get_history(self, session_id: str) -> list[dict]:
        """
        Recupera el historial de mensajes de una sesión.

        Returns:
            Lista de dicts con keys 'role' y 'content' (formato OpenAI).
        """
        try:
            item = await self.container.read_item(
                item=session_id,
                partition_key=session_id,
            )
            return item.get("messages", [])
        except cosmos_exc.CosmosResourceNotFoundError:
            return []

    async def save_turn(
        self,
        session_id: str,
        user_id:    str,
        question:   str,
        answer:     str,
        tokens:     int,
    ):
        """
        Agrega un turno (pregunta + respuesta) al historial de la sesión.
        Crea el documento si es la primera vez.
        """
        history = await self.get_history(session_id)

        history.append({"role": "user",      "content": question})
        history.append({"role": "assistant",  "content": answer})

        doc = {
            "id":         session_id,
            "session_id": session_id,
            "user_id":    user_id,
            "messages":   history,
            "tokens_total": tokens,
            "updated_at": datetime.utcnow().isoformat(),
        }
        await self.container.upsert_item(doc)
        logger.info(
            "Historial guardado. session_id=%s turnos=%d",
            session_id, len(history) // 2
        )

    async def close(self):
        if self.client:
            await self.client.close()
